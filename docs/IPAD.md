# Working from an iPad

The iPad is a client of the Mac mini. Projects, terminal commands and builds
run on the mini. This guide describes the intended client setup; it has not
yet been verified on the iPad.

## Prepare the iPad

1. In the **App Store**, search for **Tailscale**, download it and connect
   it to the same private network as the mini, as described below.
2. In **Safari**, open [T3 Code](https://app.t3.codes/). Use Safari's share
   menu and choose **Add to Home Screen**. Name the shortcut `T3 Code`.
3. In **Safari**, open [VS Code Remote](https://vscode.dev/). Connect to the
   mini's remote tunnel, then use **Add to Home Screen** to save that remote
   page as `VS Code Remote`.
4. In the **App Store**, search for **Jump Desktop** and download it. This
   is the iPad client; the mini runs Jump Desktop Connect.
5. In the **App Store**, search for **Termius** and download it for the SSH
   terminal.
6. With Tailscale connected, add two bookmarks in **Safari** (share menu →
   **Add Bookmark**, or **Add to Home Screen**), with these names so it's
   clear which is which. The real `<tailnet>` name is in the Tailscale app.

   | Bookmark | What it opens | Address |
   |---|---|---|
   | `CLIProxy` | CLIProxyAPI's panel, on the MacBook | `https://<macbook>.<tailnet>.ts.net/management.html` |
   | `Stats` | The mini's monitoring panel ([MONITORING.md](MONITORING.md)) | `https://<mini>.<tailnet>.ts.net:19999/mini/` |

   `CLIProxy` asks for its management key; type it there, never in a chat.
   The agent should supply the real clickable URLs from the owning Macs,
   using [CONNECTIONS.md](CONNECTIONS.md), and distinguish tested links from
   those still awaiting an iPad check. Do not save these example placeholders
   or a temporary T3 pairing link as permanent service bookmarks.

T3 Code, VS Code Remote Tunnels and Jump Desktop use their own configured
remote connections; joining Tailscale alone does not set them up.

## Connect Tailscale

Open Tailscale on the iPad, sign in to the same tailnet as the mini and
allow the VPN configuration when prompted. Turn the connection on and check
that both devices appear and that the mini is available. Keep Tailscale
connected while using Termius or the private T3 connection below. See the
[official iOS and iPad installation guide](https://tailscale.com/docs/install/ios).

## Add the mini in Termius

Install [Termius for iPad](https://termius.com/download/ios), then create an
SSH host with:

- Label: `Mac mini` (a display name of your choice).
- Address: the mini's Tailscale IP or MagicDNS name, from Tailscale.
- Port: `22`.
- Username: your macOS account on the mini.
- Authentication: a key configured for this iPad and authorized on the mini.

Prepare macOS Remote Login on the mini and add the iPad key's public part to
that account's `~/.ssh/authorized_keys`, preserving existing entries. Keep
the private key in the client. Check the server's host-key fingerprint
against the mini before accepting the first connection.

The `macmini` alias in a Mac's `~/.ssh/config` does not automatically exist
on the iPad; configure the Termius host explicitly. These instructions use
macOS SSH over the Tailscale network.

After connecting, run `hostname` and `whoami` to confirm the machine and
account. For terminal work that should survive an SSH disconnect, use tmux
on the mini:

```sh
tmux new-session -A -s dev
```

Reconnect and run the same command to return to the session while the mini
and tmux remain running. This does not restore a session after a reboot.

## Open T3 Code

### Option 1: T3 Connect

Use this first for the existing setup.

1. On the mini, open T3 Code's **Settings → Connections**, sign in and
   enable **T3 Connect** for its environment. Keep T3 Code running.
2. On the iPad, open [app.t3.codes](https://app.t3.codes/) in Safari or from
   the Home Screen shortcut. Sign in to the same T3 Connect account.
3. Select the mini's environment and confirm its hostname in a terminal.

This route does not require Tailscale. Keep the iPad's Tailscale app for SSH
and private connections. See the official
[T3 Connect instructions](https://github.com/pingdotgg/t3code/blob/main/docs/user/remote-access.md#t3-connect)
and [web onboarding](https://github.com/pingdotgg/t3code/blob/main/docs/user/welcome-wizard.md).

### Option 2: Private connection through Tailscale

1. Connect Tailscale on both devices to the same tailnet.
2. On the mini, use **Settings → Connections → Tailscale HTTPS** and
   create a pairing link for that HTTPS endpoint.
3. On the iPad, open T3 Code's **Settings → Connections → Add environment**
   and paste the fresh pairing link. Confirm the mini's hostname.

The hosted web app needs HTTPS; a `100.x.x.x` address alone is not enough.
Pairing links are temporary credentials: keep them out of the repository.
The host must remain running for either route. See the official
[Tailscale HTTPS instructions](https://github.com/pingdotgg/t3code/blob/main/docs/user/remote-access.md#tailscale-https).

Before an agent enables Tailscale HTTPS on this mini, inspect its existing
`tailscale serve status`. The reference mini already uses Serve/Funnel for
other services. Preserve those mappings and choose another supported HTTPS
port if needed; do not reset the existing configuration. These are
configuration steps to perform later, not changes applied by this guide.

### If the mini does not connect

For T3 Connect, check that it is enabled on the mini and that both clients
use the same account. For the private route, check Tailscale on both devices,
the HTTPS endpoint and the pairing. Use a fresh link if the old one expired.
If the Home Screen shortcut asks to sign in or pair again, complete that
step there too. Opening the web page alone does not connect the mini.

## Open VS Code remotely

Open [vscode.dev](https://vscode.dev/) in Safari and connect to the mini
through **Remote Tunnels**. Sign in with the same account used to register
the mini's tunnel. You can also use the direct `vscode.dev/tunnel/...` link
provided by VS Code on the mini; add that page to the Home Screen after
connecting.

The mini needs Remote Tunnel Access enabled in VS Code, or its tunnel CLI
service running. Opening vscode.dev alone does not connect it to the mini.
Once connected, open a folder on the mini and check its hostname in the
integrated terminal. See the
[official Remote Tunnels guide](https://code.visualstudio.com/docs/remote/tunnels).

## Open the desktop

For the desktop, finish setup and permissions in Jump Desktop Connect on
the mini, pair it with Jump Desktop on the iPad and check that you can view
and control the desktop.

## Check before relying on it

- Connect by SSH and confirm the hostname and account.
- Disconnect and reconnect to the tmux session.
- Open T3 Code through T3 Connect and confirm that work runs on the mini.
- If configured, check the Tailscale HTTPS route with the iPad VPN connected.
- Connect through VS Code Remote Tunnels and check the integrated terminal.
- Open and control the desktop with Jump Desktop.
- Repeat the access checks from outside the home Wi-Fi.
- With local recovery available, test access after restarting the mini and
  record which tools require a graphical login or other manual action.

App installation, sign-ins, pairing and iPad permission prompts are manual
steps. An agent can prepare the host and guide these steps; a repository
clone does not configure the iPad automatically.
