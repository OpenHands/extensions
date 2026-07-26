/**
 * Categories consumed by the agent-canvas /skills facet rail.
 *
 * Sourced from the `category` field on marketplace entries whose `source`
 * starts with `./skills/`. This is NOT the same taxonomy as the `category` on
 * marketplace *plugin* entries, which serves Claude Code marketplace browsing.
 *
 * Two assignments look inconsistent when skimmed and are deliberate:
 * `add-javadoc` is `code-quality` rather than `writing` because its subject is
 * code, and `github-pr-review` is `code-hosting` (GitHub API mechanics) while
 * the adjacently-named `github-pr-reviewer` is `automations` (it deploys a
 * cron job).
 */
export type SkillCategoryId =
  | "automations"
  | "environment"
  | "code-hosting"
  | "agent-authoring"
  | "code-quality"
  | "integrations"
  | "writing"
  | "design"
  | "other";

export const SKILL_CATEGORY_IDS: readonly SkillCategoryId[];

export interface SkillCatalogEntry {
  name: string;
  description: string;
  triggers: string[];
  content: string;
  /** `"other"` when the skill has no marketplace entry. */
  category: SkillCategoryId;
  license?: string;
  compatibility?: string;
}

export const SKILLS_CATALOG: SkillCatalogEntry[];
export default SKILLS_CATALOG;
