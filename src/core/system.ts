import fs from "fs-extra";
import net from "node:net";
import os from "node:os";
import { paths } from "./paths.js";
import { capture, commandExists } from "./shell.js";

export function isMacOS() {
  return process.platform === "darwin";
}

export function architecture() {
  return os.arch();
}

export async function diskSpace() {
  try {
    const result = await capture("df", ["-k", paths.home]);
    const [, line] = result.stdout.trim().split("\n");
    const parts = line.trim().split(/\s+/);
    const availableKb = Number(parts[3] ?? 0);
    return {
      availableGb: Math.round((availableKb / 1024 / 1024) * 10) / 10
    };
  } catch {
    return { availableGb: 0 };
  }
}

export async function isPortFree(port: number) {
  return new Promise<boolean>((resolve) => {
    const server = net.createServer();
    server.once("error", () => resolve(false));
    server.once("listening", () => {
      server.close(() => resolve(true));
    });
    server.listen(port, "127.0.0.1");
  });
}

export async function serverfilesRootExists() {
  return fs.pathExists(paths.root);
}

export async function baseToolChecks() {
  const [homebrew, colima, docker] = await Promise.all([
    commandExists("brew"),
    commandExists("colima"),
    commandExists("docker")
  ]);

  return { homebrew, colima, docker };
}
