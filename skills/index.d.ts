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
  /** `true` when the skill is on for every new workspace. Absent means off. */
  defaultEnabled?: boolean;
  license?: string;
  compatibility?: string;
}

export const SKILLS_CATALOG: SkillCatalogEntry[];

/** Names of the entries whose `defaultEnabled` is `true`, in catalog order. */
export const DEFAULT_ENABLED_SKILL_NAMES: readonly string[];

export default SKILLS_CATALOG;
