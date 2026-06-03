import { createElement } from "react";
import {
  BookOpen,
  Bot,
  Brain,
  Clock,
  Database,
  Flame,
  Folder,
  GitBranch,
  Globe,
  ListTree,
  MousePointerClick,
  Search,
  Sparkles,
  Telescope,
  TestTube,
} from "lucide-react";
import {
  SiAirtable,
  SiAtlassian,
  SiBrave,
  SiClickhouse,
  SiCloudflare,
  SiElevenlabs,
  SiFigma,
  SiGithub,
  SiHuggingface,
  SiKagi,
  SiLinear,
  SiMongodb,
  SiNotion,
  SiObsidian,
  SiPaypal,
  SiRedis,
  SiResend,
  SiSentry,
  SiSlack,
  SiStripe,
  SiSupabase,
} from "react-icons/si";

const LOGO = "h-5 w-5";

const simpleIcon = (Icon) => createElement(Icon, { className: LOGO });
const lucideIcon = (Icon) =>
  createElement(Icon, { className: LOGO, strokeWidth: 2.25 });

export const INTEGRATION_FALLBACK_LOGO = lucideIcon(Bot);

export const INTEGRATION_LOGOS = {
  github: simpleIcon(SiGithub),
  slack: simpleIcon(SiSlack),
  tavily: createElement(Search, { className: LOGO, strokeWidth: 2.5 }),
  linear: simpleIcon(SiLinear),
  notion: simpleIcon(SiNotion),
  atlassian: simpleIcon(SiAtlassian),
  sentry: simpleIcon(SiSentry),
  stripe: simpleIcon(SiStripe),
  paypal: simpleIcon(SiPaypal),
  "cloudflare-docs": simpleIcon(SiCloudflare),
  "cloudflare-bindings": simpleIcon(SiCloudflare),
  "cloudflare-observability": simpleIcon(SiCloudflare),
  huggingface: simpleIcon(SiHuggingface),
  deepwiki: simpleIcon(BookOpen),
  git: lucideIcon(GitBranch),
  "brave-search": simpleIcon(SiBrave),
  exa: lucideIcon(Telescope),
  firecrawl: lucideIcon(Flame),
  apify: lucideIcon(Bot),
  fetch: lucideIcon(Globe),
  "browser-mcp": lucideIcon(MousePointerClick),
  playwright: lucideIcon(TestTube),
  supabase: simpleIcon(SiSupabase),
  neon: lucideIcon(Database),
  mongodb: simpleIcon(SiMongodb),
  redis: simpleIcon(SiRedis),
  filesystem: lucideIcon(Folder),
  memory: lucideIcon(Brain),
  "sequential-thinking": lucideIcon(ListTree),
  time: lucideIcon(Clock),
  everything: lucideIcon(Sparkles),
  figma: simpleIcon(SiFigma),
  airtable: simpleIcon(SiAirtable),
  obsidian: simpleIcon(SiObsidian),
  elevenlabs: simpleIcon(SiElevenlabs),
  resend: simpleIcon(SiResend),
  "cloudflare-builds": simpleIcon(SiCloudflare),
  "cloudflare-browser-rendering": simpleIcon(SiCloudflare),
  kagi: simpleIcon(SiKagi),
  clickhouse: simpleIcon(SiClickhouse),
};

export const INTEGRATION_LOGO_IDS = new Set(Object.keys(INTEGRATION_LOGOS));
