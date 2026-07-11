import path from "node:path";
import { mergeComposeTemplate } from "../core/compose.js";
import { addStackToConfig, readConfig } from "../core/config.js";
import { paths } from "../core/paths.js";
import { ensureInitialized } from "../core/preflight.js";
import { ensureDirectories } from "../utils/fs.js";

export type StackDefinition = {
  name: string;
  template: string;
  dataDirs: string[];
};

export async function addStack(stack: StackDefinition) {
  await ensureInitialized();
  const config = await readConfig();
  await ensureDirectories(stack.dataDirs.map((dir) => path.join(paths.data, dir)));
  const result = await mergeComposeTemplate(stack.template, config);
  await addStackToConfig(stack.name);
  return result;
}
