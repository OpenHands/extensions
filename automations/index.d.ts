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
  /** Present when this automation ships an extension-owned setup experience. */
  setup?: AutomationSetup;
}

/**
 * The extension-owned configuration experience for one automation.
 *
 * Mirrors the `setup` block in `automations/catalog.schema.json`, which is
 * authoritative. It describes how an automation is *configured*; it never
 * describes what the automation does at runtime.
 */

export type AutomationSetupMode = "direct" | "assisted";
export type AutomationFieldType =
  | "text"
  | "textarea"
  | "select"
  | "cron"
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
  name: string;
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

export interface AutomationSetupRoute {
  path: string;
  page: "setup";
}

export interface AutomationCapabilityRequirements {
  triggerKinds?: AutomationTriggerKind[];
  eventSources?: string[];
  eventTypes?: string[];
  features?: string[];
  ready?: true;
}

export interface AutomationCapabilityBinding {
  field: string;
  constraint: "options" | "minIntervalSeconds";
  from: string;
}

export interface AutomationCapabilities {
  discovery: { method: "GET"; path: string };
  requires: AutomationCapabilityRequirements;
  bindings?: AutomationCapabilityBinding[];
  onUnsupported: { behavior: "block"; message: string };
}

export interface AutomationIntegrationRequirement {
  id: string;
  reason: string;
  enforcement: "block" | "warn";
}

/** Credential names only. A setup block never carries a credential value. */
export interface AutomationSecretRequirement {
  key: string;
  label: string;
  help: string;
  required: boolean;
}

export interface AutomationPrerequisites {
  integrations: AutomationIntegrationRequirement[];
  secrets: AutomationSecretRequirement[];
  onUnmet: { behavior: "block"; message: string };
  onWarn?: { behavior: "continue"; message: string };
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

export interface AutomationPreflight {
  method: "POST";
  path: string;
  runOn: ("fieldBlur" | "beforeSubmit")[];
  debounceMs?: number;
  body: AutomationRequestBody;
}

export interface AutomationValidation {
  /** Omitted when local validation is the only check available before submit. */
  preflight?: AutomationPreflight;
  onInvalid: {
    behavior: "blockSubmit";
    errorTarget: "field" | "form";
    /** Payload path to the form field, or fields, that produced it. */
    errorMap?: Record<string, string | string[]>;
  };
}

export interface AutomationReviewRow {
  label: string;
  value: string;
}

export interface AutomationReview {
  title: string;
  note?: string;
  emptyValueText?: string;
  summary: AutomationReviewRow[];
  confirmLabel: string;
}

export interface AutomationSubmitOnSuccess {
  behavior: "navigate";
  to: string;
}

export interface AutomationSubmitOnError {
  behavior: "stayOnForm";
  errorTarget: "field" | "form";
  reuseErrorMap?: boolean;
  message?: string;
}

export interface AutomationDirectSubmit {
  action: "automation.create";
  endpoint: { method: "POST"; path: string };
  payload: AutomationRequestBody;
  onSuccess: AutomationSubmitOnSuccess;
  onError: AutomationSubmitOnError;
}

export interface AutomationAssistedSubmit {
  action: "conversation.start";
  message: string;
  onSuccess: AutomationSubmitOnSuccess;
  onError: AutomationSubmitOnError;
}

export type AutomationSubmit =
  | AutomationDirectSubmit
  | AutomationAssistedSubmit;

export type AutomationAnalyticsEvent =
  | "route.entered"
  | "capabilities.resolved"
  | "validation.succeeded"
  | "submit.succeeded"
  | "submit.failed";

export interface AutomationAnalyticsStage {
  id: string;
  on: AutomationAnalyticsEvent;
  properties: Record<string, string | number | boolean>;
}

export interface AutomationAnalytics {
  consent: "required";
  stages: AutomationAnalyticsStage[];
}

export interface AutomationSetup {
  version: "1.0";
  mode: AutomationSetupMode;
  routes: AutomationSetupRoute[];
  capabilities?: AutomationCapabilities;
  requires?: AutomationPrerequisites;
  form: { note?: string; fields: AutomationFormField[] };
  validation?: AutomationValidation;
  review: AutomationReview;
  submit: AutomationSubmit;
  analytics: AutomationAnalytics;
}

export const AUTOMATION_CATALOG: RecommendedAutomation[];
/**
 * Return the full automation catalog.
 * Reads the generated static import index over `automations/catalog/<id>.json`.
 * Returns an independent copy.
 */
export function listAutomationCatalog(): RecommendedAutomation[];
/** Return one automation catalog entry by id as an independent copy. */
export function getAutomationCatalogEntry(
  id: string,
): RecommendedAutomation | undefined;
export default AUTOMATION_CATALOG;
