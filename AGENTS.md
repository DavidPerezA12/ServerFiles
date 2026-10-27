# Agent setup instructions

Serverfiles describes how to prepare a Mac for remote development. The
reference machine is a Mac mini. Work in small blocks and communicate with
the user in Spanish unless they request another language.

## Start with inspection

1. Read this file, the README, `Brewfile` and everything in `docs/`.
2. Inspect the target Mac: macOS version, architecture, hardware model,
   installed tools and apps, running services, power settings and existing
   remote access. Use `sw_vers`, `uname -m`, `sysctl -n hw.model` and relevant
   read-only checks. Establish which Mac is being configured before changing
   it. Inspect SSH, T3 Code, Tailscale and Jump Desktop independently.
3. Summarize what already works and what is missing. Existing installations
   and user choices count; avoid reinstalling or asking for them again.
4. For connections and handing over real links, follow
   [docs/CONNECTIONS.md](docs/CONNECTIONS.md). Inspect each owning host and
   distinguish configured routes from client-tested access. Tailscale
   `status` exiting successfully is not proof that BackendState is Running.

## Reuse dotfiles

Use https://github.com/DavidPerezA12/dotfiles as the default source (or the
user's own dotfiles/fork if they have one) for shared tools,
apps, shell, Git and Neovim configuration. Keep those definitions there
instead of maintaining a second copy in Serverfiles.

- If dotfiles is already available, inspect its branch, status and local
  changes. Preserve them; do not reset, overwrite or update the checkout
  automatically.
- Otherwise, clone it into an available location such as
  `$HOME/Developer/dotfiles`. Use the checkout's actual path throughout.
- Read its `AGENTS.md`, README, Brewfiles and installer before using them.
  If its instructions refer Mac mini setup back to Serverfiles, continue
  coordinating the server setup here; the shared files remain references.
- Explain what an installer actually does before running it. Flags that skip
  Homebrew or apps may still install other tools or replace configuration.
  Do not treat the entire installer or Brewfile as automatically selected.
- Apply the user's selection from the shared definitions. Preserve existing
  configuration with backups before replacing files or changing symlinks.
  Keep machine-local Git identity, credentials and private SSH keys local.

## Choose and apply one block at a time

Present concrete choices based on the inspected files and host. Ask what to
install or omit where the user has not already chosen. Explain large
downloads, paid software, sign-ins and permissions before that block starts.
Carry accepted choices forward without asking for them again.
Use dotfiles' `docs/INSTALL_CHOICES.md` for the same short Spanish conversation
flow on both Macs: identify the host, ask its intended use, offer one block
with actual missing tools and install/omit alternatives, then verify it.
Avoid one question per dependency or a giant checklist of every package.

The available blocks are:

- Shared terminal, Git and editor setup from dotfiles.
- Runtimes, coding agents, linters and SDKs.
- Apps selected from dotfiles' current app list, plus this repo's `Brewfile`:
  what only the mini needs (Jump Desktop Connect, monitoring).
- Remote access: T3 Code and T3 Connect, Tailscale, macOS Remote Login,
  Jump Desktop Connect and VS Code Remote Tunnels.
- Monitoring (`docs/MONITORING.md`).
- Settings, login items and what starts on its own, so the mini recovers
  from a restart or a power cut (`docs/MINI.md`).
- Client setup: a Mac follows dotfiles' `docs/MAC_MINI.md`, the iPad
  `docs/IPAD.md`.

Before the development-tools block, follow [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).
Ask which workloads this host should support: Android, iOS/macOS, web/backend,
local databases/containers, and coding agents. Show what already exists and
ask only about undecided choices. Android SDKs, emulator images, full Xcode,
Docker and local database services are separate selections, not automatic
consequences of choosing a development server. An unselected workload is an
intentional omission, not a failed installation or a synchronization defect.
Record the accepted selection and verify against it. Do not run dotfiles'
whole installer or Brewfiles unless all their effects have been selected.

Report each block's result and next step. Keep progress messages short.
When a step needs a sign-in or permission, explain the exact action to take
in the app or system settings and wait for the user to complete it. Never
ask for a password, private key or token in chat.

## Make hardware-dependent choices

Determine whether the target is a laptop from its hardware, for example a
`MacBook` model, rather than from the repository being used. Confirm the
hardware if detection is unclear.

- Offer AlDente only on a laptop. Exclude it on desktop Macs such as a Mac
  mini. This rule also applies when Serverfiles is used on a MacBook.
- Wispr Flow belongs on the MacBook client, not the Mac mini server. Exclude
  it from the mini's app selection; its absence is expected. Do not prompt
  to install it as part of making the Macs match.
- Tailor power settings to the actual machine and its role. Do not apply a
  desktop always-on power policy to battery operation automatically.
- Check architecture and tool requirements before selecting packages.

## Adapt the repo to this Mac during installation

The files here are templates, not a finished install. The agent adapts them
to the machine it is configuring; the user should not have to edit anything.

- Detect the account (`id -un`), hostname, home, Homebrew prefix and
  architecture. Do not assume `david`, `macmini` or `/opt/homebrew`.
- Fill placeholders such as `__USER__` and `__PANEL_DIR__` in a copy
  (installed config, LaunchAgent) and leave the repo's templates unchanged.
- Treat `docs/` values (account, aliases, tunnel name, ports, login items) as
  examples. Check what the Mac already has and keep it; ask only for choices
  the host can't answer.
- Before installing a LaunchAgent, check for an older one that does the same
  job (for example `local.david.netdata-dashboard`) and ask whether to
  replace it, so the panel doesn't run twice.
- Do not copy another person's services, Funnel/Serve routes or healthchecks.
  List the Mac's own with `launchctl list` and `tailscale serve status`.
- After each block, run the matching checks in
  [`scripts/verify.sh`](scripts/verify.sh). Its default is the server role;
  use `--role client` on a client Mac to skip server-only checks. A review
  does not authorize reconnecting Tailscale or changing routes.

## Verify the result

Installation is not proof that access works. Check versions, configuration
paths and the relevant service or connection after each block. Check an SSH
terminal's hostname and user, T3's selected environment, and desktop control
through Jump Desktop. Report client checks as pending until tested there.

Preserve existing Tailscale Serve/Funnel mappings when adding a route. Login
items and user LaunchAgents may require graphical login; test availability
after restart separately instead of promising unattended recovery.

Finish with what works, what failed and what remains manual or unverified.
Do not change project source code, install unrelated services, commit or
publish unless requested. Do not add AI attribution to commits.

## Public repository privacy

Before publication, inspect all included files, including untracked files,
binary preferences and images with their metadata. Keep tokens, keys,
personal email addresses, private network URLs/IPs, pairing links, logs,
account exports and machine-local settings outside this repo. Use placeholders
in public instructions and real addresses only in the private setup/session.
Do not copy private audit output into documentation. Documentation screenshots
must use clearly labelled synthetic data, without real hostnames, activity,
storage figures, project names or account information. Preserve any originals
only in a private backup outside the repository.
Check authors, committers and trailers separately from file contents. Old
commits can retain private emails or machine hostnames. Report findings
without printing the private values, and do not rewrite or force-push
history without explicit authorization.
