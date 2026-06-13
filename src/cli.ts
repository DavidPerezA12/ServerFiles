#!/usr/bin/env node
import { Command } from "commander";
import { addCommand } from "./commands/add.js";
import { autostartCommand } from "./commands/autostart.js";
import { doctorCommand } from "./commands/doctor.js";
import { githubRunnerCommand } from "./commands/githubRunner.js";
import { initCommand } from "./commands/init.js";
import { logsCommand } from "./commands/logs.js";
import { restartCommand } from "./commands/restart.js";
import { startCommand } from "./commands/start.js";
import { statusCommand } from "./commands/status.js";
import { stopCommand } from "./commands/stop.js";
import { ServerfilesError } from "./core/preflight.js";
import { logger } from "./utils/logger.js";

const program = new Command();

program
  .name("serverfiles")
  .description("Dotfiles for your home server.")
  .version("0.1.0");

program.addCommand(doctorCommand);
program.addCommand(initCommand);
program.addCommand(githubRunnerCommand);
program.addCommand(addCommand);
program.addCommand(startCommand);
program.addCommand(stopCommand);
program.addCommand(restartCommand);
program.addCommand(statusCommand);
program.addCommand(logsCommand);
program.addCommand(autostartCommand("enable-autostart"));
program.addCommand(autostartCommand("disable-autostart"));

try {
  await program.parseAsync(process.argv);
} catch (error) {
  if (error instanceof ServerfilesError) {
    logger.error(error.message);
    process.exitCode = 1;
  } else {
    throw error;
  }
}
