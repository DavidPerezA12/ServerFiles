import { Command } from "commander";
import { composeDown } from "../core/docker.js";
import { paths } from "../core/paths.js";
import { ensureReadyForCompose } from "../core/preflight.js";
import { logger } from "../utils/logger.js";

export const stopCommand = new Command("stop")
  .description("Stop the Serverfiles Docker Compose stack")
  .action(async () => {
    await ensureReadyForCompose();
    await composeDown(paths.compose);
    logger.success("Serverfiles stack stopped");
  });
