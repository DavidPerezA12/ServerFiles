import { Command } from "commander";
import { composePs } from "../core/docker.js";
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
    logger.line();
    logger.line("URLs and ports");
    logger.line(`PostgreSQL: localhost:${config.ports.postgres}`);
    logger.line(`Redis: localhost:${config.ports.redis}`);
    logger.line(`MongoDB: localhost:${config.ports.mongodb}`);
    logger.line(`Adminer: http://localhost:${config.ports.adminer}`);
    logger.line(`Uptime Kuma: http://localhost:${config.ports.uptimeKuma}`);
    logger.line(`Caddy HTTP: http://localhost:${config.ports.caddyHttp}`);
    logger.line(`Caddy HTTPS: https://localhost:${config.ports.caddyHttps}`);
  });
