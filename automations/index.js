/**
 * Runtime automation catalog.
 *
 * The source of truth is the hand-authored `automations/catalog/<id>/manifest.json`
 * directory. `catalog-index.js` is generated from that directory so the JS
 * package can statically import each JSON file without an aggregate JSON asset.
 */
import { AUTOMATION_CATALOG_ENTRIES } from "./catalog-index.js";
import interfaceManifest from "./interface.json" with { type: "json" };

const clone = (value) => JSON.parse(JSON.stringify(value));
const AUTOMATIONS = AUTOMATION_CATALOG_ENTRIES;
const AUTOMATION_BY_ID = new Map(AUTOMATIONS.map((entry) => [entry.id, entry]));

export const listAutomationCatalog = () => clone(AUTOMATIONS);

export const getAutomationCatalogEntry = (id) => {
  const entry = AUTOMATION_BY_ID.get(id);
  return entry ? clone(entry) : undefined;
};

export const AUTOMATION_CATALOG = clone(AUTOMATIONS);

/**
 * The production Automation interface manifest: the domain-level facts of the
 * interface, hand-authored in `automations/interface.json`.
 */
export const AUTOMATION_INTERFACE = clone(interfaceManifest);

export default AUTOMATION_CATALOG;
