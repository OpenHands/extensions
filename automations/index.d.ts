export interface RecommendedAutomation {
  id: string;
  name: string;
  category: string;
  description: string;
  prompt: string;
  exampleImplementation: string;
  requiredIntegrationIds: string[];
  popularityRank: number;
  estimatedSetupMinutes: number;
}

export const AUTOMATION_CATALOG: RecommendedAutomation[];
export default AUTOMATION_CATALOG;
