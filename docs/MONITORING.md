# Monitoring

The mini runs Netdata and a one-page panel built on top of it, to see at a
glance how it's doing from a Mac or the iPad: CPU and per-core activity, GPU,
memory pressure and swap, temperatures, the fan, power, network, the SSD's
health and the apps using the most. Both are free, have no Netdata Cloud
account and are only reachable inside the tailnet.

| What | Where it listens | Tailnet address |
|---|---|---|
| Netdata | `127.0.0.1:19999` | `https://<mini>.<tailnet>.ts.net:19999/` |
| Panel | `127.0.0.1:20000` | `https://<mini>.<tailnet>.ts.net:19999/mini/` |
| Panel, by IP | `<tailscale-ip>:8088` | `http://<tailscale-ip>:8088/mini/` |

The IP route is a fallback for clients without Tailscale DNS. It answers only
Tailscale addresses, because the macOS firewall is off on the mini.

Cost on the reference mini (M1, 8 GB): about 120 MB of RAM and under 1 % of
the CPU in total.

## Files

- [`monitoring/netdata.conf`](../monitoring/netdata.conf): Netdata on loopback
  only, without statsd or powermetrics.
- [`monitoring/panel/`](../monitoring/panel/):
  - `server.py`: joins Netdata, macmon, smartctl and macOS readings, keeps
    24 h of history in `samples.jsonl` and serves the page.
  - `index.html`: the page, in one file.
  - `mac-sensors.m`: a read-only reader for the HID temperatures, the SMC fan
    and macOS's thermal state.
  - The icons, and the LaunchAgent template.

## Install

1. Packages, from this repo's `Brewfile` (Python is the one `server.py`
   expects in `/opt/homebrew/bin`):

   ```sh
   brew bundle --file Brewfile
   ```

2. Netdata. Back up the existing config first. The repo's copy has a
   `__USER__` placeholder that is replaced with your account:

   ```sh
   cp /opt/homebrew/etc/netdata/netdata.conf ~/netdata.conf.before
   sed "s#__USER__#$(id -un)#" monitoring/netdata.conf \
     > /opt/homebrew/etc/netdata/netdata.conf
   brew services start netdata
   ```

3. The panel. LaunchAgents can't read `~/Documents`, `~/Desktop` or
   `~/Downloads`, so it runs from Application Support:

   Before installing, inspect the loaded agents. Existing setups may use
   `local.david.netdata-dashboard` rather than `local.serverfiles.panel`.
   Keep one agent only; agree on a migration before installing another
   label for the same port. The commands below are for a new installation.

   ```sh
   PANEL="$HOME/Library/Application Support/PanelMacMini"
   mkdir -p "$PANEL" ~/Library/LaunchAgents
   cp -R monitoring/panel/. "$PANEL/"
   clang -O2 -fobjc-arc -framework Foundation -framework IOKit \
     "$PANEL/mac-sensors.m" -o "$PANEL/mac-sensors"
   sed "s#__PANEL_DIR__#$PANEL#g" "$PANEL/local.serverfiles.panel.plist" \
     > ~/Library/LaunchAgents/local.serverfiles.panel.plist
   launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/local.serverfiles.panel.plist
   ```

4. Tailscale Serve. First read `tailscale status --json` (`BackendState`
   must be `Running`) and `tailscale serve status`, and keep every
   existing mapping; never run `tailscale serve reset`. These add port 19999
   only, inside the tailnet, without Funnel:

   ```sh
   tailscale serve --bg --https=19999 http://127.0.0.1:19999
   tailscale serve --bg --https=19999 --set-path=/mini http://127.0.0.1:20000
   ```

   These examples assume the routes are free or already belong to these
   services. An occupied port/path must not be overwritten. A different
   existing port means different client URLs; return those actual URLs
   using [CONNECTIONS.md](CONNECTIONS.md). Do not enable Funnel for monitoring.

## Check it

On the mini:

```sh
brew services info netdata
launchctl list | grep -E 'local\.(serverfiles\.panel|david\.netdata-dashboard)$'
curl -s http://127.0.0.1:19999/api/v1/info | head -c 200
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:20000/mini/
```

From a Mac or the iPad, with Tailscale on, open the panel's tailnet address.
The values should change every 5 seconds. Save it as a bookmark named `Stats`
on each client (dotfiles' `docs/MACOS_SETUP.md`, and [IPAD.md](IPAD.md)).
If the name does not resolve, first check that both Tailscale backends are
Running, then inspect Use Tailscale DNS on the client and its actual peer
DNSName. Diagnose competing VPN/DNS settings on the failing client before
changing them. Host-local HTTP checks do not verify the client route.

Netdata's welcome page offers to sign in; **Skip and use the dashboard
anonymously** is enough.

## Limits

- No per-core data in Netdata on macOS; the panel gets it from macmon.
- Exact thermal pressure needs `powermetrics` as root, so it's off. The panel
  shows macOS's own thermal state instead.
- The total power is macmon's SMC estimate, not an outlet measurement.
- Both services start at login, not at boot. After a restart they need the
  user's session, like the rest of the mini's LaunchAgents.
- Neither one controls the fan or runs stress tests.

## Update the panel

Edit the files here and copy them to the mini. A change to `index.html` shows
on reload; a change to `server.py` needs a restart. Detect the single installed
label first; this supports both the current template and the older setup:

```sh
if PANEL_LABEL=$(launchctl list | awk '
  $3 == "local.serverfiles.panel" || $3 == "local.david.netdata-dashboard" {
    count++; label=$3
  }
  END { if (count != 1) exit 1; print label }'); then
  launchctl kickstart -k "gui/$(id -u)/$PANEL_LABEL"
else
  echo "Expected one panel LaunchAgent; inspect missing or duplicate agents."
fi
```

If something fails, read `server-error.log` in the panel's folder.

## Remove it

Inspect the installed label and existing Serve routes first. The example is
for the new template label and a monitoring-only port 19999. Do not turn off
the whole port if another service owns a route on it; remove only the
monitoring mappings and use the actual agent label/file.

```sh
tailscale serve --https=19999 off
launchctl bootout gui/$(id -u)/local.serverfiles.panel
rm ~/Library/LaunchAgents/local.serverfiles.panel.plist
rm -r "$HOME/Library/Application Support/PanelMacMini"
brew services stop netdata
```
