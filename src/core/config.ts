import fs from "fs-extra";
import YAML from "yaml";
import { ZodError } from "zod";
import { paths } from "./paths.js";
import { ServerfilesError } from "./preflight.js";
import { serverfilesConfigSchema, type ServerfilesConfig } from "../utils/validators.js";

export async function readConfig(): Promise<ServerfilesConfig> {
  const raw = await fs.readFile(paths.config, "utf8");
  try {
    return serverfilesConfigSchema.parse(YAML.parse(raw));
  } catch (error) {
    if (error instanceof ZodError) {
      throw new ServerfilesError(
        `Invalid config.yml: ${error.issues.map((issue) => issue.message).join("; ")}`
      );
    }

    throw error;
  }
}

export async function writeConfig(config: ServerfilesConfig) {
  const parsed = serverfilesConfigSchema.parse(config);
  await fs.writeFile(paths.config, YAML.stringify(parsed), "utf8");
}

export async function addStackToConfig(stack: string) {
  const config = await readConfig();
  if (!config.stacks.includes(stack)) {
    config.stacks.push(stack);
    await writeConfig(config);
  }
}
