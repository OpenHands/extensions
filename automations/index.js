import github_pr_reviewer from "./catalog/github-pr-reviewer.json" with { type: "json" };
import github_repo_monitor from "./catalog/github-repo-monitor.json" with { type: "json" };
import slack_standup_digest from "./catalog/slack-standup-digest.json" with { type: "json" };
import slack_channel_monitor from "./catalog/slack-channel-monitor.json" with { type: "json" };
import linear_triage_assistant from "./catalog/linear-triage-assistant.json" with { type: "json" };
import research_brief_writer from "./catalog/research-brief-writer.json" with { type: "json" };
import incident_retrospective_drafter from "./catalog/incident-retrospective-drafter.json" with { type: "json" };
import jira_issue_to_pr from "./catalog/jira-issue-to-pr.json" with { type: "json" };

import github_pr_reviewer_manifest from "./manifests/github-pr-reviewer.json" with { type: "json" };
import github_repo_monitor_manifest from "./manifests/github-repo-monitor.json" with { type: "json" };
import incident_retrospective_drafter_manifest from "./manifests/incident-retrospective-drafter.json" with { type: "json" };

import capabilities_fixture from "./fixtures/capabilities.json" with { type: "json" };
import github_pr_reviewer_fixtures from "./fixtures/github-pr-reviewer.json" with { type: "json" };
import github_repo_monitor_fixtures from "./fixtures/github-repo-monitor.json" with { type: "json" };
import incident_retrospective_drafter_fixtures from "./fixtures/incident-retrospective-drafter.json" with { type: "json" };

export const AUTOMATION_CATALOG = [
  github_pr_reviewer,
  github_repo_monitor,
  slack_standup_digest,
  slack_channel_monitor,
  linear_triage_assistant,
  research_brief_writer,
  incident_retrospective_drafter,
  jira_issue_to_pr,
];

export const AUTOMATION_MANIFESTS = [
  github_pr_reviewer_manifest,
  github_repo_monitor_manifest,
  incident_retrospective_drafter_manifest,
];

export const AUTOMATION_CAPABILITIES_FIXTURE = capabilities_fixture;

export const AUTOMATION_CONTRACT_FIXTURES = [
  github_pr_reviewer_fixtures,
  github_repo_monitor_fixtures,
  incident_retrospective_drafter_fixtures,
];

export default AUTOMATION_CATALOG;
