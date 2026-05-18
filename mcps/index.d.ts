export type MarketplaceFieldType = "text" | "password";

export interface MarketplaceField {
  key: string;
  label: string;
  type?: MarketplaceFieldType;
  placeholder?: string;
  helperText?: string;
  required?: boolean;
}

export type MarketplaceTemplate =
  | {
      kind: "shttp";
      url: string;
      apiKeyOptional?: boolean;
    }
  | {
      kind: "sse";
      url: string;
      apiKeyOptional?: boolean;
    }
  | {
      kind: "stdio";
      serverName: string;
      command: string;
      args: string[];
      envFields?: MarketplaceField[];
      argFields?: MarketplaceField[];
    };

export interface McpCatalogEntry {
  id: string;
  name: string;
  description: string;
  docsUrl?: string;
  iconBg: string;
  iconColor?: string;
  keywords?: string[];
  popularityRank?: number;
  availability?: "all" | "local";
  installHint?: string;
  template: MarketplaceTemplate;
}

export const MCP_CATALOG: McpCatalogEntry[];
export default MCP_CATALOG;
