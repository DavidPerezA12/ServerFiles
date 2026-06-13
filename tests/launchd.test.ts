import assert from "node:assert/strict";
import test from "node:test";
import { renderLaunchdPlist } from "../src/core/launchd.js";

test("launchd plist includes Homebrew paths before running docker compose", async () => {
  const plist = await renderLaunchdPlist();

  assert.match(plist, /\/opt\/homebrew\/bin/);
  assert.match(plist, /\/usr\/local\/bin/);
  assert.match(plist, /docker compose -f/);
});
