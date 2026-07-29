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

export type AutomationPayloadValue =
  | string
  | number
  | boolean
  | null
  | AutomationPayloadValue[]
  | { [key: string]: AutomationPayloadValue };

export interface AutomationRequestBody {
  [key: string]: AutomationPayloadValue;
}

export interface AutomationSetup {
  version: "1.0";
  mode: AutomationSetupMode;
  form: AutomationForm;
  /** direct only. The request body the form values are mapped into. */
  payload?: AutomationRequestBody;
  /** assisted only. Setup context for the conversation that finishes setup. */
  message?: string;
}

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
