import { Command } from "commander";
import { disableAutostart, enableAutostart, launchdTargetPath } from "../core/launchd.js";
import { ensureInitialized, ensureMacOS, ensureDockerCompose } from "../core/preflight.js";
import { logger } from "../utils/logger.js";

export function autostartCommand(name: "enable-autostart" | "disable-autostart") {
  return new Command(name)
    .description(
      name === "enable-autostart"
        ? "Create and load a launchd plist for macOS autostart"
        : "Unload and remove the launchd plist"
    )
    .action(async () => {
      ensureMacOS();

      if (name === "enable-autostart") {
        await ensureInitialized();
        await ensureDockerCompose();
        await enableAutostart();
        logger.success(`Autostart enabled: ${launchdTargetPath()}`);
        return;
      }

      await disableAutostart();
      logger.success("Autostart disabled");
    });
}
