import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import {
  BRANCHES_COMMAND,
  DIFF_SUMMARY_COMMAND,
  LOG_COMMAND,
  parseBranches,
  parseDiffStats,
  parseLog,
  parseStatus,
  STATUS_COMMAND,
} from "./git-service";

let repository = "";

function shell(command: string): string {
  return execFileSync("/bin/sh", ["-c", command], { cwd: repository, encoding: "utf8" });
}

beforeAll(() => {
  repository = mkdtempSync(join(tmpdir(), "git-cockpit-protocol-"));
  shell("git init -b main && git config user.name 'Cockpit Test' && git config user.email 'cockpit@example.com'");
  writeFileSync(join(repository, "tracked.txt"), "first\n");
  writeFileSync(join(repository, "staged.txt"), "base\n");
  shell("git add tracked.txt staged.txt && git commit -m 'Initial flight' --quiet");
  writeFileSync(join(repository, "tracked.txt"), "changed\n");
  writeFileSync(join(repository, "staged.txt"), "staged change\n");
  writeFileSync(join(repository, "untracked.txt"), "new\n");
  shell("git add staged.txt");
});

afterAll(() => {
  if (repository.includes("git-cockpit-protocol-")) rmSync(repository, { recursive: true, force: true });
});

describe("real Git protocol compatibility", () => {
  it("parses actual status, refs, log, and numstat output", () => {
    const status = parseStatus(shell(STATUS_COMMAND));
    const branches = parseBranches(shell(BRANCHES_COMMAND));
    const commits = parseLog(shell(LOG_COMMAND));
    const stats = parseDiffStats(shell(DIFF_SUMMARY_COMMAND));

    expect(status.branch).toBe("main");
    expect(status.files.map((file) => file.path)).toEqual(expect.arrayContaining(["tracked.txt", "staged.txt", "untracked.txt"]));
    expect(branches).toEqual([expect.objectContaining({ name: "main", current: true })]);
    expect(commits[0]).toMatchObject({ author: "Cockpit Test", subject: "Initial flight" });
    expect(stats).toEqual(expect.arrayContaining([
      expect.objectContaining({ path: "tracked.txt", staged: false }),
      expect.objectContaining({ path: "staged.txt", staged: true }),
    ]));
  });
});
