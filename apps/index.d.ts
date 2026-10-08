export interface AppCatalogEntry {
  id: string;
  name: string;
  description: string;
  source: string;
  manifest: string;
  beta: boolean;
}

export const APPS_CATALOG: AppCatalogEntry[];
export default APPS_CATALOG;
