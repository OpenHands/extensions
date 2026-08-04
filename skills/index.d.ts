/**
 * Categories for skill entries, consumed by the agent-canvas /skills facet rail.
 *
 * Sourced from the `category` field on marketplace entries whose `source` starts with `./skills/`.
 * Distinct from the `category` on marketplace *plugin* entries, which serves Claude Code marketplace browsing.
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
