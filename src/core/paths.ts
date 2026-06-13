import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const sourceDir = path.dirname(fileURLToPath(import.meta.url));
const packageRoot = path.resolve(sourceDir, "..", "..");

export const paths = {
  home: os.homedir(),
  root: path.join(os.homedir(), ".serverfiles"),
  config: path.join(os.homedir(), ".serverfiles", "config.yml"),
  compose: path.join(os.homedir(), ".serverfiles", "docker-compose.yml"),
  stacks: path.join(os.homedir(), ".serverfiles", "stacks"),
  githubRunners: path.join(os.homedir(), ".serverfiles", "github-runners"),
  data: path.join(os.homedir(), ".serverfiles", "data"),
  logs: path.join(os.homedir(), ".serverfiles", "logs"),
  launchd: path.join(os.homedir(), ".serverfiles", "launchd"),
  backups: path.join(os.homedir(), ".serverfiles", "backups"),
  launchAgents: path.join(os.homedir(), "Library", "LaunchAgents"),
  templates: path.join(packageRoot, "templates")
};

export function templatePath(name: string) {
  return path.join(paths.templates, name);
}
