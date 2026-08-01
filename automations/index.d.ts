export interface RecommendedAutomation {
  id: string;
  name: string;
  category: string;
  description: string;
  requires: AutomationPrerequisites;
  popularityRank: number;
  estimatedSetupMinutes: number;
  /**
   * The `skills/` directory that builds this automation today. Defaults to
   * `id`; present only where the two differ. Look the launch command up from
   * that skill's entry in `SKILLS_CATALOG` rather than storing it here.
   */
  skill?: string;
  exampleImplementation: string;
  /** Present when this automation ships an extension-owned setup experience. */
  setup?: AutomationSetup;
}

/**
 * The extension-owned configuration experience for one automation.
 *
 * Mirrors the `setup` block in `automations/catalog.schema.json`, which is
 * authoritative. It describes how an automation is *configured*; it never
 * describes what the automation does at runtime.
 *
 * It states only what varies between automations, and states each of those
 * things once. Everything else is the same for every automation and is the
 * host's to generate: the slash command (`/<id>:setup`), the setup route
 * (`/automations/new/<id>`), the capabilities check, the preflight call, the
 * mapping from a rejected payload path back to the input at fault, the review
 * screen, the navigation after a success, and the analytics stages.
 */

export type AutomationSetupMode = "direct" | "assisted";
export type AutomationFieldType =
  | "text"
  | "textarea"
  | "select"
  | "cron"
  | "timezone"
  | "repo-picker";
export type AutomationGitProvider = "github" | "gitlab" | "bitbucket";
export type AutomationTriggerKind = "cron" | "event";

export interface AutomationFieldOption {
  value: string;
  label: string;
}

export interface AutomationFieldConstraints {
  minLength?: number;
  maxLength?: number;
  /** Host-implemented check, named from a closed set. Entries supply no regex. */
  format?: "safeExpressionLiteral";
}

export interface AutomationFormField {
  type: AutomationFieldType;
  label: string;
  help: string;
  placeholder?: string;
  default?: string;
  required: boolean;
  provider?: AutomationGitProvider;
  options?: AutomationFieldOption[];
  constraints?: AutomationFieldConstraints;
}

/** Keyed by field name, which is what `{{form.<name>}}` resolves against. */
export type AutomationFormFields = Record<string, AutomationFormField>;

export interface AutomationIntegrationRequirement {
  /** Why this automation needs it. Omitted when there is no setup flow to show it in. */
  message?: string;
  /** Defaults to true. `false` lets setup continue while it is unconnected. */
  required?: false;
}

export interface AutomationPrerequisites {
  /** Keyed by integration catalog id. */
  integrations: Record<string, AutomationIntegrationRequirement>;
  /** Deployment capabilities this automation cannot run without. */
  features?: string[];
}

/** The inputs that decide when the automation runs, keyed by trigger kind. */
export type AutomationTriggerForm = Partial<
  Record<AutomationTriggerKind, AutomationFormFields>
>;

export interface AutomationForm {
  note?: string;
  triggers?: AutomationTriggerForm;
  /** Every other input: the arguments to the automation itself. */
  args: AutomationFormFields;
}

export interface AutomationSetup {
  version: "1.0";
  mode: AutomationSetupMode;
  form: AutomationForm;
  /** direct only. What the automation is told to do. */
  prompt?: string;
  /** direct only, event trigger only. Which delivered events belong to it. */
  filter?: string;
  /**
   * Setup context for the conversation that finishes setup. Required for
   * assisted mode. Optional for direct mode, where it seeds the fallback
   * conversation offered when the deployment cannot run the direct path.
   */
  message?: string;
}

/**
 * The production Automation interface manifest.
 *
 * Mirrors `automations/interface.schema.json`, which is authoritative. The
 * catalog states what varies per automation; this states the domain-level
 * facts of the interface itself: routes, navigation, page-identity copy, the
 * settable attributes of an automation, the import/export envelope, the
 * service-relative endpoints, and the featured and responder id lists. The
 * host validates it at admission and falls back to its built-in defaults when
 * it is absent or rejected.
 */

export interface AutomationInterfaceRoutes {
  list: string;
  /** Carries the `:automationId` segment the host substitutes. */
  setup: string;
  /** Carries the `:automationId` segment the host substitutes. */
  detail: string;
}

export interface AutomationInterfaceNavigation {
  sidebar: { label: string };
  commandMenu: { title: string; description: string; keywords: string };
}

export interface AutomationInterfacePages {
  list: { title: string; subtitle: string };
  detail: { backLabel: string };
  edit: { title: string };
}

export type AutomationAttributeType =
  | "text"
  | "textarea"
  | "number"
  | "llm-profile"
  | "schedule";

/** The closed set of runtime-model properties a client may offer for setting. */
export type AutomationAttributeName =
  | "name"
  | "prompt"
  | "model"
  | "timeout"
  | "schedule";

export interface AutomationAttributeConstraints {
  min?: number;
  max?: number;
}

/** How one settable attribute of an existing Automation is offered. */
export interface AutomationAttribute {
  type: AutomationAttributeType;
  label: string;
  help?: string;
  required: boolean;
  /** Only a `number` attribute carries constraints. */
  constraints?: AutomationAttributeConstraints;
}

/**
 * The input surface of an existing Automation, keyed by the runtime-model
 * property the host sends. How a client offers these - Agent Canvas renders
 * an edit dialog - is the client's choice, not stated here.
 */
export type AutomationInterfaceAttributes = Partial<
  Record<AutomationAttributeName, AutomationAttribute>
>;

export interface AutomationImportDefaults {
  /** Provider inferred for short owner/repo repository URLs on import. */
  repoProvider: AutomationGitProvider;
  /** Event source of the placeholder trigger that keeps an import inert. */
  placeholderEventSource: string;
}

export interface AutomationInterfaceImportExport {
  fileKind: string;
  fileVersion: 1;
  filenameSuffix: string;
  importDefaults: AutomationImportDefaults;
}

/**
 * Service-relative paths the host calls. Relative paths only: the base path,
 * methods, headers, and auth remain the host's. `{id}` marks where the host
 * substitutes the automation id.
 */
export interface AutomationInterfaceEndpoints {
  list: string;
  detail: string;
  dispatch: string;
  runs: string;
  tarball: string;
  health: string;
  capabilities: string;
  validate: string;
  createPrompt: string;
  createPlugin: string;
}

export interface AutomationInterfaceManifest {
  version: "1.0";
  routes: AutomationInterfaceRoutes;
  navigation: AutomationInterfaceNavigation;
  pages: AutomationInterfacePages;
  docsUrl: string;
  attributes: AutomationInterfaceAttributes;
  importExport: AutomationInterfaceImportExport;
  endpoints: AutomationInterfaceEndpoints;
  featuredAutomationIds: string[];
  responderIntegrationIds: string[];
}

export const AUTOMATION_INTERFACE: AutomationInterfaceManifest;

export const AUTOMATION_CATALOG: RecommendedAutomation[];
/**
 * Return the full automation catalog.
 * Reads the generated static import index over `automations/catalog/<id>/manifest.json`.
 * Returns an independent copy.
 */
export function listAutomationCatalog(): RecommendedAutomation[];
/** Return one automation catalog entry by id as an independent copy. */
export function getAutomationCatalogEntry(
  id: string,
): RecommendedAutomation | undefined;
export default AUTOMATION_CATALOG;
