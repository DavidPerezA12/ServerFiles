import { capture, commandExists, run } from "./shell.js";

export async function hasDockerCompose() {
  if (!(await commandExists("docker"))) {
    return false;
  }

  try {
    await capture("docker", ["compose", "version"]);
    return true;
  } catch {
    return false;
  }
}

export async function canReachDockerDaemon() {
  try {
    await capture("docker", ["info"]);
    return true;
  } catch {
    return false;
  }
}

export async function composeUp(composeFile: string) {
  await run("docker", ["compose", "-f", composeFile, "up", "-d"]);
}

export async function composeDown(composeFile: string) {
  await run("docker", ["compose", "-f", composeFile, "down"]);
}

export async function composeRestart(composeFile: string) {
  await composeDown(composeFile);
  await composeUp(composeFile);
}

export async function composeLogs(composeFile: string, follow: boolean, tail: string) {
  await run("docker", [
    "compose",
    "-f",
    composeFile,
    "logs",
    "--tail",
    tail,
    ...(follow ? ["-f"] : [])
  ]);
}

export async function composePs(composeFile: string) {
  try {
    const result = await capture("docker", ["compose", "-f", composeFile, "ps"]);
    return result.stdout;
  } catch (error) {
    return error instanceof Error ? error.message : String(error);
  }
}
