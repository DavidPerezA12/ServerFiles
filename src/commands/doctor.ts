import fs from "fs-extra";
import { Command } from "commander";
import { hasDockerCompose } from "../core/docker.js";
import { isColimaRunning } from "../core/colima.js";
import { readConfig, readDefaultPorts } from "../core/config.js";
import { paths } from "../core/paths.js";
import { ServerfilesError } from "../core/preflight.js";
import {
  architecture,
  baseToolChecks,
  diskSpace,
  isMacOS,
  isPortFree,
  serverfilesRootExists
} from "../core/system.js";
import { logger } from "../utils/logger.js";

async function portAssignments() {
  if (!(await fs.pathExists(paths.config))) {
    return { source: "defaults", ports: await readDefaultPorts(), configError: undefined };
  }

  try {
    const config = await readConfig();
    return { source: "config.yml", ports: config.ports as Record<string, number>, configError: undefined };
  } catch (error) {
    return {
      source: "defaults",
      ports: await readDefaultPorts(),
      configError: error instanceof ServerfilesError ? error.message : String(error)
    };
  }
}

export const doctorCommand = new Command("doctor")
  .description("Check macOS, dependencies, Colima, ports, disk space and ~/.serverfiles")
  .action(async () => {
    logger.line("Serverfiles doctor");
    logger.line();

    const macos = isMacOS();
    const arch = architecture();
    const tools = await baseToolChecks();
    const dockerCompose = await hasDockerCompose();
    const colimaRunning = await isColimaRunning();
    const space = await diskSpace();
    const rootExists = await serverfilesRootExists();
    const configExists = await fs.pathExists(paths.config);
    const { source, ports, configError } = await portAssignments();

    logger.check("macOS", macos, process.platform);
    logger.check("architecture", ["arm64", "x64"].includes(arch), arch);
    logger.check("Homebrew installed", tools.homebrew);
    logger.check("Colima installed", tools.colima);
    logger.check("Docker CLI installed", tools.docker);
    logger.check("Docker Compose available", dockerCompose);
    logger.check("Colima running", colimaRunning);
    logger.check("disk space", space.availableGb >= 5, `${space.availableGb} GB available`);
    logger.check("~/.serverfiles exists", rootExists);
    if (configExists) {
      logger.check("config.yml valid", !configError, configError);
    }

    logger.line();
    logger.line(`Ports (from ${source})`);
    for (const [name, port] of Object.entries(ports)) {
      logger.check(`port ${port} free`, await isPortFree(port), name);
    }
  });
