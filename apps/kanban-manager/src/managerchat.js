/* "Talk to the manager": a conversation the user chats with from the board.

   The standalone SPA gets this from app.py (`manager_chat_skill` and the
   /api/workspaces/<id>/manager-chat endpoints). The extension has no server of
   its own, so the same three steps happen here against the agent server:
   create the conversation pre-loaded with the manager skill, post the user's
   messages to it, and replay the conversation's MessageEvents into the chat
   window.

   The skill differs from app.py's in ONE section — how to read the board. This
   board lives in the JSON store on disk, so the manager reads it with the
   per-workspace `vibectl.py` the automation installs (or the JSON directly);
   the SPA's manager curls the vibe API. Everything else must stay in step. */

import { resolveBackendCredentials } from "./store.js";

/* First line of the pre-loaded skill: the chat window replays the conversation
   from its events, and this is how the seeded prompt is told apart from what
   the user actually typed. Mirrors MANAGER_CHAT_MARKER in app.py. */
export const CHAT_MARKER = "<!-- vibe-manager-skill -->";
export const CHAT_ROLE = "manager_chat";

const MAX_PAGES = 20;

export function managerChatSkill(ws, storeRoot) {
  const push =
    ws.push_mode === "pr"
      ? "pull requests (workers branch and open a PR)"
      : "push to the default branch directly";
  const vibectl = `${storeRoot}/bin/${ws.id}/vibectl.py`;
  return `${CHAT_MARKER}
You are the **Vibe Manager** for the project at \`${ws.path}\` (workspace id \`${ws.id}\`), talking to the user in a chat window on their kanban board. Replies land in a small chat panel: keep them short, plain and conversational.

## What you do here
- Listen to the user: new requests, questions about the board, complaints about how the work is going.
- Write every request down in \`AGENTS.md\` (see below) so it survives this conversation.
- Answer questions about the board and the agents working on it from the LIVE state, never from memory.
- You do NOT write feature code, and you do NOT dispatch workers from this chat. The manager automation polls this board every minute and does the dispatching, with rules about concurrency and conflicting tickets that you cannot see from here. Tell the user what you recorded and let it pick the work up.

## Recording requests in AGENTS.md
1. \`AGENTS.md\` at \`${ws.path}\` is the project's standing memory — read it first.
2. Keep ONE top-level \`## Manager\` section in it (append the section at the end of the file if it isn't there yet, and create the file if it doesn't exist).
3. Under it, one bullet per request the user makes: today's date (take it from \`date -I\`, don't guess), the request in the user's own words (one or two lines), and what you did about it. Update the existing bullet when the user refines a request instead of adding a second one.
4. Write the bullet as soon as the request is made, before you write a long answer.
5. Leave the checkout clean: \`git add AGENTS.md && git commit -m "Manager: <short>"\` after editing, and push it (this workspace lands work via ${push}). Never touch other files, and never commit someone else's work in progress.

## Reading the board
The board is JSON on disk. Read it with the workspace's manager CLI:
- \`python3 ${vibectl} snapshot\` — every ticket with \`status\` (pending/in_progress/needs_input/finished/verified), \`entries\` (the request text, oldest first), \`sort_order\` (the user's priority inside a column, lower first), \`title\`, \`manager_note\`, \`conversation_id\`, \`pr_url\` and \`attachments\`.
- \`python3 ${vibectl} conversation <conversation_id>\` — \`execution_status\` (running|idle|finished|error|stuck|paused) and the model a ticket's worker is on.
If that CLI is missing (the automation installs it on its first run), read the ticket files under \`${storeRoot}/workspaces/${ws.id}/tickets/\` (one \`<ticket_id>/ticket.json\` each) directly — but never write to them by hand.

## Reading the conversations on the board
Every dispatched ticket has a worker conversation on the agent server (\`$AGENT_SERVER_URL\`, session key in \`$SESSION_API_KEY\` where the environment provides them; the CLI above already knows how to reach it). Beyond \`conversation\`:
- \`GET <agent_server>/api/conversations/<conversation_id>/events/search?sort_order=TIMESTAMP_DESC&limit=20\` → the recent events: \`MessageEvent\`s carry the agent's own words in \`llm_message.content[].text\`, \`ActionEvent\`s the commands it ran.

## Right now
Read \`AGENTS.md\` and the board, then greet the user in ONE sentence that says where the board stands (e.g. "3 queued, 1 agent working"). Then wait — answer what they ask, record what they request.`;
}

/** A chat turn from an agent-server event, or null for everything else. */
export function chatMessage(event) {
  if (event?.kind !== "MessageEvent") return null;
  const msg = event.llm_message || {};
  const role = msg.role || (event.source === "user" ? "user" : "assistant");
  if (role !== "user" && role !== "assistant") return null;
  const text = (msg.content || [])
    .filter((c) => c && c.type === "text" && c.text)
    .map((c) => c.text)
    .join("\n")
    .trim();
  // The pre-loaded skill is not something the user said — hide it.
  if (!text || text.startsWith(CHAT_MARKER)) return null;
  return { id: event.id, role, text, timestamp: event.timestamp || null };
}

export class ManagerChat {
  constructor(host, store, live) {
    this.host = host;
    this.store = store;
    // Live owns the ActionEvent summary parsing the cards already use; the
    // chat shows the same line while the manager is off running tools.
    this.live = live;
  }

  /* The settings have to come back with their secrets so the conversation can
     be created server-side, and that needs a header the host client does not
     forward — hence a raw fetch, the same escape hatch manager.js uses. */
  async agentSettings() {
    const creds = resolveBackendCredentials(this.host?.backend?.id);
    if (!creds) throw new Error("no backend credentials available to start a chat");
    const res = await fetch(`${creds.host}/api/settings`, {
      headers: {
        "X-Expose-Secrets": "encrypted",
        ...(creds.apiKey ? { "X-Session-API-Key": creds.apiKey } : {}),
      },
    });
    if (!res.ok) throw new Error(`settings unavailable: ${res.status} ${res.statusText}`);
    const settings = (await res.json())?.agent_settings;
    if (!settings) throw new Error("agent server returned no agent settings");
    // The stored [] means "bare agent"; null resolves the default exec toolset.
    settings.tools = null;
    return settings;
  }

  /** Start a chat conversation for this workspace; returns its id. */
  async start(ws) {
    const skill = managerChatSkill(ws, await this.store.storeRoot());
    const created = await this.host.agentServer.request({
      method: "POST",
      path: "/api/conversations",
      body: {
        // The dedicated workspace option keeps the conversation attached to
        // the PROJECT directory, which is where AGENTS.md lives.
        workspace: { kind: "LocalWorkspace", working_dir: ws.path },
        worktree: false,
        agent_settings: await this.agentSettings(),
        secrets_encrypted: true,
        initial_message: { role: "user", content: [{ text: skill }], run: true },
        max_iterations: 200,
        autotitle: false,
        tags: { workspace: ws.path, viberole: CHAT_ROLE },
      },
    });
    const id = created?.id;
    if (!id) throw new Error("agent server returned no conversation id");
    await this.host.agentServer.request({
      method: "PATCH",
      path: `/api/conversations/${id}`,
      body: { title: `💬 Manager chat — ${ws.name}` },
    });
    return id;
  }

  async send(convId, text) {
    await this.host.agentServer.request({
      method: "POST",
      path: `/api/conversations/${convId}/events`,
      body: { role: "user", content: [{ text }], run: true },
    });
  }

  /* Turns since `after`, which is the cursor from the previous poll: the
     newest EVENT seen, not the newest message, so a manager busy running tools
     doesn't get its whole event log re-read every couple of seconds. */
  async messages(convId, after = null) {
    const messages = [];
    let cursor = after;
    let latestAction = null;
    let pageId = null;
    for (let page = 0; page < MAX_PAGES; page += 1) {
      const query = new URLSearchParams({ sort_order: "TIMESTAMP", limit: "100" });
      if (after) query.set("timestamp__gte", after);
      if (pageId) query.set("page_id", pageId);
      const res = await this.host.agentServer.request({
        path: `/api/conversations/${convId}/events/search?${query}`,
      });
      for (const event of res?.items || []) {
        const ts = event?.timestamp;
        if (ts && (cursor === null || ts > cursor)) cursor = ts;
        // timestamp__gte is inclusive; `after` is not.
        if (after && ts && ts <= after) continue;
        const msg = chatMessage(event);
        if (msg) messages.push(msg);
        const action = this.live?.extractActionSummary(event);
        if (action) latestAction = action;
      }
      pageId = res?.next_page_id;
      if (!pageId) break;
    }
    return { messages, cursor, latestAction };
  }
}
