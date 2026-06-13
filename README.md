# Serverfiles

**Dotfiles for your home server.**

Serverfiles is an open-source, macOS-first configuration toolkit that turns your Mac mini into a reproducible home server for development, monitoring, backups and private services.

## Idea

Serverfiles treats a home server like dotfiles: versioned, repeatable, modular and easy to rebuild. The MVP focuses on macOS, Colima, Docker Compose and launchd, with no web dashboard yet.

## Requirements

- macOS on Apple Silicon or Intel
- Node.js 20+
- pnpm
- Homebrew
- Colima
- Docker CLI with Docker Compose

Recommended setup:

```sh
brew install colima docker docker-compose
colima start
```

## Installation

```sh
pnpm install
pnpm build
pnpm link --global
```

You can also run locally without linking:

```sh
pnpm dev -- doctor
```

## Development

```sh
pnpm build
pnpm test
```

CI runs build and tests on macOS, matching the project runtime assumptions.

## Commands

```sh
serverfiles doctor
serverfiles init
serverfiles github-runner owner/repo
serverfiles github-runner my-org --scope org
serverfiles add dev
serverfiles add files
serverfiles add photos
serverfiles start
serverfiles stop
serverfiles restart
serverfiles status
serverfiles logs
serverfiles logs --follow
serverfiles logs --tail 200
serverfiles enable-autostart
serverfiles disable-autostart
```

## Quick Example

```sh
serverfiles doctor
serverfiles init
serverfiles add dev
serverfiles start
serverfiles status
```

This creates `~/.serverfiles`, adds the development stack and starts the services with Docker Compose.

To prepare the Mac mini as a GitHub Actions self-hosted runner for a repository:

```sh
serverfiles github-runner owner/repo
```

The command creates setup notes under `~/.serverfiles/github-runners` and tells
you which GitHub settings page to open. GitHub's generated token is intentionally
not stored in this repository.

## Configuration

Serverfiles stores runtime state in `~/.serverfiles`:

- `config.yml`: server name, enabled stacks and port choices
- `docker-compose.yml`: generated Compose file for the enabled stacks
- `github-runners/`: local setup notes for GitHub Actions self-hosted runners
- `data/`: persistent service data
- `logs/`: service and launchd logs
- `launchd/`: generated launchd files
- `backups/`: reserved for backup profiles

Edit `~/.serverfiles/config.yml` before running `serverfiles add dev` if you need different host ports. Serverfiles validates ports and prevents duplicate assignments.

After changing ports for an enabled stack, run its `serverfiles add <stack>` command
again to regenerate the known service ports in `docker-compose.yml`.

## Available Stacks

- `dev`: PostgreSQL, Redis, MongoDB, Adminer and Uptime Kuma.
- `files`: File Browser for a simple private web file manager.
- `photos`: Immich for self-hosted photo and video backup.

Stack service ports are bound to `127.0.0.1` by default. The base compose file also includes Caddy as the public reverse proxy foundation.

Serverfiles is MIT-licensed orchestration code. Optional stacks use upstream Docker images and keep their own licenses; Serverfiles does not vendor those applications.

## Documentation

- [Getting started](docs/getting-started.md)
- [Stacks and ports](docs/stacks.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Architecture](docs/architecture.md)
- [GitHub Actions on a Mac mini](docs/ci-mac-mini-runner.md)
- [Contributing](CONTRIBUTING.md)

## Roadmap

- Caddy site templates
- restic backup profiles
- config-driven credentials
- health checks
- import/export for server profiles
- optional web dashboard

## License

MIT
