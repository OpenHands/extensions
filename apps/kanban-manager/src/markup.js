/* The SPA's static/index.html body, as a template string.

   The extension has no HTML file of its own: Canvas hands us a bare container
   and we fill it. Keeping this as one template (rather than hand-built DOM)
   makes it easy to diff against static/index.html when that changes.

   Two controls are extension-only and have no counterpart in index.html: the
   #api-setup screen (the SPA is served by the API it talks to, so it never has
   to explain that the backend is missing) and the #mgr-stop segment of the
   manager group (the SPA's manager automation is created and owned by app.py,
   not by the browser). */

export const BOARD_MARKUP = `
<header class="topbar">
  <div class="topbar-controls">
    <div class="control control-workspace">
      <div id="workspace-indicators" class="workspace-indicators" aria-label="Projects with unfinished cards"></div>
      <select id="workspace-select" aria-label="Workspace"><option value="">Choose a workspace</option></select>
    </div>
    <div class="control control-accent" id="ctl-accent" hidden>
      <button type="button" id="accent-toggle" class="ghost-btn accent-btn"
              aria-haspopup="true" aria-expanded="false" aria-label="Primary colour">
        <span class="accent-dot" aria-hidden="true"></span>
      </button>
      <div class="accent-menu" id="accent-menu" role="menu" aria-label="Primary colour" hidden></div>
    </div>
    <div class="control" id="ctl-concurrency" hidden>
      <label class="control-label" for="max-concurrent">Max agents</label>
      <input id="max-concurrent" type="number" min="1" max="20" value="3">
    </div>
    <button id="manager-chat-open" class="ghost-btn talk-btn" hidden
            title="Chat with the manager about this board">Talk to the manager</button>
    <div class="control control-settings" id="ctl-settings" hidden>
      <button type="button" id="settings-toggle" class="ghost-btn settings-btn"
              aria-haspopup="true" aria-expanded="false"
              title="Workspace settings: agent, budget, where changes land"
              aria-label="Workspace settings"><span aria-hidden="true">⚙</span></button>
      <div class="settings-menu" id="settings-menu" role="group" aria-label="Workspace settings" hidden>
        <div class="desk-setting">
          <label class="control-label" for="settings-profile">Agent</label>
          <select id="settings-profile">
            <option value="">Manager's choice</option>
          </select>
        </div>
        <div class="desk-setting">
          <label class="control-label" for="settings-budget">Budget ($)</label>
          <input id="settings-budget" type="number" min="1" step="1" value="10">
        </div>
        <div class="desk-setting">
          <span class="control-label">Where changes land</span>
          <div class="seg" id="push-mode" role="group" aria-label="Where changes land">
            <button type="button" data-mode="pr" class="seg-btn">Pull request</button>
            <button type="button" data-mode="main" class="seg-btn">Push to main</button>
          </div>
        </div>
      </div>
    </div>
    <div class="mgr-group" id="mgr-group" hidden role="group" aria-label="Manager automation">
      <div class="mgr-badge" id="mgr-badge" hidden role="button" tabindex="0"
           title="Manager automation is watching this workspace&#10;Click to run the manager now">
        <span class="pulse" id="mgr-dot"></span> <span id="mgr-text">manager</span>
      </div>
      <button type="button" id="mgr-stop" class="mgr-stop" hidden
              title="Disable the manager automation for this workspace">Stop</button>
    </div>
  </div>
</header>

<main id="main">
  <section id="api-setup" hidden>
    <div class="empty-inner">
      <p class="eyebrow">Board unavailable</p>
      <h1>Can't reach the agent server</h1>
      <p class="empty-copy">The board is stored on the agent server this Canvas backend is
         connected to, so it needs to be running.</p>
      <p class="api-setup-error" id="api-setup-error" hidden></p>
      <button type="button" id="api-retry">Retry</button>
    </div>
  </section>

  <section id="empty-state" hidden>
    <div class="empty-inner">
      <div class="empty-lanes" aria-hidden="true">
        <span class="lane-swatch" data-lane="pending"></span>
        <span class="lane-swatch" data-lane="in_progress"></span>
        <span class="lane-swatch" data-lane="needs_input"></span>
        <span class="lane-swatch" data-lane="finished"></span>
      </div>
      <p class="eyebrow">No workspace open</p>
      <h1>Choose a workspace to open its board.</h1>
      <p class="empty-copy">Each workspace gets a manager that checks the queue every minute, hands
         work to agents in their own git worktrees, and moves cards across the board as they go.</p>
    </div>
  </section>

  <section id="board-wrap" hidden>
    <form id="new-ticket-form" class="desk" autocomplete="off">
      <div class="desk-head">
        <span class="eyebrow">New request</span>
      </div>
      <div class="ticket-form-row">
        <textarea id="new-ticket-body" rows="2" aria-label="What should the agents build?"
          placeholder="What should the agents build?"></textarea>
        <div class="desk-actions">
          <input type="file" id="new-ticket-file-input" multiple hidden>
          <button type="button" id="new-ticket-attach" class="attach-btn" title="Attach files or images" aria-label="Attach files or images">
            <span aria-hidden="true">📎</span>
          </button>
          <button type="submit" id="new-ticket-submit">Send request</button>
        </div>
      </div>
      <div id="new-ticket-files" class="file-chips" hidden></div>
    </form>

    <div class="board" id="board">
      <section class="col" data-status="pending" aria-label="Pending">
        <div class="col-head">
          <span class="col-name">Pending</span>
          <span class="col-count"></span>
        </div>
        <div class="col-cards" data-status="pending"></div>
      </section>
      <section class="col" data-status="in_progress" aria-label="In progress">
        <div class="col-head">
          <span class="col-name">In progress</span>
          <span class="col-count"></span>
        </div>
        <div class="col-cards" data-status="in_progress"></div>
      </section>
      <section class="col" data-status="needs_input" aria-label="Needs you">
        <div class="col-head">
          <span class="col-name">Needs you</span>
          <span class="col-count"></span>
        </div>
        <div class="col-cards" data-status="needs_input"></div>
      </section>
      <section class="col" data-status="finished" aria-label="Finished">
        <div class="col-head">
          <span class="col-name">Finished</span>
          <span class="col-count"></span>
          <button type="button" id="show-verified" class="toggle-verified" aria-pressed="false"
                  title="Show verified" aria-label="Show verified">
            <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true" focusable="false">
              <path d="M1.8 12S5.4 5.8 12 5.8 22.2 12 22.2 12 18.6 18.2 12 18.2 1.8 12 1.8 12Z"
                    fill="none" stroke="currentColor" stroke-width="1.8"/>
              <circle cx="12" cy="12" r="3.1" fill="none" stroke="currentColor" stroke-width="1.8"/>
            </svg>
          </button>
        </div>
        <div class="col-cards" data-status="finished"></div>
      </section>
      <section class="col" data-status="verified" aria-label="Verified" hidden>
        <div class="col-head">
          <span class="col-name">Verified</span>
          <span class="col-count"></span>
        </div>
        <div class="col-cards" data-status="verified"></div>
      </section>
    </div>
  </section>
</main>

<aside id="drawer" hidden>
  <div class="drawer-backdrop" id="drawer-backdrop"></div>
  <div class="drawer-panel" role="dialog" aria-modal="true" aria-label="Request detail">
    <div class="drawer-head">
      <div class="drawer-headings">
        <div class="drawer-meta">
          <span class="drawer-status" id="drawer-status"></span>
          <span class="drawer-id" id="drawer-id"></span>
        </div>
        <h2 class="drawer-title" id="drawer-title" hidden></h2>
      </div>
      <button class="drawer-close" id="drawer-close" aria-label="Close">✕</button>
    </div>
    <div class="drawer-links" id="drawer-links"></div>
    <div class="drawer-note" id="drawer-note" hidden></div>
    <div class="drawer-activity" id="drawer-activity" hidden></div>
    <div class="drawer-attachments" id="drawer-attachments" hidden></div>
    <div class="drawer-thread" id="drawer-thread"></div>
    <form id="append-form">
      <textarea id="append-body" rows="3" aria-label="Add to this request"
        placeholder="Add to this request…"></textarea>
      <div class="desk-actions">
        <input type="file" id="drawer-file-input" multiple hidden>
        <button type="button" id="drawer-attach" class="attach-btn" title="Attach files or images" aria-label="Attach files or images">
          <span aria-hidden="true">📎</span>
        </button>
        <button type="submit">Add</button>
      </div>
    </form>
  </div>
</aside>

<aside id="manager-chat" hidden>
  <div class="chat-backdrop" id="manager-chat-backdrop"></div>
  <div class="chat-panel" role="dialog" aria-modal="true" aria-label="Talk to the manager">
    <div class="chat-head">
      <div class="chat-headings">
        <span class="eyebrow">Talk to the manager</span>
        <div class="chat-activity" id="manager-chat-activity"></div>
      </div>
      <a class="chip convo" id="manager-chat-link" hidden>↗ open conversation</a>
      <button class="drawer-close" id="manager-chat-close" aria-label="Close">✕</button>
    </div>
    <div class="chat-log" id="manager-chat-log" aria-live="polite"></div>
    <form id="manager-chat-form">
      <textarea id="manager-chat-body" rows="2" aria-label="Message the manager"
        placeholder="Ask for something, or ask how the board is doing…"></textarea>
      <div class="desk-actions">
        <button type="submit" id="manager-chat-send">Send</button>
      </div>
    </form>
  </div>
</aside>
`;
