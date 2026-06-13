import path from "node:path";
import fs from "fs-extra";
import { paths } from "./paths.js";
import { ServerfilesError } from "./preflight.js";

export type GitHubRunnerScope = "repo" | "org";

export type GitHubRunnerPlan = {
  scope: GitHubRunnerScope;
  target: string;
  label: string;
  runnerName: string;
  runnerDir: string;
  settingsPath: string;
  workflowRunsOn: string;
  readme: string;
};

function slugify(value: string) {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9._-]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function validateGitHubRunnerTarget(scope: GitHubRunnerScope, target: string) {
  const trimmed = target.trim();

  if (scope === "repo" && !/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(trimmed)) {
    throw new ServerfilesError("Repository runners must use OWNER/REPO, for example david/serverfiles.");
  }

  if (scope === "org" && !/^[A-Za-z0-9_.-]+$/.test(trimmed)) {
    throw new ServerfilesError("Organization runners must use the organization name, for example my-org.");
  }

  return trimmed;
}

export function createGitHubRunnerPlan(options: {
  scope: GitHubRunnerScope;
  target: string;
  label: string;
}): GitHubRunnerPlan {
  const target = validateGitHubRunnerTarget(options.scope, options.target);
  const label = slugify(options.label);

  if (!label) {
    throw new ServerfilesError("Runner label cannot be empty.");
  }

  const targetSlug = slugify(target);
  const runnerName = `${label}-${targetSlug}`;
  const runnerDir = path.join(paths.githubRunners, targetSlug);
  const settingsPath =
    options.scope === "repo"
      ? `https://github.com/${target}/settings/actions/runners/new`
      : `https://github.com/organizations/${target}/settings/actions/runners/new`;
  const workflowRunsOn = `[self-hosted, macOS, ARM64, ${label}]`;

  return {
    scope: options.scope,
    target,
    label,
    runnerName,
    runnerDir,
    settingsPath,
    workflowRunsOn,
    readme: renderRunnerReadme({
      scope: options.scope,
      target,
      label,
      runnerName,
      runnerDir,
      settingsPath,
      workflowRunsOn
    })
  };
}

export async function writeGitHubRunnerPlan(plan: GitHubRunnerPlan) {
  await fs.ensureDir(plan.runnerDir);
  await fs.writeFile(path.join(plan.runnerDir, "README.md"), plan.readme, "utf8");
  await fs.writeFile(
    path.join(plan.runnerDir, ".gitignore"),
    [
      ".credentials",
      ".credentials_rsaparams",
      ".env",
      ".path",
      ".runner",
      "_diag/",
      "_work/",
      "actions-runner-*.tar.gz",
      ""
    ].join("\n"),
    "utf8"
  );
}

function renderRunnerReadme(plan: Omit<GitHubRunnerPlan, "readme">) {
  const configTarget =
    plan.scope === "repo"
      ? `https://github.com/${plan.target}`
      : `https://github.com/${plan.target}`;

  return `# GitHub Actions runner: ${plan.target}

This directory is the stable local home for a GitHub Actions self-hosted runner
on this Mac mini.

Scope: ${plan.scope}
Target: ${plan.target}
Runner name: ${plan.runnerName}
Required workflow labels: ${plan.workflowRunsOn}

## Register

Open this GitHub settings page:

${plan.settingsPath}

Choose macOS and ARM64, then run GitHub's generated download commands inside
this directory:

\`\`\`sh
cd "${plan.runnerDir}"
\`\`\`

When GitHub shows the \`./config.sh\` command, add these options if they are not
already present:

\`\`\`sh
--name ${plan.runnerName} --labels ${plan.label}
\`\`\`

The full command will look similar to this, but use the current token from
GitHub because it expires:

\`\`\`sh
./config.sh --url ${configTarget} --token TOKEN --name ${plan.runnerName} --labels ${plan.label}
\`\`\`

## Install as a service

After configuration succeeds:

\`\`\`sh
./svc.sh install
./svc.sh start
./svc.sh status
\`\`\`

The runner will keep listening after the terminal closes and should start again
when the Mac mini starts.

## Workflow

Use this in workflows that should run on this Mac mini:

\`\`\`yaml
runs-on: ${plan.workflowRunsOn}
\`\`\`

Do not commit runner credentials or downloaded runner state to any repository.
`;
}
