import { Command } from "commander";
import { composeLogs } from "../core/docker.js";
import { paths } from "../core/paths.js";
import { ensureReadyForCompose } from "../core/preflight.js";

export const logsCommand = new Command("logs")
  .description("Show Docker Compose logs")
  .option("-f, --follow", "Follow logs", false)
  .option("--tail <lines>", "Number of log lines to show", "100")
  .action(async (options: { follow: boolean; tail: string }) => {
    await ensureReadyForCompose();
    await composeLogs(paths.compose, options.follow, options.tail);
  });
