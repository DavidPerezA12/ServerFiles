import { Command } from "commander";
import { composeUp } from "../core/docker.js";
import { paths } from "../core/paths.js";
import { ensureReadyForCompose } from "../core/preflight.js";
import { logger } from "../utils/logger.js";

export const startCommand = new Command("start")
  .description("Start the Serverfiles Docker Compose stack")
  .action(async () => {
    await ensureReadyForCompose();
    await composeUp(paths.compose);
    logger.success("Serverfiles stack started");
  });
