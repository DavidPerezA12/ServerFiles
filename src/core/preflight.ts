import fs from "fs-extra";
import { isColimaRunning } from "./colima.js";
import { canReachDockerDaemon, hasDockerCompose } from "./docker.js";
import { paths } from "./paths.js";
import { isMacOS } from "./system.js";

export class ServerfilesError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ServerfilesError";
  }
}

export async function ensureInitialized() {
  const missing = [];

  if (!(await fs.pathExists(paths.root))) {
    missing.push(paths.root);
  }
  if (!(await fs.pathExists(paths.config))) {
    missing.push(paths.config);
  }
  if (!(await fs.pathExists(paths.compose))) {
    missing.push(paths.compose);
  }

  if (missing.length > 0) {
    throw new ServerfilesError(
      `Serverfiles is not initialized. Run \`serverfiles init\` first. Missing: ${missing.join(", ")}`
    );
  }
}

export async function ensureDockerCompose() {
  if (!(await hasDockerCompose())) {
    throw new ServerfilesError(
      "Docker Compose is not available. Install Docker CLI/Compose and start Colima, then retry."
    );
  }
}

export async function ensureColimaRunning() {
  if (!(await isColimaRunning())) {
    throw new ServerfilesError("Colima is not running. Start it with `colima start`, then retry.");
  }
}

export async function ensureDockerDaemon() {
  if (!(await canReachDockerDaemon())) {
    throw new ServerfilesError(
      "Docker is installed, but the Docker daemon is not reachable. Start Colima with `colima start`, then retry."
    );
  }
}

export async function ensureReadyForCompose() {
  await ensureInitialized();
  await ensureDockerCompose();
  await ensureColimaRunning();
  await ensureDockerDaemon();
}

export function ensureMacOS() {
  if (!isMacOS()) {
    throw new ServerfilesError("This command is only supported on macOS.");
  }
}
