#!/opt/homebrew/bin/python3
"""Private, read-only dashboard for this Mac.

Every number comes from a real source; missing values are never filled in.
Power comes from macmon's macOS counters and SMC estimate, not an outlet meter, except
on MacBooks, where the battery gauge measures the whole Mac:
  - Netdata (127.0.0.1:19999): CPU and GPU use, swap, network, disk I/O, apps, load, uptime.
  - macmon (Homebrew, no root): per-core activity and MHz, cluster/GPU MHz and reported power.
  - mac-sensors (this folder): macOS's own temperature sensors, SMC fan RPM/min/max, thermal state.
  - ioreg / system_profiler (MacBooks only): battery charge and health, adapter, and the
    whole-Mac power the battery gauge measures.
  - vm_stat / sysctl: memory as Activity Monitor counts it, memory pressure.
  - smartctl (Homebrew): SSD health.
All displayed readings are sampled every 5 s into samples.sqlite3 (24 h).
"""
import collections
import concurrent.futures
import ipaddress
import json
import logging
import math
import os
import plistlib
import socketserver
import sqlite3
import subprocess
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = 'http://127.0.0.1:19999'
# Both Macs use the same dashboard; each installation can choose its URL path.
PANEL_PATH = os.environ.get('PANEL_PATH', '/mini').rstrip('/')
if not PANEL_PATH.startswith('/') or not PANEL_PATH[1:].replace('-', '').isalnum():
    raise ValueError('PANEL_PATH must be a single absolute URL path')
ICONS = {
    'favicon.svg': ('favicon.svg', 'image/svg+xml'),
    'favicon.ico': ('favicon-32.png', 'image/png'),
    'favicon-32.png': ('favicon-32.png', 'image/png'),
    'apple-touch-icon.png': ('apple-touch-icon.png', 'image/png'),
}
RANGES = {300: 4, 3600: 15, 21600: 30, 86400: 60}  # seconds shown -> cache seconds
POINTS = 150
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
SAMPLE_EVERY = 5
MACMON = '/opt/homebrew/bin/macmon'
SMARTCTL = '/opt/homebrew/bin/smartctl'
# The app's own CLI first, so it always matches the running daemon. Outside a
# terminal it only acts as a CLI with TAILSCALE_BE_CLI set.
os.environ.setdefault('TAILSCALE_BE_CLI', '1')
TAILSCALE = next((p for p in ('/Applications/Tailscale.app/Contents/MacOS/Tailscale',
                              '/usr/local/bin/tailscale', '/opt/homebrew/bin/tailscale')
                  if os.access(p, os.X_OK)), 'tailscale')


def run(*cmd, timeout=3):
    try:
        return subprocess.check_output(cmd, text=True, timeout=timeout, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.SubprocessError):
        return ''


def number(text):
    try:
        return int(text)
    except (ValueError, TypeError):
        return None


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def default_interface():
    for line in run('/sbin/route', '-n', 'get', 'default').splitlines():
        if line.strip().startswith('interface:'):
            return line.split(':', 1)[1].strip()
    return None


def gpu_cores():
    try:
        displays = json.loads(run('/usr/sbin/system_profiler', '-json', 'SPDisplaysDataType', timeout=20))
        return int(displays['SPDisplaysDataType'][0]['sppci_cores'])
    except (ValueError, KeyError, IndexError, TypeError):
        return None


def machine_info():
    memsize = number(run('/usr/sbin/sysctl', '-n', 'hw.memsize'))
    levels = {}
    for level in (0, 1):
        name = run('/usr/sbin/sysctl', '-n', f'hw.perflevel{level}.name')
        count = number(run('/usr/sbin/sysctl', '-n', f'hw.perflevel{level}.logicalcpu'))
        if name and count:
            levels[name] = count
    return {
        'name': run('/usr/sbin/scutil', '--get', 'ComputerName') or None,
        'model': run('/usr/sbin/sysctl', '-n', 'hw.model') or None,
        'chip': run('/usr/sbin/sysctl', '-n', 'machdep.cpu.brand_string') or None,
        'cores': number(run('/usr/sbin/sysctl', '-n', 'hw.ncpu')),
        'pCores': levels.get('Performance'), 'eCores': levels.get('Efficiency'),
        'gpuCores': gpu_cores(),
        'macos': run('/usr/bin/sw_vers', '-productVersion') or None,
        'ramGiB': memsize / 2**30 if memsize else None,
    }


MACHINE = machine_info()
NET = default_interface()

# Netdata charts with history: key -> (chart, {series: function(row) -> value})
SOURCES = {
    'cpu': ('system.cpu', {'cpu': lambda r: r['user'] + r['nice'] + r['system']}),
    'gpu': ('macos.gpu_utilization', {'gpu': lambda r: r['utilization']}),
    'swap': ('mem.swap', {'swap': lambda r: r['used'] / 1024}),
    'swapio': ('mem.swapio', {'in': lambda r: r['in'] * 1.024e-3, 'out': lambda r: abs(r['out']) * 1.024e-3}),
    'fan': ('sensors.macos_smc_fan_F0Ac', {'fan': lambda r: r['input']}),
    'disk': ('disk.disk0', {'read': lambda r: r['reads'] * 1.024e-3, 'write': lambda r: abs(r['writes']) * 1.024e-3}),
}
if NET:
    SOURCES['net'] = ('net.' + NET, {'down': lambda r: r['received'] / 1000, 'up': lambda r: abs(r['sent']) / 1000})
CURRENT = dict({k: v[0] for k, v in SOURCES.items()}, load='system.load', uptime='system.uptime')
ALIASES = {
    'qemu-system-aarch64-headless': 'Emulador Android', 'system-daemons': 'Servicios del sistema',
    'system-frameworks': 'Frameworks del sistema', 'spotlight': 'Spotlight', 'node': 'Node.js',
    'netdata': 'Netdata', 'kernel_task': 'Núcleo de macOS', 'python': 'Python', 'claude': 'Claude Code',
    'codex': 'Codex', 'X': 'Otros procesos', 'agent': 'Agentes del sistema',
}

# macOS temperature sensors, grouped by what they measure. Sensors whose meaning is
# not documented (PMU tdev*, tcal, TP3w; two of them read -21 °C) are left out.
SENSOR_GROUPS = [
    ('p', 'Núcleos de rendimiento', ('pACC MTR',)),
    ('e', 'Núcleos de eficiencia', ('eACC MTR',)),
    ('gpu', 'GPU', ('GPU MTR',)),
    ('soc', 'Resto del chip', ('SOC MTR', 'PMGR SOC Die')),
    ('ane', 'Neural Engine', ('ANE MTR',)),
    ('isp', 'Procesador de imagen', ('ISP MTR',)),
    ('pmu', 'Gestión de energía', ('PMU tdie', 'PMU2 tdie')),
    ('ssd', 'SSD', ('NAND',)),
    ('bat', 'Batería', ('gas gauge battery',)),
]

# ---------------------------------------------------------------------------
# macmon: one long-running process streaming a JSON line every 5 s.
MACMON_STATE = {'line': None, 'at': 0}


def macmon_reader():
    while True:
        try:
            process = subprocess.Popen([MACMON, 'pipe', '-i', str(SAMPLE_EVERY * 1000)],
                                       stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            for line in process.stdout:
                try:
                    MACMON_STATE.update(line=json.loads(line), at=time.time())
                except ValueError:
                    continue
            process.wait()
        except OSError:
            pass
        time.sleep(10)


def read_memory():
    pages, size = {}, None
    for line in run('/usr/bin/vm_stat').splitlines():
        if 'page size of' in line:
            size = number(line.split('page size of')[1].split()[0])
        elif ':' in line:
            key, value = line.split(':', 1)
            value = value.strip().rstrip('.')
            if value.isdigit():
                pages[key.strip().strip('"')] = int(value)
    try:
        gib = lambda key: pages[key] * size / 2**30
        apps = gib('Anonymous pages') - gib('Pages purgeable')
        wired, comp = gib('Pages wired down'), gib('Pages occupied by compressor')
    except (KeyError, TypeError):
        return {}
    return {'ram': round(apps + wired + comp, 3), 'apps': round(apps, 3), 'wired': round(wired, 3), 'comp': round(comp, 3)}


BATTERY_STATE = {'acc': None, 'watts': None, 'health': None, 'healthAt': 0}
HEALTH_NAMES = {'Good': 'Normal', 'Fair': 'Aceptable', 'Poor': 'Mala',
                'Service Recommended': 'Se recomienda revisión'}


def signed(value):
    """ioreg prints negative battery currents as unsigned 64-bit integers."""
    return value - 2**64 if isinstance(value, int) and value >= 2**63 else value


def battery_health():
    """Apple's own maximum-capacity figure and condition, refreshed every 10 min."""
    if time.time() - BATTERY_STATE['healthAt'] > 600:
        BATTERY_STATE['healthAt'] = time.time()
        try:
            items = json.loads(run('/usr/sbin/system_profiler', '-json', 'SPPowerDataType', timeout=10))['SPPowerDataType']
            info = next(i for i in items if i.get('_name') == 'spbattery_information')['sppower_battery_health_info']
            BATTERY_STATE['health'] = {
                'capacity': number(''.join(c for c in info.get('sppower_battery_health_maximum_capacity', '') if c.isdigit())),
                'condition': HEALTH_NAMES.get(info.get('sppower_battery_health'), info.get('sppower_battery_health'))}
        except (ValueError, KeyError, StopIteration, TypeError):
            BATTERY_STATE['health'] = None
    return BATTERY_STATE['health']


def read_battery():
    """Battery state and measured whole-Mac power; None on Macs without a battery.

    The gauge publishes new figures about once a minute. Power is the average of
    its system-load accumulator between two publications, so it is a measured
    one-minute mean rather than macmon's SMC estimate.
    """
    try:
        battery = plistlib.loads(run('/usr/sbin/ioreg', '-rn', 'AppleSmartBattery', '-a').encode())[0]
    except (ValueError, IndexError, plistlib.InvalidFileException):
        return None
    if not battery.get('BatteryInstalled'):
        return None
    telemetry = battery.get('PowerTelemetryData') or {}
    updated = battery.get('UpdateTime')
    acc = (updated, telemetry.get('AccumulatedSystemLoad'), telemetry.get('SystemLoadAccumulatorCount'))
    previous = BATTERY_STATE['acc']
    if all(finite(v) for v in acc):
        if previous and acc[0] != previous[0]:
            count = acc[2] - previous[2]
            if count > 0 and acc[0] - previous[0] < 180:
                BATTERY_STATE['watts'] = round((acc[1] - previous[1]) / count / 1000, 2)
            else:
                BATTERY_STATE['watts'] = None
        if not previous or acc[0] != previous[0]:
            BATTERY_STATE['acc'] = acc
        if BATTERY_STATE['watts'] is None and finite(telemetry.get('SystemLoad')):
            BATTERY_STATE['watts'] = round(telemetry['SystemLoad'] / 1000, 2)  # first reading: instantaneous
    fresh = finite(updated) and time.time() - updated < 180
    adapter = battery.get('AdapterDetails') or {}
    plugged, charging = bool(battery.get('ExternalConnected')), bool(battery.get('IsCharging'))
    minutes = lambda key: battery.get(key) if finite(battery.get(key)) and 0 < battery[key] < 65535 else None
    amps, volts = signed(battery.get('InstantAmperage')), battery.get('Voltage')
    return {'percent': battery.get('CurrentCapacity'), 'plugged': plugged, 'charging': charging,
            'full': bool(battery.get('FullyCharged')),
            'minutesLeft': None if plugged else minutes('TimeRemaining'),
            'minutesToFull': minutes('AvgTimeToFull') if charging else None,
            'adapterW': adapter.get('Watts') if plugged else None,
            'batteryW': round(volts * amps / 1e6, 1) if finite(volts) and finite(amps) else None,
            'systemW': BATTERY_STATE['watts'] if fresh else None,
            'cycles': battery.get('CycleCount'), 'designCycles': battery.get('DesignCycleCount9C'),
            'health': battery_health(), 'updatedAt': updated}


def read_sensors():
    try:
        data = json.loads(run(str(ROOT / 'mac-sensors')))
    except ValueError:
        return None
    groups = []
    for key, label, prefixes in SENSOR_GROUPS:
        sensors = sorted((name, round(value, 1)) for name, value in data.get('temps', {}).items()
                         if name.startswith(prefixes) and 0 < value < 150)
        if sensors:
            values = [v for _, v in sensors]
            groups.append({'key': key, 'label': label, 'sensors': sensors,
                           'avg': round(sum(values) / len(values), 1), 'max': max(values)})
    return {'groups': groups, 'rawTemps': data.get('temps', {}),
            'fan': data.get('fan') or {}, 'fans': data.get('fans') or [], 'thermal': data.get('thermal')}


def sample():
    """One real reading of everything Netdata does not keep. Missing sources stay missing."""
    row = {'t': time.time()}
    sensors = read_sensors()
    if sensors:
        by_key = {g['key']: g for g in sensors['groups']}
        for key, field in (('p', 'pa'), ('e', 'ea'), ('gpu', 'g'), ('soc', 'soc'), ('ssd', 'ssd'), ('pmu', 'pmu'),
                           ('bat', 'bt')):
            if key in by_key:
                row[field] = by_key[key]['avg']
        if 'p' in by_key:
            row['pm'] = by_key['p']['max']
        # Every fan comes from the same SMC read, so the figures always agree.
        for index, fan in enumerate(sensors['fans'][:2]):
            if finite(fan.get('rpm')) and fan['rpm'] >= 0:
                row[f'f{index + 1}'] = round(fan['rpm'])
    row.update(read_memory())
    line = MACMON_STATE['line'] if time.time() - MACMON_STATE['at'] < 3 * SAMPLE_EVERY else None
    if line:
        for source, field in (('cpu_power', 'cw'), ('gpu_power', 'gw'), ('ane_power', 'aw'),
                              ('sys_power', 'sw'), ('ecpu_freq_mhz', 'ef'),
                              ('pcpu_freq_mhz', 'pf'), ('gpu_freq_mhz', 'gf')):
            value = line.get(source)
            if finite(value) and value >= 0 and (field != 'sw' or value > 0):
                row[field] = round(value, 3)
        # Some Apple Silicon models expose CPU/GPU temperatures through macmon
        # rather than named HID cluster sensors. Keep the aggregate CPU reading
        # separate: it is not a fabricated performance/efficiency-cluster value.
        temps = line.get('temp') or {}
        for source, field in (('cpu_temp_avg', 'ca'), ('gpu_temp_avg', 'g')):
            value = temps.get(source)
            if field not in row and finite(value) and 0 < value < 150:
                row[field] = round(value, 2)
        fans = line.get('fans') or []
        if 'f2' not in row and len(fans) > 1 and finite(fans[1].get('rpm')) and fans[1]['rpm'] >= 0:
            row['f2'] = round(fans[1]['rpm'])
        cores = line.get('ecpu_cores', []) + line.get('pcpu_cores', [])
        if cores and all(isinstance(c.get('active_ratio'), (int, float)) and
                         math.isfinite(c['active_ratio']) for c in cores):
            row['c'] = [round(100 * c['active_ratio'], 1) for c in cores]
    # Power is reported by macOS/macmon and explicitly labelled as estimated.
    # macmon's unavailable system-power sentinel (0) stays absent above.
    battery = read_battery() if HAS_BATTERY else None
    if battery:
        if finite(battery['percent']):
            row['bp'] = battery['percent']
        if battery['systemW'] is not None:
            row['bw'] = battery['systemW']
    detail = {'sensors': sensors, 'macmon': line, 'macmonAt': MACMON_STATE['at'] if line else None,
              'battery': battery}
    now = dict(POOL.map(latest, CURRENT.items()))
    try:
        fs = os.statvfs('/System/Volumes/Data')
        space = {'free': fs.f_bavail * fs.f_frsize, 'total': fs.f_blocks * fs.f_frsize}
    except OSError:
        space = None
    row['v'] = 2
    row['reading'] = {'machine': MACHINE, 'net': NET, 'detail': detail, 'now': now, 'space': space,
                      'pressure': number(run('/usr/sbin/sysctl', '-n', 'kern.memorystatus_vm_pressure_level')),
                      'swapUsage': run('/usr/sbin/sysctl', '-n', 'vm.swapusage') or None,
                      'apps': top_apps(), 'ssd': ssd_health()}
    row['collectedAt'] = time.time()
    return row, detail


HAS_BATTERY = read_battery() is not None
MACHINE['battery'] = HAS_BATTERY

LOG = ROOT / 'samples.jsonl'
DATABASE = ROOT / 'samples.sqlite3'
SAMPLES = collections.deque(maxlen=86400 // SAMPLE_EVERY + 20)
SAMPLES_LOCK = threading.Lock()
LATEST = {'row': None, 'detail': None}
RECORDING = {'savedAt': None, 'error': None, 'firstFullAt': None, 'loadWarnings': 0}
OLD_FIELDS = ('t', 'pa', 'pm', 'ea', 'g', 'ssd', 'ram', 'apps', 'wired', 'comp')  # samples from the first version


def open_store():
    db = sqlite3.connect(DATABASE, timeout=3)
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('PRAGMA synchronous=FULL')
    db.execute('CREATE TABLE IF NOT EXISTS samples (t REAL PRIMARY KEY, payload TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT)')
    return db


def load_log(db):
    """Import legacy measurements once, without rewriting or deleting the original."""
    cutoff = time.time() - 86400
    if not db.execute("SELECT 1 FROM metadata WHERE key='legacy_imported'").fetchone():
        if LOG.exists():
            with LOG.open() as log:
                for line in log:
                    try:
                        row = json.loads(line)
                        if isinstance(row, list):
                            row = {k: v for k, v in zip(OLD_FIELDS, row) if v is not None}
                        if not isinstance(row, dict) or not finite(row.get('t')):
                            raise ValueError('invalid timestamp')
                        if cutoff <= row['t'] <= time.time():
                            db.execute('INSERT OR IGNORE INTO samples VALUES (?, ?)',
                                       (row['t'], json.dumps(row, allow_nan=False, separators=(',', ':'))))
                    except (ValueError, TypeError):
                        RECORDING['loadWarnings'] += 1
        db.execute("INSERT INTO metadata VALUES ('legacy_imported', '1')")
        db.commit()
    loaded = []
    first_full = None
    for (payload,) in db.execute('SELECT payload FROM samples WHERE t>=? ORDER BY t', (cutoff,)):
        row = json.loads(payload)
        loaded.append({k: v for k, v in row.items() if k != 'reading'})
        if row.get('v') == 2 and first_full is None:
            first_full = row['t']
    with SAMPLES_LOCK:
        SAMPLES.clear()
        SAMPLES.extend(loaded)
        RECORDING['firstFullAt'] = first_full
    if RECORDING['loadWarnings']:
        logging.warning('Skipped %s invalid legacy rows; original file preserved', RECORDING['loadWarnings'])


def save_sample(db, row):
    payload = json.dumps(row, allow_nan=False, separators=(',', ':'))
    with db:
        db.execute('INSERT INTO samples VALUES (?, ?)', (row['t'], payload))
        db.execute('DELETE FROM samples WHERE t < ?', (time.time() - 86400,))


def sampler():
    db, clocks = None, None
    while True:
        time.sleep(SAMPLE_EVERY - time.time() % SAMPLE_EVERY + 0.5)
        # Wall time keeps running while the Mac sleeps; CLOCK_UPTIME_RAW does not.
        # The difference is time asleep, so the page can label that gap as rest.
        now = (time.time(), time.clock_gettime(time.CLOCK_UPTIME_RAW))
        slept = (now[0] - clocks[0]) - (now[1] - clocks[1]) if clocks else 0
        clocks = now
        if slept > 2 * SAMPLE_EVERY:
            BATTERY_STATE['acc'] = BATTERY_STATE['watts'] = None  # don't average across sleep
        try:
            if db is None:
                db = open_store()
                load_log(db)
            row, detail = sample()
            if slept > 2 * SAMPLE_EVERY:
                row['sl'] = round(slept)
            save_sample(db, row)
        except Exception as error:
            logging.exception('Sample collection/persistence failed')
            with SAMPLES_LOCK:
                RECORDING['error'] = str(error)
            if db is not None:
                db.close()
                db = None
            continue
        with SAMPLES_LOCK:
            SAMPLES.append({k: v for k, v in row.items() if k != 'reading'})
            LATEST.update(row=row, detail=detail)
            RECORDING.update(savedAt=row['t'], error=None)
            if RECORDING['firstFullAt'] is None:
                RECORDING['firstFullAt'] = row['t']


LOCAL_SCALARS = ('ca', 'f1', 'f2', 'bp', 'bw', 'bt', 'pa', 'pm', 'ea', 'g', 'soc', 'ssd', 'pmu', 'ram', 'cw', 'gw', 'aw', 'sw', 'ef', 'pf', 'gf')


def sleeps(seconds):
    """Periods the Mac spent asleep inside the shown range, as [start, end]."""
    start = time.time() - seconds
    with SAMPLES_LOCK:
        return [[max(start, r['t'] - r['sl']), r['t']] for r in SAMPLES if r.get('sl') and r['t'] >= start]


def local_history(seconds):
    """Average the 5 s samples into POINTS buckets; a gap in sampling stays a gap."""
    start, width = time.time() - seconds, seconds / POINTS
    with SAMPLES_LOCK:
        rows = [row for row in SAMPLES if row['t'] >= start]
    buckets = collections.defaultdict(list)
    for row in rows:
        buckets[int((row['t'] - start) // width)].append(row)
    names = list(LOCAL_SCALARS) + [f'c{i}' for i in range(MACHINE['cores'] or 0)]
    out = {name: [] for name in names}
    previous = None
    for index in sorted(buckets):
        group = buckets[index]
        t = sum(r['t'] for r in group) / len(group)
        if previous is not None and min(r['t'] for r in group) - previous > max(1.5 * width, 1.5 * SAMPLE_EVERY):
            for name in names:
                out[name].append([previous + 1, None])
        for name in names:
            if name.startswith('c') and name[1:].isdigit():
                i = int(name[1:])
                values = [r['c'][i] for r in group if 'c' in r and len(r['c']) > i]
            else:
                values = [r[name] for r in group if r.get(name) is not None]
            precision = 4 if name in ('cw', 'gw', 'aw') else 2
            out[name].append([t, round(sum(values) / len(values), precision) if values else None])
        previous = max(r['t'] for r in group)
    return out


# ---------------------------------------------------------------------------
CACHE = {}
LOCKS = {key: threading.Lock() for key in list(RANGES) + ['apps', 'ssd']}
POOL = concurrent.futures.ThreadPoolExecutor(max_workers=8)


def fetch(path, **params):
    with urllib.request.urlopen(BASE + path + '?' + urllib.parse.urlencode(params), timeout=4) as response:
        return json.load(response)


def rows_of(chart, after, points):
    data = fetch('/api/v1/data', chart=chart, after=-after, points=points, format='json', group='average')
    names = data['labels'][1:]
    return sorted(((row[0], dict(zip(names, row[1:]))) for row in data['data']), key=lambda row: row[0])


def history(item, seconds):
    key, (chart, funcs) = item
    try:
        rows = rows_of(chart, seconds, POINTS)
    except Exception:
        return key, None
    out = {}
    for name, func in funcs.items():
        points = []
        for t, row in rows:
            try:
                value = func(row)
                points.append([t, round(value, 3) if finite(value) else None])
            except (TypeError, KeyError, ValueError):
                points.append([t, None])
        out[name] = points
    return key, out


def latest(item):
    key, chart = item
    try:
        rows = rows_of(chart, 10, 10)
        valid = rows and rows[-1][1] and all(finite(v) for v in rows[-1][1].values())
        return key, {'t': rows[-1][0], **rows[-1][1]} if valid and 0 <= time.time() - rows[-1][0] < 45 else None
    except Exception:
        return key, None


def top_apps():
    def query(context):
        data = fetch('/api/v3/data', contexts=context, group_by='instance', after=-30, points=1, format='json2')
        result = data['result']
        if not result['data'] or time.time() - result['data'][0][0] >= 45:
            raise ValueError('stale app readings')
        values = []
        for label, value in zip(result['labels'][1:], result['data'][0][1:]):
            name = label.split('@')[0].removeprefix('app.').rsplit('_' + context.split('.', 1)[1], 1)[0]
            amount = value[0] if isinstance(value, list) else value
            if finite(amount) and amount > 0:
                values.append([ALIASES.get(name, name.replace('_', ' ')), round(amount, 2)])
        return sorted(values, key=lambda pair: -pair[1])[:6], result['data'][0][0]

    with LOCKS['apps']:
        if time.time() - CACHE.get('apps', (0, None))[0] < 10:
            return CACHE['apps'][1]
        try:
            cpu, cpu_at = query('app.cpu_utilization')
            mem, mem_at = query('app.mem_usage')
            apps = {'cpu': cpu, 'mem': mem, 'cpuAt': cpu_at, 'memAt': mem_at}
        except Exception:
            apps = None
        CACHE['apps'] = (time.time(), apps)
        return apps


def ssd_health():
    with LOCKS['ssd']:
        if time.time() - CACHE.get('ssd', (0, None))[0] < 600:
            return CACHE['ssd'][1]
        try:
            # smartctl's exit status is a bit mask that is non-zero even for a healthy read.
            result = subprocess.run([SMARTCTL, '-j', '-a', 'disk0'], capture_output=True, text=True, timeout=15)
            data = json.loads(result.stdout)
            log = data['nvme_smart_health_information_log']
            unit = 512_000  # NVMe "data unit"
            health = {
                'model': data.get('model_name'), 'passed': data.get('smart_status', {}).get('passed'),
                'used': log['percentage_used'], 'spare': log['available_spare'],
                'written': log['data_units_written'] * unit, 'read': log['data_units_read'] * unit,
                'hours': log['power_on_hours'], 'unsafe': log['unsafe_shutdowns'],
                'errors': log['media_errors'], 'warning': log['critical_warning'], 'temp': log['temperature'],
                'capacity': data.get('user_capacity', {}).get('bytes'),
                'partial': bool(result.returncode & 7), 'at': time.time(),
            }
        except (OSError, subprocess.SubprocessError, ValueError, KeyError, TypeError):
            health = None
        CACHE['ssd'] = (time.time(), health)
        return health


def snapshot(seconds):
    with LOCKS[seconds]:
        cached = CACHE.get(seconds)
        if cached and time.time() - cached['at'] < RANGES[seconds]:
            series = cached['series']
        else:
            series = dict(POOL.map(lambda item: history(item, seconds), SOURCES.items()))
            series['local'] = local_history(seconds)
            CACHE[seconds] = {'at': time.time(), 'series': series}
    with SAMPLES_LOCK:
        row, detail = LATEST['row'], LATEST['detail']
        recording = dict(RECORDING)
    fresh = row is not None and time.time() - row['t'] < 4 * SAMPLE_EVERY
    reading = row['reading'] if fresh else {}
    now = {key: value if value and time.time() - value['t'] < 45 else None
           for key, value in reading.get('now', {}).items()}
    now = {key: now.get(key) for key in CURRENT}
    recording['missing'] = [key for key, value in now.items() if value is None]
    expected = ('g', 'ssd', 'ram', 'apps', 'wired', 'comp', 'cw', 'gw', 'aw', 'sw', 'ef', 'pf', 'gf', 'c')
    recording['missing'] += [key for key in expected if not fresh or row.get(key) is None]
    if not fresh or (row.get('pa') is None and row.get('ca') is None):
        recording['missing'].append('cpu-temperature')
    for key in ('space', 'pressure', 'apps', 'ssd'):
        if reading.get(key) is None:
            recording['missing'].append(key)
    if not fresh or not detail or (detail.get('sensors') or {}).get('thermal') is None:
        recording['missing'].append('thermal')
    if not fresh or not detail or (detail.get('sensors') or {}).get('fan', {}).get('rpm') is None:
        recording['missing'].append('fan-rpm')
    if HAS_BATTERY and (not fresh or not (detail or {}).get('battery')):
        recording['missing'].append('battery')
    recording['healthy'] = fresh and recording['error'] is None
    return {'at': time.time(), 'range': seconds, 'machine': MACHINE, 'net': NET,
            'pressure': reading.get('pressure'), 'swapUsage': reading.get('swapUsage'),
            'space': reading.get('space'), 'series': series, 'now': now,
            'local': {k: v for k, v in row.items() if k != 'reading'} if fresh else None,
            'detail': detail if fresh else None, 'apps': reading.get('apps'), 'ssd': reading.get('ssd'),
            'sleeps': sleeps(seconds), 'recording': recording}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parts = urllib.parse.urlsplit(self.path)
        path = parts.path.rstrip('/')
        name = path.rsplit('/', 1)[-1]
        if path.endswith('/api/snapshot'):
            seconds = number(urllib.parse.parse_qs(parts.query).get('range', ['300'])[0]) or 300
            if seconds not in RANGES:
                seconds = 300
            data, content_type = json.dumps(snapshot(seconds), allow_nan=False, separators=(',', ':')).encode(), 'application/json; charset=utf-8'
        elif path in ('', PANEL_PATH, PANEL_PATH + '/index.html', '/index.html'):
            page = (ROOT / 'index.html').read_text().replace('__PANEL_PATH__', PANEL_PATH)
            data, content_type = page.encode(), 'text/html; charset=utf-8'
        elif name in ICONS:
            data, content_type = (ROOT / ICONS[name][0]).read_bytes(), ICONS[name][1]
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; base-uri 'none'; form-action 'none'")
        self.end_headers()
        try:
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, fmt, *args):
        if args and str(args[1]) not in ('200', '204'):
            super().log_message(fmt, *args)


TAILNET = (ipaddress.ip_network('100.64.0.0/10'), ipaddress.ip_network('fd7a:115c:a1e0::/48'))
FALLBACK_PORT = 8088


class TailnetHandler(Handler):
    # Plain-HTTP fallback on this Mac's Tailscale IP, for devices without MagicDNS.
    # Only Tailscale peers are answered (the macOS firewall is off, so the IP check matters).
    def handle_one_request(self):
        if not any(ipaddress.ip_address(self.client_address[0]) in net for net in TAILNET):
            self.close_connection = True
            return
        super().handle_one_request()


def tailscale_ipv4():
    # Only a real Tailscale address; the CLI prints errors on stdout.
    for line in run(TAILSCALE, 'ip', '-4').splitlines():
        try:
            if ipaddress.ip_address(line) in TAILNET[0]:
                return line
        except ValueError:
            pass
    return None


def serve_tailnet_fallback():
    while True:
        address = tailscale_ipv4()
        try:
            if not address:
                raise OSError('no Tailscale address yet')
            fallback = LocalServer((address, FALLBACK_PORT), TailnetHandler)
            fallback.daemon_threads = True
            fallback.serve_forever()
        except OSError:
            time.sleep(30)


class LocalServer(ThreadingHTTPServer):
    def server_bind(self):
        # HTTPServer normally does a reverse-DNS lookup here. Loopback needs none.
        socketserver.TCPServer.server_bind(self)
        self.server_name, self.server_port = 'localhost', self.server_address[1]


if __name__ == '__main__':
    server = LocalServer(('127.0.0.1', 20000), Handler)
    server.daemon_threads = True
    targets = (macmon_reader, sampler)
    # HTTPS Serve is sufficient by default; direct tailnet HTTP is an explicit opt-in.
    if os.environ.get('PANEL_TAILNET_FALLBACK') == '1':
        targets += (serve_tailnet_fallback,)
    for target in targets:
        threading.Thread(target=target, daemon=True).start()
    server.serve_forever()
