package main

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func writeJSON(t *testing.T, path string, value any) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		t.Fatal(err)
	}
	raw, err := json.Marshal(value)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, raw, 0o600); err != nil {
		t.Fatal(err)
	}
}

func event(id, timestamp, source, text string) map[string]any {
	return map[string]any{
		"id": id, "timestamp": timestamp, "source": source, "kind": "MessageEvent",
		"llm_message": map[string]any{"role": source, "content": []any{map[string]any{"type": "text", "text": text}}},
	}
}

func seedConversation(t *testing.T, root, id, title string) string {
	t.Helper()
	conversation := filepath.Join(root, id)
	writeJSON(t, filepath.Join(conversation, "meta.json"), map[string]any{
		"id": id, "title": title, "created_at": "2026-09-01T10:00:00Z", "updated_at": "2026-09-02T10:00:00Z",
		"initial_message": map[string]any{"role": "user", "content": []any{map[string]any{"type": "text", "text": "initial local question"}}},
	})
	writeJSON(t, filepath.Join(conversation, "events", "event-00001-event-a.json"), event("event-a", "2026-09-01T10:01:00Z", "user", "alpha canvas search phrase"))
	writeJSON(t, filepath.Join(conversation, "events", "event-00002-event-b.json"), map[string]any{
		"id": "event-b", "timestamp": "2026-09-01T10:02:00Z", "source": "agent", "kind": "ActionEvent", "tool_name": "terminal", "summary": "Inspect repository status",
		"reasoning_content": "private reasoning must never be indexed", "action": map[string]any{"kind": "TerminalAction", "command": "git status --short"},
	})
	return conversation
}

func locationByLayout(locations []DataLocation, layout string) DataLocation {
	for _, location := range locations {
		if location.Layout == layout {
			return location
		}
	}
	return DataLocation{}
}

func TestDiscoveryHandlesMissingEmptyAndDualLayouts(t *testing.T) {
	home := t.TempDir()
	locations := discoverLocations(home)
	if state := locationByLayout(locations, "sdk-dev").State; state != "missing" {
		t.Fatalf("missing dev layout: %s", state)
	}
	if err := os.MkdirAll(filepath.Join(home, ".openhands", "dev_conversations"), 0o700); err != nil {
		t.Fatal(err)
	}
	locations = discoverLocations(home)
	if state := locationByLayout(locations, "sdk-dev").State; state != "empty" {
		t.Fatalf("empty dev layout: %s", state)
	}
	seedConversation(t, filepath.Join(home, ".openhands", "dev_conversations"), "dev-id", "Dev title")
	seedConversation(t, filepath.Join(home, ".openhands", "conversations"), "standard-id", "Standard title")
	locations = discoverLocations(home)
	if locationByLayout(locations, "sdk-dev").State != "ready" || locationByLayout(locations, "sdk-standard").State != "ready" {
		t.Fatalf("dual layouts not ready: %#v", locations)
	}
	external := t.TempDir()
	linkedParent := filepath.Join(home, ".openhands", "linked")
	if err := os.MkdirAll(linkedParent, 0o700); err != nil {
		t.Fatal(err)
	}
	linkedCandidate := filepath.Join(linkedParent, "dev_conversations")
	if err := os.Symlink(external, linkedCandidate); err == nil {
		locations = discoverLocations(home)
		foundUnsupported := false
		for _, location := range locations {
			if location.Path == linkedCandidate && location.State == "unsupported" {
				foundUnsupported = true
			}
		}
		if !foundUnsupported {
			t.Fatal("symlinked discovery candidate was not rejected")
		}
	}
}

func TestObservedSDKParserIndexesSafeSelectedFields(t *testing.T) {
	home := t.TempDir()
	conversation := seedConversation(t, filepath.Join(home, ".openhands", "dev_conversations"), "conv-id", "Native search")
	raw, err := os.ReadFile(filepath.Join(conversation, "events", "event-00002-event-b.json"))
	if err != nil {
		t.Fatal(err)
	}
	_, document, err := parseDocument(filepath.Join(conversation, "events", "event-00002-event-b.json"), raw)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(document.Text, "git status") || !strings.Contains(document.Text, "Inspect repository") {
		t.Fatalf("expected safe action fields: %#v", document)
	}
	if strings.Contains(document.Text, "private reasoning") {
		t.Fatal("reasoning content leaked into index")
	}
}

func TestAppDataRootRejectsSymlinkEscape(t *testing.T) {
	home := t.TempDir()
	apps := filepath.Join(home, ".openhands", "apps")
	if err := os.MkdirAll(apps, 0o700); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(t.TempDir(), filepath.Join(apps, "conversation-search-sidecar")); err != nil {
		t.Fatal(err)
	}
	if _, err := rootFor(home); err == nil || !strings.Contains(err.Error(), "symbolic link") {
		t.Fatalf("expected symlink rejection, got %v", err)
	}
	childHome := t.TempDir()
	childRoot := filepath.Join(childHome, ".openhands", "apps", "conversation-search-sidecar")
	if err := os.MkdirAll(childRoot, 0o700); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(t.TempDir(), filepath.Join(childRoot, "index")); err != nil {
		t.Fatal(err)
	}
	if _, err := rootFor(childHome); err == nil || !strings.Contains(err.Error(), "index is a symbolic link") {
		t.Fatalf("expected App child symlink rejection, got %v", err)
	}
}

func TestConversationDiscoveryDoesNotFollowNestedSymlinks(t *testing.T) {
	home := t.TempDir()
	root := filepath.Join(home, ".openhands", "dev_conversations")
	conversation := filepath.Join(root, "linked-conversation")
	if err := os.MkdirAll(conversation, 0o700); err != nil {
		t.Fatal(err)
	}
	external := t.TempDir()
	writeJSON(t, filepath.Join(external, "meta.json"), map[string]any{"id": "outside", "title": "must not leak"})
	writeJSON(t, filepath.Join(external, "events", "event-00001-outside.json"), event("outside", "2026-09-01T10:01:00Z", "user", "outside secret"))
	if err := os.Symlink(filepath.Join(external, "meta.json"), filepath.Join(conversation, "meta.json")); err != nil {
		t.Fatal(err)
	}
	if err := os.Symlink(filepath.Join(external, "events"), filepath.Join(conversation, "events")); err != nil {
		t.Fatal(err)
	}
	locations := discoverLocations(home)
	dev := locationByLayout(locations, "sdk-dev")
	if dev.State != "ready" || dev.Conversations != 1 || dev.Files != 0 {
		t.Fatalf("nested links were counted as source files: %#v", dev)
	}
	if files := sourceFiles(locations); len(files) != 0 {
		t.Fatalf("nested links escaped source discovery: %#v", files)
	}
}

func TestIncrementalIndexRankingFiltersMalformedAndDeletion(t *testing.T) {
	home := t.TempDir()
	devRoot := filepath.Join(home, ".openhands", "dev_conversations")
	standardRoot := filepath.Join(home, ".openhands", "conversations")
	first := seedConversation(t, devRoot, "conv-a", "Canvas Alpha")
	seedConversation(t, standardRoot, "conv-b", "Other topic")
	malformed := filepath.Join(first, "events", "event-00003-bad.json")
	if err := os.WriteFile(malformed, []byte("{not-json"), 0o600); err != nil {
		t.Fatal(err)
	}
	status, err := syncIndex(home, false)
	if err != nil {
		t.Fatal(err)
	}
	if status.Documents != 6 || status.MalformedFiles != 1 || status.Conversations != 2 {
		t.Fatalf("unexpected status: %#v", status)
	}
	result, err := searchIndex(home, Request{Query: "alpha", Filters: SearchFilters{Role: "user"}, Limit: 10})
	if err != nil {
		t.Fatal(err)
	}
	if result.Total != 2 || len(result.Hits) == 0 || result.Hits[0].Role != "user" {
		t.Fatalf("unexpected ranked results: %#v", result)
	}
	stableID := result.Hits[0].ID
	filtered, err := searchIndex(home, Request{Query: "repository status", Filters: SearchFilters{Kind: "ActionEvent", Tool: "terminal", Before: "2026-09-02"}, Limit: 10})
	if err != nil || filtered.Total != 2 {
		t.Fatalf("kind/tool/date filters failed: %#v %v", filtered, err)
	}
	after, err := searchIndex(home, Request{Query: "alpha", Filters: SearchFilters{After: "2026-09-03"}, Limit: 10})
	if err != nil || after.Total != 0 {
		t.Fatalf("after filter failed: %#v %v", after, err)
	}
	unchanged, err := syncIndex(home, false)
	if err != nil {
		t.Fatal(err)
	}
	if unchanged.Skipped != 7 || unchanged.Added != 0 || unchanged.Updated != 0 {
		t.Fatalf("not incremental: %#v", unchanged)
	}
	metaPath := filepath.Join(first, "meta.json")
	metaInfo, err := os.Stat(metaPath)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.Chtimes(metaPath, metaInfo.ModTime().Add(time.Second), metaInfo.ModTime().Add(time.Second)); err != nil {
		t.Fatal(err)
	}
	hashFallback, err := syncIndex(home, false)
	if err != nil || hashFallback.Skipped != 7 || hashFallback.Updated != 0 {
		t.Fatalf("content-hash fallback failed: %#v %v", hashFallback, err)
	}
	eventPath := filepath.Join(first, "events", "event-00001-event-a.json")
	writeJSON(t, eventPath, event("event-a", "2026-09-03T10:01:00Z", "user", "replacement delta phrase"))
	writeJSON(t, metaPath, map[string]any{"id": "conv-a", "title": "Retitled conversation", "created_at": "2026-09-01T10:00:00Z", "updated_at": "2026-09-03T10:00:00Z"})
	if err := os.Remove(filepath.Join(first, "events", "event-00002-event-b.json")); err != nil {
		t.Fatal(err)
	}
	changed, err := syncIndex(home, false)
	if err != nil {
		t.Fatal(err)
	}
	if changed.Updated < 1 || changed.Removed != 1 {
		t.Fatalf("update/delete not tracked: %#v", changed)
	}
	old, _ := searchIndex(home, Request{Query: "repository status", Limit: 10})
	for _, hit := range old.Hits {
		if strings.HasPrefix(hit.SourcePath, first) {
			t.Fatalf("deleted source still indexed: %#v", hit)
		}
	}
	replacement, _ := searchIndex(home, Request{Query: "replacement delta", Limit: 10})
	if replacement.Total != 1 {
		t.Fatalf("changed content missing: %#v", replacement)
	}
	if replacement.Hits[0].ID != stableID {
		t.Fatalf("stable event identity changed: %s != %s", replacement.Hits[0].ID, stableID)
	}
	if replacement.Hits[0].Title != "Retitled conversation" {
		t.Fatalf("metadata change did not refresh event title: %#v", replacement.Hits[0])
	}
}

func TestRepairRecoversCorruptIndex(t *testing.T) {
	home := t.TempDir()
	seedConversation(t, filepath.Join(home, ".openhands", "dev_conversations"), "conv", "Repair")
	if _, err := syncIndex(home, false); err != nil {
		t.Fatal(err)
	}
	_, indexPath, _, _ := appPaths(home)
	if err := os.RemoveAll(indexPath); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(indexPath, 0o700); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(indexPath, "corrupt"), []byte("broken"), 0o600); err != nil {
		t.Fatal(err)
	}
	if _, err := searchIndex(home, Request{Query: "alpha"}); err == nil {
		t.Fatal("corrupt index should fail")
	}
	status, err := syncIndex(home, true)
	if err != nil {
		t.Fatal(err)
	}
	if !status.Ready || status.Documents != 3 {
		t.Fatalf("repair failed: %#v", status)
	}
}

func TestDaemonBridgeHealthSearchStopAndIdleCleanup(t *testing.T) {
	home := t.TempDir()
	seedConversation(t, filepath.Join(home, ".openhands", "dev_conversations"), "conv", "Daemon")
	done := make(chan error, 1)
	go func() { done <- serveWithIdle(home, 30*time.Second) }()
	deadline := time.Now().Add(3 * time.Second)
	for time.Now().Before(deadline) {
		if _, err := loadDaemonState(home); err == nil {
			break
		}
		select {
		case err := <-done:
			t.Fatalf("daemon exited during startup: %v", err)
		default:
		}
		time.Sleep(20 * time.Millisecond)
	}
	if status := readServiceStatus(home, "command"); !status.Running {
		t.Fatalf("daemon not healthy: %#v", status)
	}
	if _, err := callDaemon(home, Request{Action: "index"}); err != nil {
		t.Fatal(err)
	}
	response, err := callDaemon(home, Request{Action: "search", Query: "alpha"})
	if err != nil || response.Search == nil || response.Search.Total == 0 {
		t.Fatalf("RPC search failed: %#v %v", response, err)
	}
	if _, err := callDaemon(home, Request{Action: "stop"}); err != nil {
		t.Fatal(err)
	}
	select {
	case err := <-done:
		if err != nil {
			t.Fatal(err)
		}
	case <-time.After(3 * time.Second):
		t.Fatal("daemon did not stop")
	}
	if _, err := os.Stat(statePath(home)); !errorsIsNotExist(err) {
		t.Fatalf("daemon state survived stop: %v", err)
	}

	idleHome := t.TempDir()
	idleDone := make(chan error, 1)
	go func() { idleDone <- serveWithIdle(idleHome, 50*time.Millisecond) }()
	select {
	case err := <-idleDone:
		if err != nil {
			t.Fatal(err)
		}
	case <-time.After(7 * time.Second):
		t.Fatal("idle daemon did not clean up")
	}
}

func errorsIsNotExist(err error) bool { return err != nil && os.IsNotExist(err) }
