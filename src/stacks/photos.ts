import { addStack } from "./stack.js";

export async function addPhotosStack() {
  return addStack({
    name: "photos",
    template: "docker-compose.photos.yml",
    dataDirs: ["immich/library", "immich/postgres"]
  });
}
