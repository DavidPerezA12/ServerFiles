import { addStack } from "./stack.js";

export async function addFilesStack() {
  return addStack({
    name: "files",
    template: "docker-compose.files.yml",
    dataDirs: ["files", "filebrowser/database", "filebrowser/config"]
  });
}
