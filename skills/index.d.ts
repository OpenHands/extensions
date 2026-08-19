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
  /**
   * `true` when the skill is on for every new workspace. Absent means off.
   *
   * This is the manifest's answer to "is this enabled for every new user?",
   * not a badge and not a claim that the skill cannot be turned off - a host
   * seeds a fresh workspace from it and the user is free to change it after.
   */
  defaultEnabled?: boolean;
  license?: string;
  compatibility?: string;
}

export const SKILLS_CATALOG: SkillCatalogEntry[];

/**
 * Names of the entries whose `defaultEnabled` is `true`, in catalog order.
 *
 * Exported so hosts seed a new workspace from one place instead of each
 * recomputing the same filter over `SKILLS_CATALOG`.
 */
export const DEFAULT_ENABLED_SKILL_NAMES: readonly string[];

export default SKILLS_CATALOG;
