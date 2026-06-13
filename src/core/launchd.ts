import fs from "fs-extra";
import os from "node:os";
import path from "node:path";
import { paths, templatePath } from "./paths.js";
import { capture, run } from "./shell.js";

export const launchdLabel = "dev.serverfiles.stack";
export const launchdFileName = `${launchdLabel}.plist`;

export function launchdSourcePath() {
  return path.join(paths.launchd, launchdFileName);
}

export function launchdTargetPath() {
  return path.join(paths.launchAgents, launchdFileName);
}

export async function renderLaunchdPlist() {
  const template = await fs.readFile(templatePath("launchd.plist"), "utf8");
  return template
    .replaceAll("{{LABEL}}", launchdLabel)
    .replaceAll("{{HOME}}", os.homedir())
    .replaceAll("{{COMPOSE_FILE}}", paths.compose)
    .replaceAll("{{LOG_FILE}}", path.join(paths.logs, "launchd.log"))
    .replaceAll("{{ERROR_LOG_FILE}}", path.join(paths.logs, "launchd.err.log"));
}

export async function enableAutostart() {
  await fs.ensureDir(paths.launchd);
  await fs.ensureDir(paths.launchAgents);

  const plist = await renderLaunchdPlist();
  await fs.writeFile(launchdSourcePath(), plist, "utf8");
  await fs.copy(launchdSourcePath(), launchdTargetPath());

  try {
    await capture("launchctl", ["bootout", `gui/${process.getuid?.()}`, launchdTargetPath()]);
  } catch {
    // It is fine when the service was not loaded before.
  }

  await run("launchctl", ["bootstrap", `gui/${process.getuid?.()}`, launchdTargetPath()]);
  await run("launchctl", ["enable", `gui/${process.getuid?.()}/${launchdLabel}`]);
}

export async function disableAutostart() {
  try {
    await capture("launchctl", ["bootout", `gui/${process.getuid?.()}`, launchdTargetPath()]);
  } catch {
    // It is fine when the service is already unloaded.
  }

  await fs.remove(launchdTargetPath());
}
