import assert from "node:assert/strict";
import test from "node:test";
import { applyConfigToCompose } from "../src/core/compose.js";
import type { ServerfilesConfig } from "../src/utils/validators.js";

const config: ServerfilesConfig = {
  version: 1,
  serverName: "mac-mini",
  root: "/tmp/serverfiles-test/.serverfiles",
  stacks: ["dev"],
  ports: {
    caddyHttp: 8081,
    caddyHttps: 8443,
    postgres: 15432,
    redis: 16379,
    mongodb: 27018,
    adminer: 18080,
    uptimeKuma: 13001,
    filebrowser: 18082,
    immich: 12283
  }
};

test("applies configured host ports to known compose services", () => {
  const compose = applyConfigToCompose(
    {
      services: {
        caddy: {},
        postgres: {},
        redis: {},
        mongodb: {},
        adminer: {},
        "uptime-kuma": {},
        filebrowser: {},
        "immich-server": {},
        custom: { ports: ["9000:9000"] }
      }
    },
    config
  );

  assert.deepEqual(compose.services?.caddy.ports, ["8081:80", "8443:443"]);
  assert.deepEqual(compose.services?.postgres.ports, ["127.0.0.1:15432:5432"]);
  assert.deepEqual(compose.services?.redis.ports, ["127.0.0.1:16379:6379"]);
  assert.deepEqual(compose.services?.mongodb.ports, ["127.0.0.1:27018:27017"]);
  assert.deepEqual(compose.services?.adminer.ports, ["127.0.0.1:18080:8080"]);
  assert.deepEqual(compose.services?.["uptime-kuma"].ports, ["127.0.0.1:13001:3001"]);
  assert.deepEqual(compose.services?.filebrowser.ports, ["127.0.0.1:18082:80"]);
  assert.deepEqual(compose.services?.["immich-server"].ports, ["127.0.0.1:12283:2283"]);
  assert.deepEqual(compose.services?.custom.ports, ["9000:9000"]);
});
