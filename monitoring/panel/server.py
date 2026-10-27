#!/opt/homebrew/bin/python3
"""Private, read-only dashboard for this Mac.

Every number comes from a real source; missing values are never filled in.
System power is macmon's hardware-derived estimate, not an outlet measurement:
  - Netdata (127.0.0.1:19999): CPU and GPU use, swap, network, disk I/O, apps, load, uptime.
  - macmon (Homebrew, no root): per-core activity and MHz, cluster/GPU MHz, CPU/GPU/ANE/system power.
  - mac-sensors (this folder): macOS's own temperature sensors, SMC fan RPM/min/max, thermal state.
  - vm_stat / sysctl: memory as Activity Monitor counts it, memory pressure.
  - smartctl (Homebrew): SSD health.
Readings Netdata keeps no history for are sampled here every 5 s into samples.jsonl (24 h).
"""
import collections
import concurrent.futures
import ipaddress
import json
import math
import os
import socketserver
import subprocess
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = 'http://127.0.0.1:19999'
ICONS = {
    'favicon.svg': ('favicon.svg', 'image/svg+xml'),
    'favicon.ico': ('favicon-32.png', 'image/png'),
    'favicon-32.png': ('favicon-32.png', 'image/png'),
    'apple-touch-icon.png': ('apple-touch-icon.png', 'image/png'),
}
RANGES = {300: 4, 3600: 15, 21600: 30, 86400: 60}  # seconds shown -> cache seconds
POINTS = 150
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
    except ValueError:
        return None


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
    return {'groups': groups, 'fan': data.get('fan') or {}, 'thermal': data.get('thermal')}


def sample():
    """One real reading of everything Netdata does not keep. Missing sources stay missing."""
    row = {'t': round(time.time())}
    sensors = read_sensors()
    if sensors:
        by_key = {g['key']: g for g in sensors['groups']}
        for key, field in (('p', 'pa'), ('e', 'ea'), ('gpu', 'g'), ('soc', 'soc'), ('ssd', 'ssd'), ('pmu', 'pmu')):
            if key in by_key:
                row[field] = by_key[key]['avg']
        if 'p' in by_key:
            row['pm'] = by_key['p']['max']
    row.update(read_memory())
    line = MACMON_STATE['line'] if time.time() - MACMON_STATE['at'] < 3 * SAMPLE_EVERY else None
    if line:
        for source, field in (('cpu_power', 'cw'), ('gpu_power', 'gw'), ('ane_power', 'aw'),
                              ('sys_power', 'sw'), ('ecpu_freq_mhz', 'ef'),
                              ('pcpu_freq_mhz', 'pf'), ('gpu_freq_mhz', 'gf')):
            value = line.get(source)
            if isinstance(value, (int, float)) and math.isfinite(value) and value >= 0:
                # macmon emits 0 when its system-power SMC source is unavailable.
                if field != 'sw' or value > 0:
                    row[field] = round(value, 3)
        cores = line.get('ecpu_cores', []) + line.get('pcpu_cores', [])
        if cores and all(isinstance(c.get('active_ratio'), (int, float)) and
                         math.isfinite(c['active_ratio']) for c in cores):
            row['c'] = [round(100 * c['active_ratio'], 1) for c in cores]
    detail = {'sensors': sensors, 'macmon': line}
    return row, detail


LOG = ROOT / 'samples.jsonl'
SAMPLES = collections.deque(maxlen=86400 // SAMPLE_EVERY + 20)
SAMPLES_LOCK = threading.Lock()
LATEST = {'row': None, 'detail': None}
OLD_FIELDS = ('t', 'pa', 'pm', 'ea', 'g', 'ssd', 'ram', 'apps', 'wired', 'comp')  # samples from the first version


def load_log():
    cutoff = time.time() - 86400
    try:
        for line in LOG.read_text().splitlines():
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if isinstance(row, list):
                row = {k: v for k, v in zip(OLD_FIELDS, row) if v is not None}
            if isinstance(row, dict) and row.get('t', 0) >= cutoff:
                SAMPLES.append(row)
    except OSError:
        pass
    old = ROOT / 'temps.jsonl'
    if old.exists():
        old.unlink()
    LOG.write_text(''.join(json.dumps(r, separators=(',', ':')) + '\n' for r in SAMPLES))


def sampler():
    load_log()
    while True:
        time.sleep(SAMPLE_EVERY - time.time() % SAMPLE_EVERY + 0.5)
        try:
            row, detail = sample()
        except Exception:
            continue
        with SAMPLES_LOCK:
            SAMPLES.append(row)
            LATEST.update(row=row, detail=detail)
            with LOG.open('a') as log:
                log.write(json.dumps(row, separators=(',', ':')) + '\n')
            if LOG.stat().st_size > 12_000_000:  # ~1.5 days of rows: keep the last 24 h
                LOG.write_text(''.join(json.dumps(r, separators=(',', ':')) + '\n' for r in SAMPLES))


LOCAL_SCALARS = ('pa', 'pm', 'ea', 'g', 'soc', 'ssd', 'pmu', 'ram', 'cw', 'gw', 'aw', 'sw', 'ef', 'pf', 'gf')


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
        t = round(start + (index + .5) * width)
        if previous is not None and t - previous > max(3 * width, 3 * SAMPLE_EVERY + 1):
            for name in names:
                out[name].append([previous + 1, None])
        group = buckets[index]
        for name in names:
            if name.startswith('c') and name[1:].isdigit():
                i = int(name[1:])
                values = [r['c'][i] for r in group if 'c' in r and len(r['c']) > i]
            else:
                values = [r[name] for r in group if r.get(name) is not None]
            precision = 4 if name in ('cw', 'gw', 'aw') else 2
            out[name].append([t, round(sum(values) / len(values), precision) if values else None])
        previous = t
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
                points.append([t, round(func(row), 3)])
            except (TypeError, KeyError):
                points.append([t, None])
        out[name] = points
    return key, out


def latest(item):
    key, chart = item
    try:
        rows = [row for row in rows_of(chart, 10, 10) if any(v is not None for v in row[1].values())]
        return key, {'t': rows[-1][0], **rows[-1][1]} if rows and time.time() - rows[-1][0] < 45 else None
    except Exception:
        return key, None


def top_apps():
    def query(context):
        data = fetch('/api/v3/data', contexts=context, group_by='instance', after=-30, points=1, format='json2')
        result = data['result']
        values = []
        for label, value in zip(result['labels'][1:], result['data'][0][1:]):
            name = label.split('@')[0].removeprefix('app.').rsplit('_' + context.split('.', 1)[1], 1)[0]
            amount = value[0] if isinstance(value, list) else value
            if amount:
                values.append([ALIASES.get(name, name.replace('_', ' ')), round(amount, 2)])
        return sorted(values, key=lambda pair: -pair[1])[:6]

    with LOCKS['apps']:
        if time.time() - CACHE.get('apps', (0, None))[0] < 10:
            return CACHE['apps'][1]
        try:
            apps = {'cpu': query('app.cpu_utilization'), 'mem': query('app.mem_usage')}
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
    now = dict(POOL.map(latest, CURRENT.items()))
    with SAMPLES_LOCK:
        row, detail = LATEST['row'], LATEST['detail']
    fresh = row is not None and time.time() - row['t'] < 4 * SAMPLE_EVERY
    try:
        fs = os.statvfs('/')
        space = {'free': fs.f_bavail * fs.f_frsize, 'total': fs.f_blocks * fs.f_frsize}
    except OSError:
        space = None
    pressure = number(run('/usr/sbin/sysctl', '-n', 'kern.memorystatus_vm_pressure_level'))
    swap = run('/usr/sbin/sysctl', '-n', 'vm.swapusage')
    return {'at': time.time(), 'range': seconds, 'machine': MACHINE, 'net': NET, 'pressure': pressure,
            'swapUsage': swap or None, 'space': space, 'series': series, 'now': now,
            'local': row if fresh else None, 'detail': detail if fresh else None,
            'apps': top_apps(), 'ssd': ssd_health()}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parts = urllib.parse.urlsplit(self.path)
        path = parts.path.rstrip('/')
        name = path.rsplit('/', 1)[-1]
        if path.endswith('/api/snapshot'):
            seconds = number(urllib.parse.parse_qs(parts.query).get('range', ['300'])[0]) or 300
            if seconds not in RANGES:
                seconds = 300
            data, content_type = json.dumps(snapshot(seconds), separators=(',', ':')).encode(), 'application/json; charset=utf-8'
        elif path in ('', '/mini', '/mini/index.html', '/index.html'):
            data, content_type = (ROOT / 'index.html').read_bytes(), 'text/html; charset=utf-8'
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
    for target in (macmon_reader, sampler, serve_tailnet_fallback):
        threading.Thread(target=target, daemon=True).start()
    server.serve_forever()
