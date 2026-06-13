# Contributing

Thanks for helping build Serverfiles.

Serverfiles is intentionally a small, boring TypeScript CLI for macOS home servers. Keep changes practical, modular and friendly to people running a Mac mini as a 24/7 server.

## Development

```sh
pnpm install
pnpm build
pnpm test
pnpm dev -- doctor
```

Use a temporary `HOME` when testing commands that write runtime files:

```sh
TEST_HOME="$(mktemp -d)"
HOME="$TEST_HOME" node dist/cli.js init
HOME="$TEST_HOME" node dist/cli.js add dev
```

## Guidelines

- Keep commands thin; put reusable behavior in `src/core`.
- Keep stack-specific logic in `src/stacks`.
- Use structured YAML parsing and writing instead of string edits.
- Do not hardcode user paths; use `src/core/paths.ts`.
- Do not require Docker Desktop, OrbStack or proprietary tooling.
- Treat Colima plus Docker CLI/Compose as the default runtime.
- Do not add a web dashboard until it is explicitly roadmap work.
- Add focused tests for reusable core behavior.
- Update the README or `docs/` when user-facing behavior changes.
- Follow the shared repository guidance in `AGENTS.md`.

## Verification

Before opening a pull request, run:

```sh
pnpm build
pnpm test
```
