# Stacks

## dev

The `dev` stack includes:

- PostgreSQL
- Redis
- MongoDB
- Adminer
- Uptime Kuma

Add it with:

```sh
serverfiles add dev
```

Default ports:

| Service | Port |
| --- | ---: |
| PostgreSQL | 5432 |
| Redis | 6379 |
| MongoDB | 27017 |
| Adminer | 8080 |
| Uptime Kuma | 3001 |

The generated Compose file binds these development services to `127.0.0.1` by default. Caddy remains the public entry point on ports 80 and 443.

Change ports in `~/.serverfiles/config.yml` before adding the stack. The generated Compose file uses those configured ports.

If the stack is already enabled, edit `config.yml` and run `serverfiles add dev`
again to reapply its configured ports.

## files

The `files` stack adds [File Browser](https://filebrowser.org/) as a lightweight private file manager.

Add it with:

```sh
serverfiles add files
```

Default port:

| Service | Port |
| --- | ---: |
| File Browser | 8082 |

Persistent data is stored under `~/.serverfiles/data/files`, with File Browser configuration and database files under `~/.serverfiles/data/filebrowser`.

Change `ports.filebrowser` in `~/.serverfiles/config.yml` and rerun
`serverfiles add files` to use a different host port.

File Browser is distributed by its upstream project under Apache-2.0. Serverfiles only provides the Compose integration and does not vendor File Browser source code.

## photos

The `photos` stack adds [Immich](https://immich.app/) for self-hosted photo and video backup.

Add it with:

```sh
serverfiles add photos
```

Default port:

| Service | Port |
| --- | ---: |
| Immich | 2283 |

Persistent media and database data are stored under `~/.serverfiles/data/immich`.

Change `ports.immich` in `~/.serverfiles/config.yml` and rerun
`serverfiles add photos` to use a different host port.

Immich is distributed by its upstream project under AGPL-3.0. Serverfiles only provides the Compose integration and does not vendor Immich source code. The Compose template follows Immich's Docker Compose installation model, with service names adjusted so it can coexist with other Serverfiles stacks.

You can override the Immich image version and database credentials through environment variables before running Docker Compose:

```sh
IMMICH_VERSION=v2 SERVERFILES_IMMICH_DB_PASSWORD=change_me serverfiles start
```
