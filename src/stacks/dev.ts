import { addStack } from "./stack.js";

export async function addDevStack() {
  return addStack({
    name: "dev",
    template: "docker-compose.dev.yml",
    dataDirs: ["postgres", "redis", "mongodb", "uptime-kuma"]
  });
}
