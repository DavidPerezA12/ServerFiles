import { mergeComposeTemplate } from "../core/compose.js";
import { addStackToConfig, readConfig } from "../core/config.js";
import { ensureInitialized } from "../core/preflight.js";

export async function addFilesStack() {
  await ensureInitialized();
  const config = await readConfig();
  const result = await mergeComposeTemplate("docker-compose.files.yml", config);
  await addStackToConfig("files");
  return result;
}
