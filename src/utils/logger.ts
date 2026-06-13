import chalk from "chalk";

export const logger = {
  info(message: string) {
    console.log(chalk.cyan("info"), message);
  },
  success(message: string) {
    console.log(chalk.green("ok"), message);
  },
  warn(message: string) {
    console.log(chalk.yellow("warn"), message);
  },
  error(message: string) {
    console.error(chalk.red("error"), message);
  },
  line(message = "") {
    console.log(message);
  },
  check(label: string, ok: boolean, detail?: string) {
    const mark = ok ? chalk.green("yes") : chalk.red("no");
    const suffix = detail ? chalk.gray(` ${detail}`) : "";
    console.log(`${mark} ${label}${suffix}`);
  }
};
