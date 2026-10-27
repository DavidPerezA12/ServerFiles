# Selecting development tools

Before configuring the server, ask what work it should run. A Mac mini does
not need every package or app from the MacBook. Shared package definitions
remain in dotfiles; Serverfiles coordinates which ones to apply on this host.

## Ask after inspecting

Use the same conversation flow as dotfiles' `docs/INSTALL_CHOICES.md`;
the workload choices below specialize it for the server.

Inspect the installed tools, active services and the requirements of the
projects the user wants to run. Then present a short selection in Spanish,
for example:

> ¿Qué quieres desarrollar en este servidor: Android, iOS/macOS, web/backend
> u otras cosas? Esto es lo que ya tienes instalado. Para lo que falta,
> elige si necesitas solo compilar o también ejecutar emuladores, bases de
> datos y contenedores en el mini.

Carry choices already made in the conversation forward. Do not ask the user
to repeat them. For each selected workload, explain the concrete missing
packages, download/storage cost for large components, and any manual steps.

| Workload | Confirm before installation | Verify after the selected setup |
|---|---|---|
| Android | JDK and SDK versions required by the projects; command-line tools, platform-tools and build packages; emulator and system images only if wanted; Android Studio separately | Resolve `JAVA_HOME` and `ANDROID_HOME`, check Java, sdkmanager and adb versions, and build the selected project; boot an emulator only if selected |
| iOS/macOS | Command Line Tools versus full Xcode; project-compatible Xcode version; simulator runtimes and devices only if needed | Check `xcode-select -p`, the selected toolchain and a project build; run on a simulator only if selected |
| Web/backend | Project runtimes and version managers, such as Node/NVM, Bun or Python/uv; package managers and linters required by the projects | Check command paths and versions, then the project's relevant build or checks |
| Databases and containers | Whether PostgreSQL, Docker or another service should run locally, or the projects should use an existing remote service | Check the selected client/service and an actual connection; preserve existing data and ports |
| Coding agents | Which CLIs are wanted and which accounts the user will use | Check executable paths and versions; keep sign-ins and credentials local and manual |

Installing an SDK is not proof that a project builds. Conversely, an app
missing from Homebrew's inventory may already be installed manually; inspect
its executable or app before proposing a duplicate installation.

## Record the selection

Keep a machine-local checklist with the chosen workloads, package/SDK versions,
items already working, intentional omissions and pending manual steps. Do not
put credentials or private project/network details into the public repository.
The selected checklist is the verification baseline: do not label an omitted
workload as missing merely because it appears in dotfiles' Brewfiles.

Do not run the complete shared installer or `brew bundle` against the whole
shared inventory unless the user has selected everything it would do.
Installer skip flags can still install other tools or change configuration;
inspect them before using them for a partial setup.

## Client-only apps

Wispr Flow is for the MacBook client and must not be installed on the Mac
mini server. Its absence on the mini is correct. AlDente is also excluded
on the mini because it is a desktop Mac. These are not tools needed to
compile projects or host remote development.
