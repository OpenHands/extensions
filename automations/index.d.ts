export interface RecommendedAutomation {
  id: string;
  name: string;
  category: string;
  /**
   * The glyph the card shows, from the closed set the interface manifest's
   * navigation uses. Absent means the host derives one from the integrations.
   */
  icon?:
    | "layout-dashboard"
    | "sparkles"
    | "bot"
    | "circle-alert"
    | "activity"
    | "timer";
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
  /**
   * repo-picker only. The field collects several repositories rather than one,
   * and its value is a list. A whole-value placeholder resolves to that list.
   */
  multiple?: true;
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

/** A config.json leaf: templated string, number, boolean, null, or a nesting of those. */
export type AutomationBundleConfigValue =
  | string
  | number
  | boolean
  | null
  | AutomationBundleConfigValue[]
  | { [key: string]: AutomationBundleConfigValue };

/**
 * The script tarball a direct entry may ship instead of a prompt, for an
 * automation that is deterministic machinery rather than judgement.
 */
export interface AutomationBundle {
  /** The command run inside the extracted tarball. */
  entrypoint: string;
  /** Script run once before the entrypoint. Absent when nothing to install. */
  setupScript?: string;
  /** Seconds a run may take, when the service default is not enough. */
  timeout?: number;
  /** Packed path -> the repository path the file is read from at build time. */
  files: Record<string, string>;
  /** Rendered from the form and packed as config.json beside the entrypoint. */
  config: Record<string, AutomationBundleConfigValue>;
}

export interface AutomationSetup {
  version: "1.0";
  mode: AutomationSetupMode;
  form: AutomationForm;
  /** direct only. What the automation is told to do. */
  prompt?: string;
  /** direct only, and the alternative to `prompt`. Exactly one is present. */
  bundle?: AutomationBundle;
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
  /** The templates sub-page. Static: there is no parameter to substitute. */
  templates: string;
}

/** An icon name from the host's closed icon map. */
export type AutomationIconSlug =
  | "layout-dashboard"
  | "sparkles"
  | "bot"
  | "circle-alert"
  | "activity"
  | "timer";

/** The pages a sub-page navigation item may point at. */
export type AutomationSubPageId = "list" | "templates";

export interface AutomationSubPageNavItem {
  /** The `pages` entry this item navigates to; its route comes from `routes`. */
  page: AutomationSubPageId;
  label: string;
  icon: AutomationIconSlug;
}

export interface AutomationInterfaceNavigation {
  sidebar: { label: string };
  commandMenu: { title: string; description: string; keywords: string };
  /** The ordered sub-page navigation of the Automation interface. */
  subPages: AutomationSubPageNavItem[];
}

/** A value the host computes; a tile picks and captions it, never defines it. */
export type AutomationOverviewMetric =
  | "automations"
  | "needs-attention"
  | "total-runs"
  | "average-duration";

/**
 * One summary tile. `detail` captions the value; `zeroDetail`, when present,
 * replaces it while the value is zero. Both are plain substitution over the
 * metric's placeholder namespace: only the `automations` metric exposes
 * `{{active}}`, so every other tile's copy is literal.
 */
export interface AutomationOverviewTile {
  metric: AutomationOverviewMetric;
  label: string;
  detail: string;
  zeroDetail?: string;
  icon: AutomationIconSlug;
}

export interface AutomationOverview {
  /** Names the tiles section for assistive technology. */
  label: string;
  tiles: AutomationOverviewTile[];
}

export type AutomationStatusFilterValue =
  | "all"
  | "active"
  | "failing"
  | "disabled";
export type AutomationTriggerFilterValue = "all" | "schedule" | "event";

/**
 * A filter dropdown. Values name predicates the host implements; the manifest
 * supplies which appear and their labels. `label` is the control's accessible
 * name. The `all` option is the host's default and reset target.
 */
export interface AutomationStatusFilter {
  id: "status";
  label: string;
  options: { value: AutomationStatusFilterValue; label: string }[];
}

export interface AutomationTriggerFilter {
  id: "trigger";
  label: string;
  options: { value: AutomationTriggerFilterValue; label: string }[];
}

export type AutomationDashboardFilter =
  | AutomationStatusFilter
  | AutomationTriggerFilter;

/** A comparator the host implements, named from a closed set. */
export type AutomationSortValue = "last-run" | "runs" | "name";

export interface AutomationDashboardSort {
  /** The control's accessible name. */
  label: string;
  options: { value: AutomationSortValue; label: string }[];
  /** Must be one of the declared option values. */
  default: AutomationSortValue;
}

/**
 * Copy for the per-automation run insights on cards and rows. The states,
 * precedence, sampling, and value formatting are the host's; the manifest
 * names them.
 */
export interface AutomationListInsights {
  health: {
    healthy: string;
    failing: string;
    running: string;
    disabled: string;
    neverRun: string;
    checking: string;
  };
  lastRun: { label: string; never: string; justNow: string };
  stats: { runs: string; recentSuccess: string; averageDuration: string };
}

/**
 * The templates sub-page identity. Its body - the catalog cards and their
 * launch behavior - is the host's existing catalog surface.
 */
export interface AutomationTemplatesPage {
  title: string;
  description: string;
}

export interface AutomationInterfacePages {
  list: {
    title: string;
    subtitle: string;
    overview: AutomationOverview;
    /** The filter dropdowns of the list page, in render order. */
    filters: AutomationDashboardFilter[];
    sort: AutomationDashboardSort;
    insights: AutomationListInsights;
  };
  detail: { backLabel: string };
  edit: { title: string };
  templates: AutomationTemplatesPage;
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
  /** The raw create endpoint, which a bundle entry is created through. */
  createBundle: string;
  /** Where a bundle's tarball is uploaded before that create call. */
  uploads: string;
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
/**
 * Return the files a bundle entry ships, keyed by the path each takes inside
 * the tarball, as an independent copy. Undefined for an entry with no bundle.
 *
 * The contents are inlined at build time from the repository paths
 * `setup.bundle.files` names, because a host packing the tarball has the
 * published package but not the repository.
 */
export function getAutomationBundleFiles(
  id: string,
): Record<string, string> | undefined;
export default AUTOMATION_CATALOG;
