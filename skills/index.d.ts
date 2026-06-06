export interface SkillCatalogEntry {
  name: string;
  description: string;
  triggers: string[];
  content: string;
  license?: string;
  compatibility?: string;
}

export const SKILLS_CATALOG: SkillCatalogEntry[];
export default SKILLS_CATALOG;
