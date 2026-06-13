import fs from "fs-extra";
import path from "node:path";

export async function ensureDirectories(paths: string[]) {
  await Promise.all(paths.map((dir) => fs.ensureDir(dir)));
}

export async function writeFileIfMissing(filePath: string, content: string) {
  if (await fs.pathExists(filePath)) {
    return false;
  }

  await fs.ensureDir(path.dirname(filePath));
  await fs.writeFile(filePath, content, "utf8");
  return true;
}
