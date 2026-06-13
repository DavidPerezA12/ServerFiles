import { Command } from "commander";
import {
  createGitHubRunnerPlan,
  writeGitHubRunnerPlan,
  type GitHubRunnerScope
} from "../core/githubRunner.js";
import { ensureInitialized } from "../core/preflight.js";
import { logger } from "../utils/logger.js";

export const githubRunnerCommand = new Command("github-runner")
  .description("Prepare local setup notes for a GitHub Actions self-hosted runner")
  .argument("<target>", "OWNER/REPO for repo scope, or ORG with --scope org")
  .option("--scope <scope>", "Runner scope: repo or org", "repo")
  .option("--label <label>", "Custom runner label used by workflows", "mac-mini")
  .action(async (target: string, options: { scope: string; label: string }) => {
    await ensureInitialized();

    if (options.scope !== "repo" && options.scope !== "org") {
      logger.error("Scope must be repo or org.");
      process.exitCode = 1;
      return;
    }

    const plan = createGitHubRunnerPlan({
      scope: options.scope as GitHubRunnerScope,
      target,
      label: options.label
    });

    await writeGitHubRunnerPlan(plan);

    logger.success(`Prepared GitHub runner directory: ${plan.runnerDir}`);
    logger.info(`Open GitHub settings: ${plan.settingsPath}`);
    logger.info(`Runner name: ${plan.runnerName}`);
    logger.info(`Workflow runs-on: ${plan.workflowRunsOn}`);
    logger.warn("Use GitHub's current token when running ./config.sh; do not commit runner secrets.");
  });
