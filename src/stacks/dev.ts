import { mergeComposeTemplate } from "../core/compose.js";
import { addStackToConfig, readConfig } from "../core/config.js";
import { ensureInitialized } from "../core/preflight.js";

export async function addDevStack() {
  await ensureInitialized();
  const config = await readConfig();
  const result = await mergeComposeTemplate("docker-compose.dev.yml", config);
  await addStackToConfig("dev");
  return result;
}
