# Connections and the links to give the user

Each link belongs to a particular host and service. A reachable web page
does not prove that the client is connected to the intended Mac.

| Access | Host | Where the real address comes from | Client check |
|---|---|---|---|
| SSH | Mac mini | The mini's entry in `tailscale status --json` and its macOS account; the MacBook uses the configured `macmini` alias | Connect and check `hostname` and `whoami` |
| Stats / Netdata | Mac mini | The mini's `tailscale serve status`, preserving its actual HTTPS port and `/mini/` path | Open from the MacBook or iPad with Tailscale connected; check recent, changing data |
| CLIProxy | MacBook | The MacBook's `tailscale serve status`; append `/management.html` to the endpoint that actually proxies CLIProxy | Open from the intended client; enter the management key in the page |
| T3 Connect | The selected Mac | `https://app.t3.codes/`, then sign in and choose the host's environment | Check the selected environment and run `hostname` in its terminal |
| T3 direct pairing | The Mac being paired | A fresh pairing link from that host's Settings → Connections; use its configured Tailscale HTTPS endpoint | Add the environment on the receiving device, then check its hostname |
| VS Code Remote Tunnels | Mac mini | The tunnel link printed or shown by the mini's VS Code, not a guessed tunnel name | Open a project and check the integrated terminal's hostname |
| Jump Desktop | Mac mini | The mini paired in Jump Desktop Connect; this is an app connection, not an invented web URL | View and control the intended desktop |

## Inspect before changing anything

On each Mac, use the CLI that matches its running Tailscale installation:

```sh
tailscale status --json
tailscale debug prefs
tailscale serve status
```

When using the app bundle directly in a noninteractive shell, run it with
`TAILSCALE_BE_CLI=1`. Read `BackendState` from the JSON: only `Running`
confirms the local backend is connected. A successful command exit, an old
Tailscale IP, or a saved Serve mapping does not confirm connectivity.

For DNS problems, check that both devices are connected first, then inspect
the peer and `CorpDNS` (Use Tailscale DNS) on the client. Use the actual peer's
`DNSName`, not a hostname assembled from its display name. A ping can show a
direct or relayed route; either route can work. Do not reconnect Tailscale,
alter DNS, enable sharing, or reset Serve/Funnel merely to complete a review.

T3 Connect has its own connection and does not require the Tailscale route.
Keep that working access while investigating SSH or private web services.
The host and its service must stay running for their respective links to work.

## Return useful links

- Give clickable, real URLs in the reply, with the service, owning Mac and
  required client app/VPN beside each one. The `<mini>.<tailnet>.ts.net`
  addresses in the public docs are examples, not usable links to hand over.
- Inspect Serve on the host that owns the service. The MacBook's Serve
  output does not list the mini's routes, or the reverse. Preserve the full
  origin (including a nondefault port) and path.
- For each link, say whether it was tested from the intended client, only
  configured on the host, or could not be checked. Host-local HTTP 200 alone
  does not verify the HTTPS route, DNS, access policy or an iPad connection.
- If the host is unavailable or Tailscale is stopped, state the concrete
  failure. A link from an earlier inspection must be marked as not rechecked;
  never fabricate an address or claim it works now.
- Pairing links authorize access and are one-time links for new devices.
  Generate one on the chosen host only when pairing is requested, and pass
  it directly to the intended client. Keep it out of public docs, commits
  and diagnostic logs. If the creating page was closed or reloaded, create
  a fresh link rather than reusing an unavailable one.
- Public docs keep placeholders for private network addresses. Machine-local
  bookmarks keep the real address. A bookmark on one device does not prove
  that it exists on another.

## Keep services private and existing routes intact

Inspect the exact listener before adding a route. Serve shares to the tailnet;
Funnel exposes a service to the internet. A `.ts.net` hostname alone does not
prove a route is private: inspect its port's Serve/Funnel state. Do not enable
Funnel for Stats, Netdata, CLIProxy or T3 pairing as part of this setup.

Keep existing project routes. Adding the same port/path can replace its
current target; choose an available endpoint instead of running a sample
command against an occupied route. Never use `tailscale serve reset`.

See the official [Serve reference](https://tailscale.com/docs/reference/tailscale-cli/serve),
[Funnel guide](https://tailscale.com/docs/features/tailscale-funnel) and
[T3 remote-access guide](https://github.com/pingdotgg/t3code/blob/main/docs/user/remote-access.md).
