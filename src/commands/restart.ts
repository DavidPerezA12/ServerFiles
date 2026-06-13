import { Command } from "commander";
import { composeRestart } from "../core/docker.js";
import { paths } from "../core/paths.js";
import { ensureReadyForCompose } from "../core/preflight.js";
import { logger } from "../utils/logger.js";

export const restartCommand = new Command("restart")
  .description("Restart the Serverfiles Docker Compose stack")
  .action(async () => {
    await ensureReadyForCompose();
    await composeRestart(paths.compose);
    logger.success("Serverfiles stack restarted");
  });
