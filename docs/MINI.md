# The mini's settings

What has to be turned on for the mini to work unattended: after a restart or a
power cut it has to log in, open its apps and start its services without
anyone at the screen. Most of it is manual, in System Settings or in each app.

## macOS

| Setting | Where | Value |
|---|---|---|
| Automatic login | Users & Groups → Automatically log in as | Your account (`id -un`) |
| FileVault | Privacy & Security → FileVault | Off (automatic login needs it off) |
| Remote Login (SSH) | General → Sharing → Remote Login | On |
| Prevent sleep | Energy → Prevent automatic sleeping when the display is off | On |
| Start after a power failure | Energy → Start up automatically after a power failure | On |
| Wake for network access | Energy → Wake for network access | On |

Check them over SSH:

```sh
defaults read /Library/Preferences/com.apple.loginwindow autoLoginUser   # your account
fdesetup status                                                          # Off
pmset -g custom | grep -E ' sleep|autorestart|womp'   # sleep 0, autorestart 1, womp 1
```

The macOS firewall is off. That's why everything binds to `127.0.0.1` and
goes out through Tailscale; keep it that way for anything new.

## Open at login

General → Login Items → Open at Login:

- **Amphetamine**: keeps the mini awake. In its settings: start a session at
  launch, default duration **Indefinitely**, hide the Dock icon.
- **T3 Code**: has to be running for T3 Connect. Check the item points to the
  installed app (`T3 Code (Beta)`); after switching channel, the old item
  stays and points to an app that no longer exists.
- Raycast, Magnet, Macs Fan Control and Google Drive.

List them over SSH:

```sh
osascript -e 'tell application "System Events" to get the path of every login item'
```

A `missing value` in that list is an item whose app is gone; remove it and
add the right one.

## Apps

Development tools are selected with the user according to
[DEVELOPMENT.md](DEVELOPMENT.md), including whether Android or iOS builds,
emulators, databases and containers should run here. Do not copy the
MacBook's entire app list. Wispr Flow stays on the MacBook client and is
excluded from this mini's setup, as is AlDente.

- **Tailscale**: logged in, "Start on log in" on, Tailscale DNS on. It's the
  app's own setting, not a login item.
- **Jump Desktop Connect**: signed in to the Jump account, with Screen
  Recording and Accessibility allowed in Privacy & Security. It starts at boot
  by itself (its LaunchDaemon), before anyone logs in.
- **T3 Code**: Settings → Connections → T3 Connect on, signed in to the same
  account as the MacBook and the iPad.
- **VS Code Remote Tunnel**: named `mac-mini`, installed as a service with
  `code tunnel service install` and signed in with the same account as
  vscode.dev on the iPad. It runs as the LaunchAgent
  `com.visualstudio.code.tunnel`.

## What starts on its own

User LaunchAgents start at login, which is why automatic login matters:

| LaunchAgent | What | Where it's documented |
|---|---|---|
| `sh.brew.netdata` | Netdata | [MONITORING.md](MONITORING.md) |
| `local.serverfiles.panel` | The `Stats` panel | [MONITORING.md](MONITORING.md) |
| `com.visualstudio.code.tunnel` | VS Code Remote Tunnel | Above |

Older installs use `local.david.netdata-dashboard` for Stats. Inspect the
actual label before checking or restarting it; keep a single panel agent
and follow [MONITORING.md](MONITORING.md) for the detection command.

Other LaunchAgents (your own servers, for example) belong in this table too.
List yours with `launchctl list | grep -v com.apple`.

## Tailscale Serve on the mini

| Port | Goes to | Who reaches it |
|---|---|---|
| 19999 `/` | Netdata (`127.0.0.1:19999`) | Tailnet only |
| 19999 `/mini` | The `Stats` panel (`127.0.0.1:20000`) | Tailnet only |

Other projects may already own routes (Funnel included). Before adding one, read `tailscale serve status` and use another port.
Never run `tailscale serve reset`.
These are reference routes, not proof of the installed endpoints. Inspect
their actual ports, paths and privacy and hand over the real links following
[CONNECTIONS.md](CONNECTIONS.md).

## After a restart

Check from the MacBook, without touching the mini:

1. `ssh macmini` connects.
2. T3 Code shows the mini's environment.
3. Jump Desktop shows its desktop.
4. The `Stats` bookmark loads.
5. Run [`scripts/verify.sh`](../scripts/verify.sh) over SSH; it checks the
   settings and services above without changing anything.
