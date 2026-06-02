module.exports = async ({ github, context, core }) => {
  const issueNumber = Number(process.env.ISSUE_NUMBER);
  const summary = (process.env.SUMMARY || "").trim();
  const classification = process.env.CLASSIFICATION || "no-match";
  const autoClose = process.env.AUTO_CLOSE_CANDIDATE === "true";
  const closeAfterDays = process.env.CLOSE_AFTER_DAYS || "3";
  let candidates = [];
  try {
    candidates = JSON.parse(process.env.CANDIDATE_ISSUES_JSON || "[]");
  } catch (error) {
    core.setFailed(`Invalid candidate JSON: ${error.message}`);
    return;
  }
  if (!Array.isArray(candidates)) {
    core.setFailed("CANDIDATE_ISSUES_JSON is not an array");
    return;
  }
  if (candidates.length === 0) {
    core.warning(`No candidate issues were returned for issue #${issueNumber}; skipping.`);
    return;
  }

  const canonicalIssueRaw = process.env.CANONICAL_ISSUE_NUMBER || candidates[0].number;
  const canonicalIssueNumber = canonicalIssueRaw ? Number(canonicalIssueRaw) : Number.NaN;
  const candidateLabel = "duplicate-candidate";

  function parseDuplicateCheckMarker(body) {
    if (!body) return null;
    const match = body.match(/<!-- openhands-duplicate-check canonical=(\d+) auto-close=(true|false) -->/);
    if (!match) return null;
    return {
      canonicalIssueNumber: Number(match[1]),
      autoClose: match[2] === "true",
    };
  }

  async function ensureCanonicalIssueIsOpenIssue() {
    let canonicalIssue;
    try {
      ({ data: canonicalIssue } = await github.rest.issues.get({
        owner: context.repo.owner,
        repo: context.repo.repo,
        issue_number: canonicalIssueNumber,
      }));
    } catch (error) {
      if (error.status === 404) {
        core.setFailed(`Canonical issue #${canonicalIssueNumber} does not exist.`);
        return false;
      }
      throw error;
    }
    if (canonicalIssue.pull_request) {
      core.setFailed(`Canonical issue #${canonicalIssueNumber} is a pull request, not an issue.`);
      return false;
    }
    if (canonicalIssue.state !== "open" || canonicalIssue.locked) {
      core.setFailed(`Canonical issue #${canonicalIssueNumber} must be an open, unlocked issue.`);
      return false;
    }
    return true;
  }

  async function ensureCandidateLabelOnIssue() {
    try {
      await github.rest.issues.getLabel({
        owner: context.repo.owner,
        repo: context.repo.repo,
        name: candidateLabel,
      });
    } catch (error) {
      if (error.status !== 404) throw error;
      await github.rest.issues.createLabel({
        owner: context.repo.owner,
        repo: context.repo.repo,
        name: candidateLabel,
        color: "f97316",
        description: "Potential duplicate awaiting auto-close or maintainer review",
      });
    }

    const { data: issue } = await github.rest.issues.get({
      owner: context.repo.owner,
      repo: context.repo.repo,
      issue_number: issueNumber,
    });
    const labelNames = (issue.labels || []).map((label) =>
      typeof label === "string" ? label : label.name,
    );
    if (!labelNames.includes(candidateLabel)) {
      await github.rest.issues.addLabels({
        owner: context.repo.owner,
        repo: context.repo.repo,
        issue_number: issueNumber,
        labels: [candidateLabel],
      });
    }
  }

  async function removeCandidateLabelFromIssue() {
    try {
      await github.rest.issues.removeLabel({
        owner: context.repo.owner,
        repo: context.repo.repo,
        issue_number: issueNumber,
        name: candidateLabel,
      });
    } catch (error) {
      if (error.status !== 404) throw error;
    }
  }

  if (!Number.isInteger(canonicalIssueNumber) || canonicalIssueNumber <= 0) {
    core.setFailed(`No canonical issue number was returned for issue #${issueNumber}.`);
    return;
  }
  if (canonicalIssueNumber === issueNumber) {
    core.setFailed(`Duplicate check cannot mark issue #${issueNumber} as a duplicate of itself.`);
    return;
  }

  if (!(await ensureCanonicalIssueIsOpenIssue())) return;

  const marker = `<!-- openhands-duplicate-check canonical=${canonicalIssueNumber} auto-close=${autoClose ? "true" : "false"} -->`;
  const header = candidates.length === 1
    ? "Found 1 possible duplicate issue:"
    : `Found ${candidates.length} possible duplicate issues:`;
  const candidateLines = candidates.map((candidate, index) =>
    `${index + 1}. [#${candidate.number}](${candidate.url}) — ${candidate.title}`,
  );

  const sections = [];
  if (summary) sections.push(summary, "");
  sections.push(header, "", ...candidateLines);

  if (classification === "overlapping-scope") {
    sections.push(
      "",
      "These may not be exact duplicates, but the scope appears to overlap enough that keeping discussion in one place may be more useful.",
    );
  }

  if (autoClose) {
    sections.push(
      "",
      `This issue will be automatically closed as a duplicate in ${closeAfterDays} days.`,
      "",
      "- If your issue is a duplicate, please close it and 👍 the existing issue instead",
      "- To prevent auto-closure, add a comment or 👎 this comment",
    );
  }

  sections.push(
    "",
    marker,
    "_This comment was created by an AI assistant (OpenHands) on behalf of the repository maintainer._",
  );
  const body = sections.join("\n").trim();

  const maxCommentPages = 50;
  let allComments = [];
  let page = 1;
  while (page <= maxCommentPages) {
    const { data: comments } = await github.rest.issues.listComments({
      owner: context.repo.owner,
      repo: context.repo.repo,
      issue_number: issueNumber,
      per_page: 100,
      page,
    });
    if (!comments || comments.length === 0) break;
    allComments = allComments.concat(comments);
    if (comments.length < 100) break;
    page += 1;
  }
  if (page > maxCommentPages) {
    core.setFailed(`Stopped loading comments for issue #${issueNumber} after ${maxCommentPages} pages.`);
    return;
  }

  const existing = allComments.find((comment) =>
    comment.body && comment.body.includes("<!-- openhands-duplicate-check "),
  );
  if (existing) {
    const existingMarker = parseDuplicateCheckMarker(existing.body);
    if (existingMarker) {
      if (
        existingMarker.canonicalIssueNumber !== canonicalIssueNumber ||
        existingMarker.autoClose !== autoClose
      ) {
        await github.rest.issues.updateComment({
          owner: context.repo.owner,
          repo: context.repo.repo,
          comment_id: existing.id,
          body,
        });
        if (autoClose) await ensureCandidateLabelOnIssue();
        else await removeCandidateLabelFromIssue();
        core.info(`Updated existing duplicate check comment ${existing.id} on issue #${issueNumber}.`);
        return;
      }
      if (autoClose) await ensureCandidateLabelOnIssue();
      else await removeCandidateLabelFromIssue();
    } else {
      core.warning(
        `Duplicate check comment already exists on issue #${issueNumber} but its marker could not be parsed; leaving label state unchanged.`,
      );
    }
    core.info(`Duplicate check comment already exists on issue #${issueNumber}; skipping.`);
    return;
  }

  await github.rest.issues.createComment({
    owner: context.repo.owner,
    repo: context.repo.repo,
    issue_number: issueNumber,
    body,
  });

  if (autoClose) await ensureCandidateLabelOnIssue();
};
