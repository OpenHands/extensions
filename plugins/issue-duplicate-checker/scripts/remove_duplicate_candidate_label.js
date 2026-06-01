module.exports = async ({ github, context, core }) => {
  const issueNumber = context.issue.number;
  const commenter = context.payload.comment?.user?.login ?? "";
  const normalizedCommenter = commenter.toLowerCase();

  if (normalizedCommenter.endsWith("[bot]") || normalizedCommenter === "all-hands-bot") {
    core.info(`Skipping duplicate-candidate label removal for bot comment from ${commenter || "unknown"}`);
    return;
  }

  core.info(`Removing duplicate-candidate label from issue #${issueNumber} after comment from ${commenter}`);

  try {
    await github.rest.issues.removeLabel({
      owner: context.repo.owner,
      repo: context.repo.repo,
      issue_number: issueNumber,
      name: "duplicate-candidate",
    });
  } catch (error) {
    if (error.status === 404) {
      core.info(`duplicate-candidate label was already removed from issue #${issueNumber}`);
      return;
    }
    throw error;
  }
};
