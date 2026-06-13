# Troubleshooting

## Docker commands fail

Make sure Colima is installed and running:

```sh
brew install colima docker docker-compose
colima start
docker compose version
```

Serverfiles uses the Docker CLI through Colima. Docker Desktop and OrbStack are not required.

If `docker compose version` works but commands still fail, check that Colima is running and the Docker daemon is reachable:

```sh
colima status
docker info
```

## Command says Serverfiles is not initialized

Run:

```sh
serverfiles init
```

This creates `~/.serverfiles/config.yml` and `~/.serverfiles/docker-compose.yml`.

## Ports are already in use

Run:

```sh
serverfiles doctor
```

`doctor` checks the default core and `dev` ports. For an optional or customized
port, inspect it directly:

```sh
lsof -nP -iTCP:8082 -sTCP:LISTEN
```

Stop the process using the conflicting port, or edit `~/.serverfiles/config.yml`.
If the stack was already added, rerun its add command so Serverfiles regenerates
the known service ports:

```sh
serverfiles add dev
```

Use `serverfiles add files` or `serverfiles add photos` for those stacks.

## Autostart does not run

Check launchd logs:

```sh
cat ~/.serverfiles/logs/launchd.log
cat ~/.serverfiles/logs/launchd.err.log
```

You can recreate the launchd entry with:

```sh
serverfiles disable-autostart
serverfiles enable-autostart
```

The generated launchd job includes the common Homebrew paths for Apple Silicon and Intel Macs. If Docker was installed somewhere else, make sure `docker` is available to launchd.
