import fs from "fs-extra";
import { Command } from "commander";
import path from "node:path";
import { paths, templatePath } from "../core/paths.js";
import { ensureDirectories, writeFileIfMissing } from "../utils/fs.js";
import { logger } from "../utils/logger.js";

const dataDirs = ["caddy", "postgres", "redis", "mongodb", "uptime-kuma", "adminer"];

export const initCommand = new Command("init")
  .description("Create the ~/.serverfiles structure and initial config")
  .action(async () => {
    await ensureDirectories([
      paths.root,
      paths.stacks,
      paths.githubRunners,
      paths.data,
      paths.logs,
      paths.launchd,
      paths.backups,
      ...dataDirs.map((dir) => path.join(paths.data, dir))
    ]);

    const configTemplate = (await fs.readFile(templatePath("config.yml"), "utf8")).replaceAll(
      "{{ROOT}}",
      paths.root
    );
    const composeTemplate = await fs.readFile(templatePath("docker-compose.base.yml"), "utf8");

    const configCreated = await writeFileIfMissing(paths.config, configTemplate);
    const composeCreated = await writeFileIfMissing(paths.compose, composeTemplate);

    logger.success("Initialized ~/.serverfiles");
    logger.info(`${configCreated ? "Created" : "Kept"} ${paths.config}`);
    logger.info(`${composeCreated ? "Created" : "Kept"} ${paths.compose}`);
  });
