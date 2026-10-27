#!/bin/sh
# Read-only checks. Default: server; --role client skips server-only checks.
# Exit code = number of failed checks (capped at 125).
fail=0
role=server
ok()   { printf 'ok    %s\n' "$1"; }
bad()  { printf 'FAIL  %s\n' "$1"; fail=$((fail+1)); }
skip() { printf 'skip  %s\n' "$1"; }

case "$*" in
  '') ;;
  '--role server') role=server ;;
  '--role client') role=client ;;
  '--help'|'-h') echo 'Usage: verify.sh [--role server|client]'; exit 0 ;;
  *) echo 'Usage: verify.sh [--role server|client]' >&2; exit 2 ;;
esac

echo "host: $(hostname) user: $(id -un) model: $(sysctl -n hw.model) arch: $(uname -m) role: $role"

if [ "$role" = server ]; then
  if login_user=$(defaults read /Library/Preferences/com.apple.loginwindow autoLoginUser 2>/dev/null); then
    if [ "$login_user" = "$(id -un)" ]; then ok "automatic login is $(id -un)"
    else bad "automatic login is not $(id -un)"; fi
  else bad "cannot read automatic login setting"; fi

  if vault=$(fdesetup status 2>/dev/null); then
    case "$vault" in
      *'FileVault is Off.'*) ok 'FileVault off' ;;
      *) bad 'FileVault not confirmed off (automatic login requires it off)' ;;
    esac
  else bad 'cannot read FileVault state'; fi

  if power=$(pmset -g custom 2>/dev/null); then
    check_power() {
      if printf '%s\n' "$power" | awk -v key="$1" -v want="$2" '
        $1 == key { found++; if ($2 != want) wrong++ }
        END { exit !(found > 0 && wrong == 0) }'; then
        ok "$1 $2"
      else bad "$1 is missing or not $2"; fi
    }
    check_power sleep 0
    check_power autorestart 1
    check_power womp 1
  else bad 'cannot read power settings'; fi

  if nc -z -w 2 127.0.0.1 22 2>/dev/null; then ok 'SSH port 22 accepts connections'
  else bad 'SSH port 22 is not accepting connections'; fi
else skip 'server power policy, automatic login and SSH listener (client role)'; fi

# Prefer the app's own CLI to avoid a different Homebrew client version.
if [ -n "${SERVERFILES_TAILSCALE_CLI:-}" ]; then
  tailscale_cli=$SERVERFILES_TAILSCALE_CLI
elif [ -x /Applications/Tailscale.app/Contents/MacOS/Tailscale ]; then
  tailscale_cli=/Applications/Tailscale.app/Contents/MacOS/Tailscale
else tailscale_cli=$(command -v tailscale 2>/dev/null || true); fi
python_cli=$(command -v python3 2>/dev/null || true)
if [ -z "$tailscale_cli" ]; then
  bad 'Tailscale CLI not found'
elif [ -z "$python_cli" ]; then
  bad 'python3 required to read Tailscale JSON status'
elif ts_status=$(TAILSCALE_BE_CLI=1 "$tailscale_cli" status --json 2>/dev/null); then
  if backend=$(printf '%s' "$ts_status" | "$python_cli" -c '
import json, sys
state = json.load(sys.stdin).get("BackendState")
if not isinstance(state, str) or not state:
    raise SystemExit(1)
print(state)
' 2>/dev/null); then
    if [ "$backend" = Running ]; then ok 'Tailscale backend Running'
    else bad "Tailscale backend $backend (not connected)"; fi
  else bad 'cannot read Tailscale backend state'; fi
else bad 'cannot query Tailscale status'; fi

if [ "$role" = server ]; then
  if curl -fs -m 5 http://127.0.0.1:19999/api/v1/info >/dev/null; then ok 'Netdata answers'
  else bad 'Netdata not answering'; fi
  if [ "$(curl -s -m 5 -o /dev/null -w '%{http_code}' http://127.0.0.1:20000/mini/)" = 200 ]; then
    ok 'Stats panel answers'
  else bad 'Stats panel not answering'; fi
else skip 'Netdata and Stats (client role)'; fi

if login_items=$(osascript -e 'tell application "System Events" to get the path of every login item' 2>/dev/null); then
  if printf '%s\n' "$login_items" | grep -q 'missing value'; then bad 'login item with missing app'
  else ok 'no broken login items'; fi
else bad 'cannot read login items (check Automation permission)'; fi

[ "$fail" -le 125 ] || fail=125
exit "$fail"
