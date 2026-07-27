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

/**
 * The extension-owned configuration experience for one automation.
 *
 * Mirrors `automations/manifest.schema.json`, which is authoritative. A manifest
 * describes how an automation is *configured*; it never describes what the
 * automation does at runtime.
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
  /** Host-implemented check, named from a closed set. Manifests supply no regex. */
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

export interface AutomationManifestRoute {
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

/** Credential names only. A manifest never carries a credential value. */
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

export interface AutomationManifest {
  manifestVersion: "1.0";
  id: string;
  name: string;
  category: string;
  description: string;
  setupMode: AutomationSetupMode;
  routes: AutomationManifestRoute[];
  capabilities?: AutomationCapabilities;
  requires?: AutomationPrerequisites;
  form: { note?: string; fields: AutomationFormField[] };
  validation?: AutomationValidation;
  review: AutomationReview;
  submit: AutomationSubmit;
  analytics: AutomationAnalytics;
}

/**
 * Worked request and response examples for one manifest. Contract inputs for
 * OpenHands/agent-canvas and OpenHands/automation - nothing installs or runs them.
 */

export interface AutomationPreflightError {
  field: string;
  code?: string;
  message: string;
}

export interface AutomationLocalValidationResult {
  valid: boolean;
  errors: { field: string; constraint?: string; message: string }[];
}

export interface AutomationContractScenario {
  id: string;
  description: string;
  /** What the user typed. Running it through the manifest's submit mapping must reproduce the request below. */
  formValues?: Record<string, string>;
  integrationState?: Record<string, "connected" | "missing">;
  expectedPrerequisiteOutcome?: {
    behavior: "block" | "continue";
    message: string;
  };
  localValidation?: AutomationLocalValidationResult;
  preflight?: {
    request: { method: "POST"; path: string; body: AutomationRequestBody };
    response: {
      status: number;
      body: { valid: boolean; errors: AutomationPreflightError[] };
    };
  };
  create?: {
    request: { method: "POST"; path: string; body: AutomationRequestBody };
    response: { status: number; body: Record<string, unknown> };
  };
  conversation?: {
    request: { action: "conversation.start"; message: string };
    response: { status: number; body: { conversation_id: string } };
  };
  expectedFieldErrors?: Record<string, string>;
  expectedReviewSummary?: AutomationReviewRow[];
  expectedNavigation?: string;
  /** Present and false when the scenario deliberately shows a request the manifest does not produce. */
  matchesManifestPayload?: boolean;
}

export interface AutomationContractFixtures {
  manifestId: string;
  description: string;
  /** Names a response in AUTOMATION_CAPABILITIES_FIXTURE under which these scenarios hold. */
  capabilities: string;
  /** Capability responses that make this manifest's requirements unsatisfiable. */
  blockedBy: string[];
  scenarios: AutomationContractScenario[];
}

export interface AutomationCapabilitiesFixture {
  description: string;
  endpoint: { method: "GET"; path: string };
  responses: Record<
    string,
    { description: string; status: number; body: Record<string, unknown> }
  >;
}

export const AUTOMATION_CATALOG: RecommendedAutomation[];
export const AUTOMATION_MANIFESTS: AutomationManifest[];
export const AUTOMATION_CAPABILITIES_FIXTURE: AutomationCapabilitiesFixture;
export const AUTOMATION_CONTRACT_FIXTURES: AutomationContractFixtures[];
export default AUTOMATION_CATALOG;
