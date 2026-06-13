import { Command } from "commander";
import { hasDockerCompose } from "../core/docker.js";
import { isColimaRunning } from "../core/colima.js";
import {
  architecture,
  baseToolChecks,
  diskSpace,
  isMacOS,
  isPortFree,
  serverfilesRootExists
} from "../core/system.js";
import { logger } from "../utils/logger.js";

const basicPorts = [80, 443, 5432, 6379, 27017, 8080, 3001];

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

    logger.check("macOS", macos, process.platform);
    logger.check("architecture", ["arm64", "x64"].includes(arch), arch);
    logger.check("Homebrew installed", tools.homebrew);
    logger.check("Colima installed", tools.colima);
    logger.check("Docker CLI installed", tools.docker);
    logger.check("Docker Compose available", dockerCompose);
    logger.check("Colima running", colimaRunning);
    logger.check("disk space", space.availableGb >= 5, `${space.availableGb} GB available`);
    logger.check("~/.serverfiles exists", rootExists);

    logger.line();
    logger.line("Ports");
    for (const port of basicPorts) {
      logger.check(`port ${port} free`, await isPortFree(port));
    }
  });
