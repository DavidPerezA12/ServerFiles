import { Command } from "commander";
import { addDevStack } from "../stacks/dev.js";
import { addFilesStack } from "../stacks/files.js";
import { addPhotosStack } from "../stacks/photos.js";
import { logger } from "../utils/logger.js";

const stacks = {
  dev: addDevStack,
  files: addFilesStack,
  photos: addPhotosStack
} as const;

export const addCommand = new Command("add")
  .description("Add a stack to docker-compose.yml")
  .argument("<stack>", "Stack name")
  .action(async (stack: string) => {
    if (!(stack in stacks)) {
      logger.error(`Unknown stack: ${stack}`);
      logger.info(`Available stacks: ${Object.keys(stacks).join(", ")}`);
      process.exitCode = 1;
      return;
    }

    const result = await stacks[stack as keyof typeof stacks]();
    for (const service of result.addedServices) {
      logger.success(`Added service: ${service}`);
    }
    for (const service of result.existingServices) {
      logger.info(`Service already exists: ${service}`);
    }
  });
