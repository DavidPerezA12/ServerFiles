# Architecture

Serverfiles is a TypeScript CLI built with Commander.js.

- `src/commands`: CLI command handlers
- `src/core`: reusable system, Docker, config, compose and launchd logic
- `src/stacks`: stack definitions
- `templates`: initial config, compose fragments and launchd plist
- `tests`: Node test runner coverage for core modules
- `docs`: project documentation

The MVP uses Colima as the primary open-source container runtime on macOS.

Commands stay intentionally thin:

- `src/commands` parses CLI options and prints user-facing output
- `src/core/preflight.ts` centralizes environment checks
- `src/core/config.ts` validates `config.yml` with zod
- `src/core/compose.ts` reads and writes Compose YAML structurally
- `src/stacks` owns stack-specific merge behavior

Templates are copied or merged into `~/.serverfiles`; user paths are derived from `os.homedir()` in `src/core/paths.ts`.

`config.yml` is the source of truth for configured host ports. Running
`serverfiles add <stack>` merges that stack's template into `docker-compose.yml`
and reapplies configured ports to known services.

GitHub Actions builds and tests the project on macOS, matching the primary runtime.
