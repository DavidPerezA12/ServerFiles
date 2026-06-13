import { capture } from "./shell.js";

export async function isColimaRunning() {
  try {
    const result = await capture("colima", ["status"]);
    return /Running/i.test(result.stdout);
  } catch {
    return false;
  }
}
