# Getting Started

Serverfiles is a macOS-first CLI for turning a Mac mini into a reproducible home server.

## Requirements

- macOS
- Node.js 20 or newer
- pnpm
- Homebrew
- Colima
- Docker CLI with Docker Compose

Install the runtime tools and start Colima:

```sh
brew install colima docker docker-compose
colima start
```

## Local development

```sh
pnpm install
pnpm build
pnpm test
pnpm link --global
serverfiles doctor
```

You can run the CLI without linking:

```sh
pnpm dev -- doctor
```

## First server setup

```sh
serverfiles doctor
serverfiles init
serverfiles add dev
serverfiles start
serverfiles status
```

The runtime directory is `~/.serverfiles`.

To prepare a GitHub Actions self-hosted runner directory for a repository:

```sh
serverfiles github-runner owner/repo
```

This writes setup notes under `~/.serverfiles/github-runners` without storing
GitHub tokens or runner credentials.

For development and testing, use a temporary home directory so your real server state is left alone:

```sh
TEST_HOME="$(mktemp -d)"
HOME="$TEST_HOME" node dist/cli.js init
HOME="$TEST_HOME" node dist/cli.js add dev
```

See [Stacks](stacks.md) for the optional `files` and `photos` stacks.
