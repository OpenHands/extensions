import github_pr_reviewer from "./catalog/github-pr-reviewer.json" with { type: "json" };
import github_repo_monitor from "./catalog/github-repo-monitor.json" with { type: "json" };
import slack_standup_digest from "./catalog/slack-standup-digest.json" with { type: "json" };
import slack_channel_monitor from "./catalog/slack-channel-monitor.json" with { type: "json" };
import linear_triage_assistant from "./catalog/linear-triage-assistant.json" with { type: "json" };
import research_brief_writer from "./catalog/research-brief-writer.json" with { type: "json" };
import incident_retrospective_drafter from "./catalog/incident-retrospective-drafter.json" with { type: "json" };

export const AUTOMATION_CATALOG = [
  github_pr_reviewer,
  github_repo_monitor,
  slack_standup_digest,
  slack_channel_monitor,
  linear_triage_assistant,
  research_brief_writer,
  incident_retrospective_drafter,
];
export default AUTOMATION_CATALOG;
