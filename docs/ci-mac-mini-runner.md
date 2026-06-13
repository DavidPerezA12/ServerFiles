# GitHub Actions on a Mac mini

This project can run CI on a personal Mac mini using a GitHub Actions
self-hosted runner. The normal development flow stays the same:

```text
MacBook -> git push -> GitHub detects workflow -> GitHub sends the job to the self-hosted runner -> Mac mini runs CI
```

The MacBook only pushes code. The Mac mini is the machine that checks out the
repository, installs dependencies, builds and runs tests.

## Register the runner

Register the runner from GitHub, then run the generated commands on the Mac mini.

Serverfiles can prepare a local setup directory and repo-specific instructions:

```sh
serverfiles github-runner OWNER/REPO
```

For an organization-level runner:

```sh
serverfiles github-runner ORG --scope org
```

The command writes instructions under `~/.serverfiles/github-runners`. It creates
local setup notes only; it does not store GitHub tokens or runner credentials.

1. Open the repository on GitHub.
2. Go to Settings.
3. Go to Actions -> Runners.
4. Choose New self-hosted runner.
5. Choose macOS.
6. Choose ARM64 for an Apple Silicon Mac mini.
7. On the Mac mini, create a runner directory and run the download commands that
   GitHub shows.
8. Run the generated `./config.sh` command from GitHub.
9. Add the custom label `mac-mini`.

GitHub gives each runner default labels such as `self-hosted`, `macOS` and
`ARM64`. The extra `mac-mini` label makes the workflow target this machine
explicitly.

You can add the custom label either during setup:

```sh
./config.sh --url https://github.com/OWNER/REPO --token TOKEN --labels mac-mini
```

Or after setup from GitHub:

1. Go to Settings -> Actions -> Runners.
2. Open the runner.
3. In Labels, add or create `mac-mini`.

The token in GitHub's generated command is short lived. Use the exact current
command from the GitHub UI when registering the runner.

## Install the runner as a service

After `./config.sh` succeeds, install the runner service from the runner
directory on the Mac mini:

```sh
./svc.sh install
./svc.sh start
./svc.sh status
```

This keeps the runner listening for jobs after the terminal closes and starts it
again when the Mac mini starts. To manage it later:

```sh
./svc.sh stop
./svc.sh start
./svc.sh status
```

If you installed the runner under another user account, run these commands while
logged in as that user. Keep the runner directory in a stable location such as
`~/actions-runner/serverfiles`.

## Workflow

The CI workflow for this repository uses the Mac mini runner:

```yaml
name: CI Mac mini

on:
  push:
    branches:
      - main
  pull_request:

jobs:
  build:
    runs-on: [self-hosted, macOS, ARM64, mac-mini]

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: 22

      - name: Enable pnpm
        run: corepack enable

      - name: Install dependencies
        run: pnpm install --frozen-lockfile

      - name: Typecheck and build
        run: pnpm build

      - name: Test
        run: pnpm test
```

## What should run where

For Serverfiles, the main build and test job should run on the Mac mini because
the project is macOS-first and uses macOS-specific assumptions such as launchd.

Jobs that only lint Markdown, check formatting, validate YAML or run generic
static analysis could stay on GitHub-hosted runners if desired. The current
workflow is small, so keeping the whole job on the Mac mini is reasonable.

For personal repositories that are not in a GitHub organization, register the
Mac mini per repository. If you want one runner registration shared by several
repositories, put those repositories in a GitHub organization and register an
organization-level runner with repository access limited to the repos you trust.

## Other repository types

Node, Next.js or Vercel projects can use the same runner labels and swap in the
project's normal package-manager commands:

```yaml
jobs:
  test:
    runs-on: [self-hosted, macOS, ARM64, mac-mini]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: pnpm
      - run: corepack enable
      - run: pnpm install --frozen-lockfile
      - run: pnpm lint
      - run: pnpm test
      - run: pnpm build
```

Android projects can target the same Mac mini and run Gradle:

```yaml
jobs:
  android:
    runs-on: [self-hosted, macOS, ARM64, mac-mini]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: 17
      - run: ./gradlew test assembleDebug
```

iOS, macOS, Swift or Xcode projects are a natural fit for the Mac mini:

```yaml
jobs:
  xcode:
    runs-on: [self-hosted, macOS, ARM64, mac-mini]
    steps:
      - uses: actions/checkout@v4
      - run: xcodebuild test -scheme YourScheme -destination 'platform=macOS'
```

## Important warnings

- The Mac mini must be powered on and connected to the internet.
- The runner service must be active.
- If a workflow uses `ubuntu-latest`, `macos-latest` or `windows-latest`, it runs
  on GitHub-hosted infrastructure, not on this Mac mini.
- To use this Mac mini, jobs must use `self-hosted` and the correct labels.
- Avoid self-hosted runners for public repositories that accept pull requests
  from unknown contributors. Those workflows can execute untrusted code on your
  machine.
- For private and personal repositories, this setup makes sense if you trust the
  code that can reach the runner.
