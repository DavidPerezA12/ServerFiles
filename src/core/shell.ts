import { execa, type Options } from "execa";

export async function commandExists(command: string) {
  try {
    await execa("command", ["-v", command], { shell: true });
    return true;
  } catch {
    return false;
  }
}

export async function run(command: string, args: string[], options: Options = {}) {
  return execa(command, args, {
    stdio: "inherit",
    ...options
  });
}

export async function capture(command: string, args: string[], options: Options = {}) {
  const result = await execa(command, args, {
    ...options
  });

  return {
    ...result,
    stdout: String(result.stdout ?? ""),
    stderr: String(result.stderr ?? "")
  };
}
