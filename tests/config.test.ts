import assert from "node:assert/strict";
import test from "node:test";
import { serverfilesConfigSchema } from "../src/utils/validators.js";

const baseConfig = {
  version: 1,
  serverName: "mac-mini",
  root: "/tmp/serverfiles-test/.serverfiles",
  stacks: [],
  ports: {
    caddyHttp: 80,
    caddyHttps: 443,
    postgres: 5432,
    redis: 6379,
    mongodb: 27017,
    adminer: 8080,
    uptimeKuma: 3001,
    filebrowser: 8082,
    immich: 2283
  }
};

test("accepts a valid serverfiles config", () => {
  assert.deepEqual(serverfilesConfigSchema.parse(baseConfig), baseConfig);
});

test("rejects duplicate configured ports", () => {
  const result = serverfilesConfigSchema.safeParse({
    ...baseConfig,
    ports: {
      ...baseConfig.ports,
      adminer: 5432
    }
  });

  assert.equal(result.success, false);
  assert.match(String(result.error.issues[0]?.message), /already used/);
});

test("rejects ports outside the TCP range", () => {
  const result = serverfilesConfigSchema.safeParse({
    ...baseConfig,
    ports: {
      ...baseConfig.ports,
      redis: 70000
    }
  });

  assert.equal(result.success, false);
});
