import { Command } from "commander";
import { composePs } from "../core/docker.js";
import { readCompose } from "../core/compose.js";
import { readConfig } from "../core/config.js";
import { paths } from "../core/paths.js";
import { ensureReadyForCompose } from "../core/preflight.js";
import { logger } from "../utils/logger.js";

export const statusCommand = new Command("status")
  .description("Show container status and main service URLs")
  .action(async () => {
    await ensureReadyForCompose();
    logger.line("Containers");
    logger.line(await composePs(paths.compose));

    const config = await readConfig();
    const services = (await readCompose()).services ?? {};
    const urlLines: Array<[service: string, line: string]> = [
      ["caddy", `Caddy HTTP: http://localhost:${config.ports.caddyHttp}`],
      ["caddy", `Caddy HTTPS: https://localhost:${config.ports.caddyHttps}`],
      ["postgres", `PostgreSQL: localhost:${config.ports.postgres}`],
      ["redis", `Redis: localhost:${config.ports.redis}`],
      ["mongodb", `MongoDB: localhost:${config.ports.mongodb}`],
      ["adminer", `Adminer: http://localhost:${config.ports.adminer}`],
      ["uptime-kuma", `Uptime Kuma: http://localhost:${config.ports.uptimeKuma}`],
      ["filebrowser", `File Browser: http://localhost:${config.ports.filebrowser}`],
      ["immich-server", `Immich: http://localhost:${config.ports.immich}`]
    ];

    logger.line();
    logger.line("URLs and ports");
    for (const [service, line] of urlLines) {
      if (services[service]) {
        logger.line(line);
      }
    }
  });
