import { mergeComposeTemplate } from "../core/compose.js";
import { addStackToConfig, readConfig } from "../core/config.js";
import { ensureInitialized } from "../core/preflight.js";

export async function addPhotosStack() {
  await ensureInitialized();
  const config = await readConfig();
  const result = await mergeComposeTemplate("docker-compose.photos.yml", config);
  await addStackToConfig("photos");
  return result;
}
