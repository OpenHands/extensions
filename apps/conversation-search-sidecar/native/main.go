package main

import (
	"bytes"
	"context"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"runtime"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"

	bleve "github.com/blevesearch/bleve/v2"
	"github.com/blevesearch/bleve/v2/mapping"
	"github.com/blevesearch/bleve/v2/search/query"
)

const (
	version             = "0.1.0"
	protocolPrefix      = "CONVERSATION_SEARCH\t"
	appSubpath          = ".openhands/apps/conversation-search-sidecar"
	idleShutdownSeconds = 600
	maxIndexedTextBytes = 32 * 1024
)

type Request struct {
	Action   string        `json:"action"`
	Query    string        `json:"query,omitempty"`
	Filters  SearchFilters `json:"filters,omitempty"`
	Limit    int           `json:"limit,omitempty"`
	Document string        `json:"documentId,omitempty"`
}

type SearchFilters struct {
	Role   string `json:"role,omitempty"`
	Kind   string `json:"kind,omitempty"`
	Tool   string `json:"tool,omitempty"`
	After  string `json:"after,omitempty"`
	Before string `json:"before,omitempty"`
}

type Envelope struct {
	OK    bool      `json:"ok"`
	Data  *Response `json:"data,omitempty"`
	Error string    `json:"error,omitempty"`
}

type Response struct {
	Status  *IndexStatus    `json:"status,omitempty"`
	Search  *SearchResponse `json:"search,omitempty"`
	Hit     *SearchHit      `json:"hit,omitempty"`
	Message string          `json:"message,omitempty"`
}

type DataLocation struct {
	Path          string `json:"path"`
	Layout        string `json:"layout"`
	State         string `json:"state"`
	Conversations int    `json:"conversations"`
	Files         int    `json:"files"`
	Malformed     int    `json:"malformed"`
	Message       string `json:"message,omitempty"`
}

type ServiceStatus struct {
	Running             bool   `json:"running"`
	Mode                string `json:"mode"`
	Version             string `json:"version"`
	PID                 int    `json:"pid,omitempty"`
	StartedAt           string `json:"startedAt,omitempty"`
	LastActivity        string `json:"lastActivity,omitempty"`
	IdleSeconds         int    `json:"idleSeconds,omitempty"`
	IdleShutdownSeconds int    `json:"idleShutdownSeconds"`
}

type IndexStatus struct {
	Ready          bool           `json:"ready"`
	Documents      uint64         `json:"documents"`
	SourceFiles    int            `json:"sourceFiles"`
	Conversations  int            `json:"conversations"`
	MalformedFiles int            `json:"malformedFiles"`
	IndexBytes     int64          `json:"indexBytes"`
	LastIndexedAt  string         `json:"lastIndexedAt,omitempty"`
	Locations      []DataLocation `json:"locations"`
	Service        ServiceStatus  `json:"service"`
	Added          int            `json:"added,omitempty"`
	Updated        int            `json:"updated,omitempty"`
	Removed        int            `json:"removed,omitempty"`
	Skipped        int            `json:"skipped,omitempty"`
}

type SearchHit struct {
	ID             string  `json:"id"`
	Score          float64 `json:"score"`
	ConversationID string  `json:"conversationId"`
	EventID        string  `json:"eventId"`
	Title          string  `json:"title"`
	Timestamp      string  `json:"timestamp"`
	Role           string  `json:"role"`
	Kind           string  `json:"kind"`
	Tool           string  `json:"tool"`
	SourcePath     string  `json:"sourcePath"`
	Excerpt        string  `json:"excerpt"`
	Text           string  `json:"text,omitempty"`
	Summary        string  `json:"summary,omitempty"`
}

type SearchResponse struct {
	Total      uint64      `json:"total"`
	DurationMS float64     `json:"durationMs"`
	Hits       []SearchHit `json:"hits"`
	Status     IndexStatus `json:"status"`
}

type FileState struct {
	Size      int64    `json:"size"`
	ModUnixNS int64    `json:"modUnixNs"`
	SHA256    string   `json:"sha256"`
	DocIDs    []string `json:"docIds"`
	Malformed bool     `json:"malformed,omitempty"`
	ConvID    string   `json:"conversationId"`
}

type Manifest struct {
	Version       int                  `json:"version"`
	Files         map[string]FileState `json:"files"`
	LastIndexedAt string               `json:"lastIndexedAt"`
}

type IndexDocument struct {
	ConversationID string    `json:"conversationId"`
	EventID        string    `json:"eventId"`
	Title          string    `json:"title"`
	Timestamp      time.Time `json:"timestamp"`
	Role           string    `json:"role"`
	Kind           string    `json:"kind"`
	Tool           string    `json:"tool"`
	SourcePath     string    `json:"sourcePath"`
	Text           string    `json:"text"`
	Summary        string    `json:"summary"`
}

type candidate struct {
	path   string
	layout string
}

type daemonState struct {
	PID          int    `json:"pid"`
	Port         int    `json:"port"`
	Token        string `json:"token"`
	Version      string `json:"version"`
	StartedAt    string `json:"startedAt"`
	LastActivity string `json:"lastActivity"`
}

func rootFor(home string) (string, error) {
	home, err := filepath.Abs(home)
	if err != nil {
		return "", err
	}
	root := filepath.Clean(filepath.Join(home, appSubpath))
	prefix := filepath.Clean(home) + string(os.PathSeparator)
	if !strings.HasPrefix(root+string(os.PathSeparator), prefix) {
		return "", errors.New("App data path escaped the Agent Server home")
	}
	if pathContainsSymlink(home, root) {
		return "", errors.New("App data path contains a symbolic link")
	}
	for _, child := range []string{"bin", "build", "index", "logs", "run"} {
		if info, statErr := os.Lstat(filepath.Join(root, child)); statErr == nil && info.Mode()&os.ModeSymlink != 0 {
			return "", fmt.Errorf("App data subdirectory %s is a symbolic link", child)
		}
	}
	return root, nil
}

func pathContainsSymlink(base, target string) bool {
	relative, err := filepath.Rel(filepath.Clean(base), filepath.Clean(target))
	if err != nil || relative == ".." || strings.HasPrefix(relative, ".."+string(os.PathSeparator)) {
		return true
	}
	current := filepath.Clean(base)
	for _, part := range strings.Split(relative, string(os.PathSeparator)) {
		if part == "" || part == "." {
			continue
		}
		current = filepath.Join(current, part)
		if info, statErr := os.Lstat(current); statErr == nil && info.Mode()&os.ModeSymlink != 0 {
			return true
		}
	}
	return false
}

func uniqueCandidates(home string) []candidate {
	base := filepath.Join(home, ".openhands")
	items := []candidate{
		{filepath.Join(base, "dev_conversations"), "sdk-dev"},
		{filepath.Join(base, "conversations"), "sdk-standard"},
	}
	// Agent Server deployments can override OPENHANDS_PERSISTENCE_DIR. The
	// active Canvas environment uses .openhands/agent-canvas/dev_conversations.
	if matches, _ := filepath.Glob(filepath.Join(base, "*", "dev_conversations")); len(matches) > 0 {
		for _, match := range matches {
			items = append(items, candidate{match, "sdk-discovered"})
		}
	}
	// Some Agent Server home endpoints already point at a persistence root.
	items = append(items, candidate{filepath.Join(home, "dev_conversations"), "sdk-home-root"})
	seen := map[string]bool{}
	result := make([]candidate, 0, len(items))
	for _, item := range items {
		clean := filepath.Clean(item.path)
		if seen[clean] {
			continue
		}
		seen[clean] = true
		result = append(result, candidate{clean, item.layout})
	}
	return result
}

func discoverLocations(home string) []DataLocation {
	locations := make([]DataLocation, 0)
	for _, item := range uniqueCandidates(home) {
		location := DataLocation{Path: item.path, Layout: item.layout, State: "missing"}
		info, err := os.Lstat(item.path)
		if errors.Is(err, os.ErrNotExist) {
			locations = append(locations, location)
			continue
		}
		if err != nil {
			location.State, location.Message = "unreadable", err.Error()
			locations = append(locations, location)
			continue
		}
		if info.Mode()&os.ModeSymlink != 0 || !info.IsDir() {
			location.State, location.Message = "unsupported", "candidate is not a real directory"
			locations = append(locations, location)
			continue
		}
		if pathContainsSymlink(home, item.path) {
			location.State, location.Message = "unsupported", "candidate path contains a symbolic link"
			locations = append(locations, location)
			continue
		}
		entries, err := os.ReadDir(item.path)
		if err != nil {
			location.State, location.Message = "unreadable", err.Error()
			locations = append(locations, location)
			continue
		}
		location.State = "empty"
		for _, entry := range entries {
			if entry.Type()&os.ModeSymlink != 0 || !entry.IsDir() {
				continue
			}
			location.Conversations++
			convPath := filepath.Join(item.path, entry.Name())
			if metaInfo, err := os.Lstat(filepath.Join(convPath, "meta.json")); err == nil && metaInfo.Mode().IsRegular() {
				location.Files++
			}
			eventsPath := filepath.Join(convPath, "events")
			eventsInfo, err := os.Lstat(eventsPath)
			if err != nil || eventsInfo.Mode()&os.ModeSymlink != 0 || !eventsInfo.IsDir() {
				continue
			}
			events, err := os.ReadDir(eventsPath)
			if err == nil {
				for _, event := range events {
					if event.Type()&os.ModeSymlink == 0 && !event.IsDir() && strings.HasPrefix(event.Name(), "event-") && strings.HasSuffix(event.Name(), ".json") {
						location.Files++
					}
				}
			}
		}
		if location.Conversations > 0 {
			location.State = "ready"
		}
		locations = append(locations, location)
	}
	return locations
}

func sourceFiles(locations []DataLocation) []string {
	var files []string
	for _, location := range locations {
		if location.State != "ready" {
			continue
		}
		conversations, err := os.ReadDir(location.Path)
		if err != nil {
			continue
		}
		for _, conversation := range conversations {
			if conversation.Type()&os.ModeSymlink != 0 || !conversation.IsDir() {
				continue
			}
			convPath := filepath.Join(location.Path, conversation.Name())
			meta := filepath.Join(convPath, "meta.json")
			if info, err := os.Lstat(meta); err == nil && info.Mode().IsRegular() {
				files = append(files, meta)
			}
			eventsPath := filepath.Join(convPath, "events")
			eventsInfo, err := os.Lstat(eventsPath)
			if err != nil || eventsInfo.Mode()&os.ModeSymlink != 0 || !eventsInfo.IsDir() {
				continue
			}
			events, err := os.ReadDir(eventsPath)
			if err != nil {
				continue
			}
			for _, event := range events {
				if event.Type()&os.ModeSymlink != 0 || event.IsDir() || !strings.HasPrefix(event.Name(), "event-") || !strings.HasSuffix(event.Name(), ".json") {
					continue
				}
				files = append(files, filepath.Join(convPath, "events", event.Name()))
			}
		}
	}
	sort.Strings(files)
	return files
}

func appPaths(home string) (root, indexPath, manifestPath string, err error) {
	root, err = rootFor(home)
	if err != nil {
		return "", "", "", err
	}
	return root, filepath.Join(root, "index", "bleve"), filepath.Join(root, "index", "sources.json"), nil
}

func loadManifest(path string) Manifest {
	manifest := Manifest{Version: 1, Files: map[string]FileState{}}
	raw, err := os.ReadFile(path)
	if err == nil && json.Unmarshal(raw, &manifest) == nil && manifest.Files != nil {
		return manifest
	}
	return Manifest{Version: 1, Files: map[string]FileState{}}
}

func saveManifest(path string, manifest Manifest) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return err
	}
	raw, err := json.MarshalIndent(manifest, "", "  ")
	if err != nil {
		return err
	}
	temporary := path + ".tmp"
	if err := os.WriteFile(temporary, raw, 0o600); err != nil {
		return err
	}
	return os.Rename(temporary, path)
}

func newIndexMapping() *mapping.IndexMappingImpl {
	mapping := bleve.NewIndexMapping()
	text := bleve.NewTextFieldMapping()
	text.Store = true
	text.IncludeTermVectors = true
	keyword := bleve.NewTextFieldMapping()
	keyword.Store = true
	keyword.Analyzer = "keyword"
	date := bleve.NewDateTimeFieldMapping()
	date.Store = true
	for _, field := range []string{"text", "title", "summary"} {
		mapping.DefaultMapping.AddFieldMappingsAt(field, text)
	}
	for _, field := range []string{"conversationId", "eventId", "role", "kind", "tool", "sourcePath"} {
		mapping.DefaultMapping.AddFieldMappingsAt(field, keyword)
	}
	mapping.DefaultMapping.AddFieldMappingsAt("timestamp", date)
	return mapping
}

func openIndex(path string) (bleve.Index, error) {
	index, err := bleve.Open(path)
	if err == nil {
		return index, nil
	}
	if !errors.Is(err, os.ErrNotExist) && !strings.Contains(strings.ToLower(err.Error()), "does not exist") {
		return nil, err
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return nil, err
	}
	return bleve.New(path, newIndexMapping())
}

func hashBytes(raw []byte) string {
	digest := sha256.Sum256(raw)
	return hex.EncodeToString(digest[:])
}

func scalarString(value any) string {
	if text, ok := value.(string); ok {
		return text
	}
	return ""
}

func nested(object map[string]any, name string) map[string]any {
	value, _ := object[name].(map[string]any)
	return value
}

func collectContent(value any, destination *[]string) {
	switch item := value.(type) {
	case string:
		if strings.TrimSpace(item) != "" {
			*destination = append(*destination, item)
		}
	case []any:
		for _, child := range item {
			if object, ok := child.(map[string]any); ok {
				collectContent(object["text"], destination)
			}
		}
	}
}

func trimIndexed(value string) string {
	value = strings.TrimSpace(value)
	if len(value) > maxIndexedTextBytes {
		value = value[:maxIndexedTextBytes] + "\n[truncated for local index]"
	}
	return value
}

func conversationInfo(metaPath, fallback string) (title string, timestamp time.Time) {
	title = fallback
	info, err := os.Lstat(metaPath)
	if err != nil || !info.Mode().IsRegular() {
		return title, time.Time{}
	}
	raw, err := os.ReadFile(metaPath)
	if err != nil {
		return title, time.Time{}
	}
	var meta map[string]any
	if json.Unmarshal(raw, &meta) != nil {
		return title, time.Time{}
	}
	if candidate := scalarString(meta["title"]); candidate != "" {
		title = candidate
	}
	for _, field := range []string{"updated_at", "created_at"} {
		if parsed, err := time.Parse(time.RFC3339Nano, scalarString(meta[field])); err == nil {
			return title, parsed
		}
	}
	return title, time.Time{}
}

func parseDocument(path string, raw []byte) (string, IndexDocument, error) {
	convPath := filepath.Dir(path)
	if filepath.Base(convPath) == "events" {
		convPath = filepath.Dir(convPath)
	}
	convID := filepath.Base(convPath)
	title, metaTime := conversationInfo(filepath.Join(convPath, "meta.json"), convID)
	var object map[string]any
	if err := json.Unmarshal(raw, &object); err != nil {
		return convID, IndexDocument{}, err
	}
	if filepath.Base(path) == "meta.json" {
		parts := []string{}
		if message := nested(object, "initial_message"); message != nil {
			collectContent(message["content"], &parts)
		}
		doc := IndexDocument{ConversationID: convID, EventID: "meta", Title: title, Timestamp: metaTime, Role: "conversation", Kind: "ConversationMetadata", SourcePath: path, Text: trimIndexed(strings.Join(parts, "\n"))}
		return convID, doc, nil
	}
	eventID := scalarString(object["id"])
	if eventID == "" {
		return convID, IndexDocument{}, errors.New("event has no stable id")
	}
	timestamp := time.Time{}
	if parsed, err := time.Parse(time.RFC3339Nano, scalarString(object["timestamp"])); err == nil {
		timestamp = parsed
	}
	kind := scalarString(object["kind"])
	role := scalarString(object["source"])
	tool := scalarString(object["tool_name"])
	summary := scalarString(object["summary"])
	parts := []string{}
	if message := nested(object, "llm_message"); message != nil {
		if messageRole := scalarString(message["role"]); messageRole != "" {
			role = messageRole
		}
		collectContent(message["content"], &parts)
	}
	collectContent(object["extended_content"], &parts)
	if action := nested(object, "action"); action != nil {
		collectContent(action["message"], &parts)
		collectContent(action["command"], &parts)
	}
	if observation := nested(object, "observation"); observation != nil {
		collectContent(observation["content"], &parts)
		if tool == "" {
			tool = scalarString(observation["kind"])
		}
	}
	for _, field := range []string{"message", "error", "reason"} {
		collectContent(object[field], &parts)
	}
	if summary != "" {
		parts = append(parts, summary)
	}
	doc := IndexDocument{ConversationID: convID, EventID: eventID, Title: title, Timestamp: timestamp, Role: role, Kind: kind, Tool: tool, SourcePath: path, Text: trimIndexed(strings.Join(parts, "\n")), Summary: trimIndexed(summary)}
	return convID, doc, nil
}

func documentID(path string, document IndexDocument) string {
	return hashBytes([]byte(path + "\x00" + document.ConversationID + "\x00" + document.EventID))
}

func dirSize(path string) int64 {
	var size int64
	_ = filepath.WalkDir(path, func(_ string, entry os.DirEntry, err error) error {
		if err == nil && !entry.IsDir() {
			if info, statErr := entry.Info(); statErr == nil {
				size += info.Size()
			}
		}
		return nil
	})
	return size
}

func statusFor(home, mode string, locations []DataLocation) IndexStatus {
	_, indexPath, manifestPath, _ := appPaths(home)
	manifest := loadManifest(manifestPath)
	var documents uint64
	ready := false
	if index, err := bleve.Open(indexPath); err == nil {
		documents, _ = index.DocCount()
		ready = true
		_ = index.Close()
	}
	return composeStatus(home, mode, locations, manifest, documents, ready)
}

func composeStatus(home, mode string, locations []DataLocation, manifest Manifest, documents uint64, ready bool) IndexStatus {
	_, indexPath, _, _ := appPaths(home)
	status := IndexStatus{Ready: ready, Documents: documents, Locations: locations, LastIndexedAt: manifest.LastIndexedAt, SourceFiles: len(manifest.Files), Service: readServiceStatus(home, mode)}
	conversationSet := map[string]bool{}
	for path, state := range manifest.Files {
		conversationSet[state.ConvID] = true
		if state.Malformed {
			status.MalformedFiles++
			for i := range status.Locations {
				prefix := filepath.Clean(status.Locations[i].Path) + string(os.PathSeparator)
				if strings.HasPrefix(filepath.Clean(path), prefix) {
					status.Locations[i].Malformed++
					break
				}
			}
		}
	}
	status.Conversations = len(conversationSet)
	status.IndexBytes = dirSize(indexPath)
	return status
}

func syncIndex(home string, rebuild bool) (IndexStatus, error) {
	root, indexPath, manifestPath, err := appPaths(home)
	if err != nil {
		return IndexStatus{}, err
	}
	if err := os.MkdirAll(filepath.Join(root, "index"), 0o700); err != nil {
		return IndexStatus{}, err
	}
	if rebuild {
		_ = os.RemoveAll(indexPath)
		_ = os.Remove(manifestPath)
	}
	locations := discoverLocations(home)
	files := sourceFiles(locations)
	manifest := loadManifest(manifestPath)
	index, err := openIndex(indexPath)
	if err != nil {
		return IndexStatus{}, fmt.Errorf("open Bleve index: %w", err)
	}
	indexOpen := true
	defer func() {
		if indexOpen {
			_ = index.Close()
		}
	}()
	batch := index.NewBatch()
	seen := map[string]bool{}
	changedMeta := map[string]bool{}
	currentFiles := map[string]bool{}
	for _, path := range files {
		currentFiles[path] = true
	}
	for path := range manifest.Files {
		if filepath.Base(path) == "meta.json" && !currentFiles[path] {
			changedMeta[filepath.Dir(path)] = true
		}
	}
	for _, path := range files {
		if filepath.Base(path) != "meta.json" {
			continue
		}
		info, statErr := os.Stat(path)
		previous, found := manifest.Files[path]
		if statErr != nil || !found {
			changedMeta[filepath.Dir(path)] = true
			continue
		}
		if previous.Size != info.Size() || previous.ModUnixNS != info.ModTime().UnixNano() {
			raw, readErr := os.ReadFile(path)
			if readErr != nil || previous.SHA256 != hashBytes(raw) {
				changedMeta[filepath.Dir(path)] = true
			} else {
				previous.Size, previous.ModUnixNS = info.Size(), info.ModTime().UnixNano()
				manifest.Files[path] = previous
			}
		}
	}
	added, updated, skipped := 0, 0, 0
	for _, path := range files {
		seen[path] = true
		info, err := os.Stat(path)
		if err != nil {
			continue
		}
		previous, found := manifest.Files[path]
		force := changedMeta[filepath.Dir(path)] || changedMeta[filepath.Dir(filepath.Dir(path))]
		if found && !force && previous.Size == info.Size() && previous.ModUnixNS == info.ModTime().UnixNano() {
			skipped++
			continue
		}
		raw, err := os.ReadFile(path)
		if err != nil {
			continue
		}
		hash := hashBytes(raw)
		if found && !force && previous.SHA256 == hash {
			previous.Size, previous.ModUnixNS = info.Size(), info.ModTime().UnixNano()
			manifest.Files[path] = previous
			skipped++
			continue
		}
		for _, oldID := range previous.DocIDs {
			batch.Delete(oldID)
		}
		convID, document, parseErr := parseDocument(path, raw)
		state := FileState{Size: info.Size(), ModUnixNS: info.ModTime().UnixNano(), SHA256: hash, ConvID: convID}
		if parseErr != nil {
			state.Malformed = true
			manifest.Files[path] = state
			if found {
				updated++
			} else {
				added++
			}
			continue
		}
		id := documentID(path, document)
		if err := batch.Index(id, document); err != nil {
			return IndexStatus{}, err
		}
		state.DocIDs = []string{id}
		manifest.Files[path] = state
		if found {
			updated++
		} else {
			added++
		}
	}
	removed := 0
	for path, previous := range manifest.Files {
		if seen[path] {
			continue
		}
		for _, id := range previous.DocIDs {
			batch.Delete(id)
		}
		delete(manifest.Files, path)
		removed++
	}
	if batch.Size() > 0 {
		if err := index.Batch(batch); err != nil {
			return IndexStatus{}, err
		}
	}
	manifest.LastIndexedAt = time.Now().UTC().Format(time.RFC3339Nano)
	if err := saveManifest(manifestPath, manifest); err != nil {
		return IndexStatus{}, err
	}
	documents, _ := index.DocCount()
	_ = index.Close()
	indexOpen = false
	status := composeStatus(home, "command", locations, manifest, documents, true)
	status.Added, status.Updated, status.Removed, status.Skipped = added, updated, removed, skipped
	return status, nil
}

func termFilter(field, value string) query.Query {
	query := bleve.NewTermQuery(value)
	query.SetField(field)
	return query
}

func searchIndex(home string, request Request) (SearchResponse, error) {
	_, indexPath, _, err := appPaths(home)
	if err != nil {
		return SearchResponse{}, err
	}
	index, err := bleve.Open(indexPath)
	if err != nil {
		return SearchResponse{}, errors.New("the local index is not ready; run Index now first")
	}
	indexOpen := true
	defer func() {
		if indexOpen {
			_ = index.Close()
		}
	}()
	queries := []query.Query{}
	if strings.TrimSpace(request.Query) == "" {
		queries = append(queries, bleve.NewMatchAllQuery())
	} else {
		fields := []struct {
			name  string
			boost float64
		}{{"title", 3}, {"summary", 2}, {"text", 1}, {"tool", 1.5}}
		matches := make([]query.Query, 0, len(fields))
		for _, field := range fields {
			match := bleve.NewMatchQuery(request.Query)
			match.SetField(field.name)
			match.SetBoost(field.boost)
			matches = append(matches, match)
		}
		queries = append(queries, bleve.NewDisjunctionQuery(matches...))
	}
	if request.Filters.Role != "" {
		queries = append(queries, termFilter("role", request.Filters.Role))
	}
	if request.Filters.Kind != "" {
		queries = append(queries, termFilter("kind", request.Filters.Kind))
	}
	if request.Filters.Tool != "" {
		queries = append(queries, termFilter("tool", request.Filters.Tool))
	}
	var start, end time.Time
	if request.Filters.After != "" {
		if parsed, err := time.Parse("2006-01-02", request.Filters.After); err == nil {
			start = parsed
		}
	}
	if request.Filters.Before != "" {
		if parsed, err := time.Parse("2006-01-02", request.Filters.Before); err == nil {
			end = parsed
		}
	}
	if !start.IsZero() || !end.IsZero() {
		rangeQuery := bleve.NewDateRangeQuery(start, end)
		rangeQuery.SetField("timestamp")
		queries = append(queries, rangeQuery)
	}
	combined := bleve.NewConjunctionQuery(queries...)
	limit := request.Limit
	if limit < 1 || limit > 100 {
		limit = 40
	}
	searchRequest := bleve.NewSearchRequestOptions(combined, limit, 0, false)
	searchRequest.Fields = []string{"conversationId", "eventId", "title", "timestamp", "role", "kind", "tool", "sourcePath", "text", "summary"}
	searchRequest.Highlight = bleve.NewHighlight()
	started := time.Now()
	result, err := index.Search(searchRequest)
	if err != nil {
		return SearchResponse{}, err
	}
	hits := make([]SearchHit, 0, len(result.Hits))
	for _, item := range result.Hits {
		field := func(name string) string {
			value, found := item.Fields[name]
			if !found || value == nil {
				return ""
			}
			return fmt.Sprint(value)
		}
		excerpt := ""
		for _, name := range []string{"text", "summary", "title"} {
			if fragments := item.Fragments[name]; len(fragments) > 0 {
				excerpt = strings.Join(fragments, " … ")
				break
			}
		}
		text := field("text")
		if excerpt == "" {
			excerpt = trimExcerpt(text, 280)
		}
		hits = append(hits, SearchHit{ID: item.ID, Score: item.Score, ConversationID: field("conversationId"), EventID: field("eventId"), Title: field("title"), Timestamp: field("timestamp"), Role: field("role"), Kind: field("kind"), Tool: field("tool"), SourcePath: field("sourcePath"), Excerpt: excerpt, Text: text, Summary: field("summary")})
	}
	documents, _ := index.DocCount()
	_ = index.Close()
	indexOpen = false
	status := composeStatus(home, "command", discoverLocations(home), loadManifest(filepath.Join(filepath.Dir(indexPath), "sources.json")), documents, true)
	return SearchResponse{Total: result.Total, DurationMS: float64(time.Since(started).Microseconds()) / 1000, Hits: hits, Status: status}, nil
}

func trimExcerpt(value string, limit int) string {
	value = strings.Join(strings.Fields(value), " ")
	if len(value) > limit {
		return value[:limit] + "…"
	}
	return value
}

func inspectDocument(home, id string) (SearchHit, error) {
	_, indexPath, _, _ := appPaths(home)
	index, err := bleve.Open(indexPath)
	if err != nil {
		return SearchHit{}, errors.New("the local index is not ready")
	}
	defer index.Close()
	request := bleve.NewSearchRequest(bleve.NewDocIDQuery([]string{id}))
	request.Size = 1
	request.Fields = []string{"conversationId", "eventId", "title", "timestamp", "role", "kind", "tool", "sourcePath", "text", "summary"}
	result, err := index.Search(request)
	if err != nil || len(result.Hits) == 0 {
		return SearchHit{}, errors.New("indexed event was not found")
	}
	item := result.Hits[0]
	field := func(name string) string {
		value, found := item.Fields[name]
		if !found || value == nil {
			return ""
		}
		return fmt.Sprint(value)
	}
	return SearchHit{ID: item.ID, Score: item.Score, ConversationID: field("conversationId"), EventID: field("eventId"), Title: field("title"), Timestamp: field("timestamp"), Role: field("role"), Kind: field("kind"), Tool: field("tool"), SourcePath: field("sourcePath"), Text: field("text"), Summary: field("summary"), Excerpt: trimExcerpt(field("text"), 280)}, nil
}

func handle(home, mode string, request Request) (Response, error) {
	switch request.Action {
	case "diagnose", "status":
		status := statusFor(home, mode, discoverLocations(home))
		return Response{Status: &status}, nil
	case "index":
		status, err := syncIndex(home, false)
		status.Service = readServiceStatus(home, mode)
		return Response{Status: &status, Message: "Incremental indexing complete."}, err
	case "rebuild", "repair":
		status, err := syncIndex(home, true)
		status.Service = readServiceStatus(home, mode)
		return Response{Status: &status, Message: "Full index rebuild complete."}, err
	case "search":
		result, err := searchIndex(home, request)
		result.Status.Service = readServiceStatus(home, mode)
		return Response{Search: &result}, err
	case "inspect":
		if request.Document == "" {
			return Response{}, errors.New("documentId is required")
		}
		hit, err := inspectDocument(home, request.Document)
		return Response{Hit: &hit}, err
	default:
		return Response{}, fmt.Errorf("unknown structured action %q", request.Action)
	}
}

func statePath(home string) string {
	root, _ := rootFor(home)
	return filepath.Join(root, "run", "daemon.json")
}

func loadDaemonState(home string) (daemonState, error) {
	raw, err := os.ReadFile(statePath(home))
	if err != nil {
		return daemonState{}, err
	}
	var state daemonState
	if err := json.Unmarshal(raw, &state); err != nil {
		return daemonState{}, err
	}
	if state.Port < 1 || state.Token == "" {
		return daemonState{}, errors.New("invalid daemon state")
	}
	return state, nil
}

func saveDaemonState(home string, state daemonState) error {
	path := statePath(home)
	if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
		return err
	}
	raw, _ := json.MarshalIndent(state, "", "  ")
	temporary := path + ".tmp"
	if err := os.WriteFile(temporary, raw, 0o600); err != nil {
		return err
	}
	if err := os.Rename(temporary, path); err != nil {
		_ = os.Remove(temporary)
		return err
	}
	return nil
}

func callDaemon(home string, request Request) (Response, error) {
	state, err := loadDaemonState(home)
	if err != nil {
		return Response{}, errors.New("conversation search service is not running")
	}
	raw, _ := json.Marshal(request)
	httpRequest, _ := http.NewRequest(http.MethodPost, fmt.Sprintf("http://127.0.0.1:%d/rpc", state.Port), bytes.NewReader(raw))
	httpRequest.Header.Set("Authorization", "Bearer "+state.Token)
	httpRequest.Header.Set("Content-Type", "application/json")
	client := http.Client{Timeout: 300 * time.Second}
	httpResponse, err := client.Do(httpRequest)
	if err != nil {
		return Response{}, errors.New("conversation search service is unreachable")
	}
	defer httpResponse.Body.Close()
	var envelope Envelope
	if err := json.NewDecoder(io.LimitReader(httpResponse.Body, 16*1024*1024)).Decode(&envelope); err != nil {
		return Response{}, err
	}
	if !envelope.OK {
		return Response{}, errors.New(envelope.Error)
	}
	if envelope.Data == nil {
		return Response{}, errors.New("service returned no data")
	}
	return *envelope.Data, nil
}

func readServiceStatus(home, mode string) ServiceStatus {
	status := ServiceStatus{Running: mode == "service", Mode: mode, Version: version, IdleShutdownSeconds: idleShutdownSeconds}
	state, err := loadDaemonState(home)
	if err != nil {
		return status
	}
	started, _ := time.Parse(time.RFC3339Nano, state.StartedAt)
	last, _ := time.Parse(time.RFC3339Nano, state.LastActivity)
	status.PID, status.StartedAt, status.LastActivity = state.PID, state.StartedAt, state.LastActivity
	if !last.IsZero() {
		status.IdleSeconds = int(time.Since(last).Seconds())
	}
	if mode == "service" && state.PID == os.Getpid() {
		status.Running = true
		return status
	}
	client := http.Client{Timeout: 800 * time.Millisecond}
	req, _ := http.NewRequest(http.MethodGet, fmt.Sprintf("http://127.0.0.1:%d/health", state.Port), nil)
	req.Header.Set("Authorization", "Bearer "+state.Token)
	if response, err := client.Do(req); err == nil {
		status.Running = response.StatusCode == 200
		response.Body.Close()
	}
	_ = started
	return status
}

func randomToken() string {
	raw := make([]byte, 32)
	_, _ = rand.Read(raw)
	return base64.RawURLEncoding.EncodeToString(raw)
}

func serve(home string) error {
	return serveWithIdle(home, idleShutdownSeconds*time.Second)
}

func serveWithIdle(home string, idleLimit time.Duration) error {
	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		return err
	}
	defer listener.Close()
	root, _ := rootFor(home)
	_ = os.MkdirAll(filepath.Join(root, "logs"), 0o700)
	state := daemonState{PID: os.Getpid(), Port: listener.Addr().(*net.TCPAddr).Port, Token: randomToken(), Version: version, StartedAt: time.Now().UTC().Format(time.RFC3339Nano), LastActivity: time.Now().UTC().Format(time.RFC3339Nano)}
	if err := saveDaemonState(home, state); err != nil {
		return err
	}
	defer os.Remove(statePath(home))
	var lock sync.Mutex
	lastActivity := time.Now()
	shutdown := make(chan struct{}, 1)
	authorized := func(request *http.Request) bool { return request.Header.Get("Authorization") == "Bearer "+state.Token }
	mux := http.NewServeMux()
	mux.HandleFunc("/health", func(response http.ResponseWriter, request *http.Request) {
		if !authorized(request) {
			http.Error(response, "unauthorized", http.StatusUnauthorized)
			return
		}
		lock.Lock()
		lastActivity = time.Now()
		state.LastActivity = lastActivity.UTC().Format(time.RFC3339Nano)
		_ = saveDaemonState(home, state)
		lock.Unlock()
		response.Header().Set("Content-Type", "application/json")
		_, _ = io.WriteString(response, `{"ok":true}`)
	})
	mux.HandleFunc("/rpc", func(writer http.ResponseWriter, httpRequest *http.Request) {
		if !authorized(httpRequest) {
			http.Error(writer, "unauthorized", http.StatusUnauthorized)
			return
		}
		lock.Lock()
		defer lock.Unlock()
		lastActivity = time.Now()
		state.LastActivity = lastActivity.UTC().Format(time.RFC3339Nano)
		_ = saveDaemonState(home, state)
		var request Request
		if err := json.NewDecoder(io.LimitReader(httpRequest.Body, 1024*1024)).Decode(&request); err != nil {
			writeHTTP(writer, nil, err)
			return
		}
		if request.Action == "stop" {
			writeHTTP(writer, &Response{Message: "Service stopped."}, nil)
			select {
			case shutdown <- struct{}{}:
			default:
			}
			return
		}
		result, err := handle(home, "service", request)
		writeHTTP(writer, &result, err)
	})
	server := http.Server{Handler: mux, ReadHeaderTimeout: 5 * time.Second}
	go func() { _ = server.Serve(listener) }()
	ticker := time.NewTicker(5 * time.Second)
	defer ticker.Stop()
	for {
		select {
		case <-shutdown:
			ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
			defer cancel()
			return server.Shutdown(ctx)
		case <-ticker.C:
			lock.Lock()
			idle := time.Since(lastActivity)
			lock.Unlock()
			if idle >= idleLimit {
				ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
				defer cancel()
				return server.Shutdown(ctx)
			}
		}
	}
}

func writeHTTP(writer http.ResponseWriter, response *Response, err error) {
	writer.Header().Set("Content-Type", "application/json")
	envelope := Envelope{OK: err == nil, Data: response}
	if err != nil {
		envelope.Error = err.Error()
	}
	_ = json.NewEncoder(writer).Encode(envelope)
}

func decodeRequest(value string) (Request, error) {
	raw, err := base64.StdEncoding.DecodeString(value)
	if err != nil {
		return Request{}, errors.New("request was not valid base64")
	}
	var request Request
	if err := json.Unmarshal(raw, &request); err != nil {
		return Request{}, errors.New("request was not valid JSON")
	}
	return request, nil
}

func printEnvelope(response Response, err error) {
	envelope := Envelope{OK: err == nil, Data: &response}
	if err != nil {
		envelope.Data = nil
		envelope.Error = err.Error()
	}
	raw, _ := json.Marshal(envelope)
	fmt.Println(protocolPrefix + base64.StdEncoding.EncodeToString(raw))
}

func main() {
	home, err := os.Getwd()
	if err != nil {
		printEnvelope(Response{}, err)
		os.Exit(1)
	}
	if len(os.Args) < 2 {
		printEnvelope(Response{}, errors.New("usage: conversation-search version|once|rpc|serve"))
		os.Exit(2)
	}
	switch os.Args[1] {
	case "version":
		printEnvelope(Response{Message: fmt.Sprintf("conversation-search %s %s-%s", version, runtime.GOOS, runtime.GOARCH)}, nil)
	case "once":
		if len(os.Args) != 3 {
			printEnvelope(Response{}, errors.New("once requires a base64 JSON request"))
			os.Exit(2)
		}
		request, decodeErr := decodeRequest(os.Args[2])
		if decodeErr != nil {
			printEnvelope(Response{}, decodeErr)
			os.Exit(2)
		}
		response, handleErr := handle(home, "command", request)
		printEnvelope(response, handleErr)
		if handleErr != nil {
			os.Exit(1)
		}
	case "rpc":
		if len(os.Args) != 3 {
			printEnvelope(Response{}, errors.New("rpc requires a base64 JSON request"))
			os.Exit(2)
		}
		request, decodeErr := decodeRequest(os.Args[2])
		if decodeErr != nil {
			printEnvelope(Response{}, decodeErr)
			os.Exit(2)
		}
		response, rpcErr := callDaemon(home, request)
		printEnvelope(response, rpcErr)
		if rpcErr != nil {
			os.Exit(1)
		}
	case "serve":
		if serveErr := serve(home); serveErr != nil {
			fmt.Fprintln(os.Stderr, serveErr)
			os.Exit(1)
		}
	default:
		printEnvelope(Response{}, errors.New("unknown command"))
		os.Exit(2)
	}
}

// strconv is referenced so version probes can confirm the binary was linked
// with the expected standard library without adding another runtime dependency.
var _ = strconv.IntSize
