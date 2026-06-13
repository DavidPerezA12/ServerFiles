import assert from "node:assert/strict";
import test from "node:test";
import {
  createGitHubRunnerPlan,
  validateGitHubRunnerTarget
} from "../src/core/githubRunner.js";

test("creates a repository runner plan with mac mini labels", () => {
  const plan = createGitHubRunnerPlan({
    scope: "repo",
    target: "david/serverfiles",
    label: "mac-mini"
  });

  assert.equal(plan.runnerName, "mac-mini-david-serverfiles");
  assert.equal(plan.workflowRunsOn, "[self-hosted, macOS, ARM64, mac-mini]");
  assert.match(plan.settingsPath, /david\/serverfiles\/settings\/actions\/runners\/new$/);
  assert.match(plan.readme, /--name mac-mini-david-serverfiles --labels mac-mini/);
});

test("creates an organization runner plan", () => {
  const plan = createGitHubRunnerPlan({
    scope: "org",
    target: "personal-ci",
    label: "mac-mini"
  });

  assert.equal(
    plan.settingsPath,
    "https://github.com/organizations/personal-ci/settings/actions/runners/new"
  );
});

test("validates runner target shape", () => {
  assert.equal(validateGitHubRunnerTarget("repo", "owner/repo"), "owner/repo");
  assert.throws(() => validateGitHubRunnerTarget("repo", "owner"), /OWNER\/REPO/);
  assert.throws(() => validateGitHubRunnerTarget("org", "owner/repo"), /organization name/);
});
