#!/bin/bash
#
# Test Plugin Loading via OpenHands Cloud API
#
# This script creates a conversation with a specified plugin loaded,
# waits for the sandbox to be ready, and verifies the agent response
# matches an expected string or pattern.
#
# Usage:
#   ./test_plugin.sh --plugin <plugin-path> --message <initial-message> --expect <string-or-regex>
#
# Examples:
#   # Test city-weather plugin
#   ./test_plugin.sh \
#     --plugin "plugins/city-weather" \
#     --message "/city-weather:now Tokyo" \
#     --expect "Weather Report"
#
#   # Test magic-test plugin with regex
#   ./test_plugin.sh \
#     --plugin "plugins/magic-test" \
#     --message "alakazam" \
#     --expect "Plugin loaded successfully" \
#     --regex
#
# Environment Variables:
#   OPENHANDS_URL     - OpenHands Cloud URL (default: https://app.all-hands.dev)
#   OH_API_KEY        - Your OpenHands API key (required)
#   OPENHANDS_API_KEY - Alternative name for API key (fallback if OH_API_KEY not set)
#   MARKETPLACE_REPO  - Plugin marketplace repo (default: github:OpenHands/extensions)
#   MARKETPLACE_REF   - Git ref for marketplace (default: main)
#

set -e

# ============================================================================
# DEFAULTS
# ============================================================================

OPENHANDS_URL="${OPENHANDS_URL:-https://app.all-hands.dev}"
# Support both OH_API_KEY (preferred) and OPENHANDS_API_KEY (fallback)
OH_API_KEY="${OH_API_KEY:-${OPENHANDS_API_KEY:-}}"
MARKETPLACE_REPO="${MARKETPLACE_REPO:-github:OpenHands/extensions}"
MARKETPLACE_REF="${MARKETPLACE_REF:-main}"

# Script arguments
PLUGIN_PATH=""
INITIAL_MESSAGE=""
EXPECT_STRING=""
USE_REGEX=false
OPEN_BROWSER=false
VERBOSE=false
MAX_WAIT=180  # Maximum seconds to wait for conversation
POLL_INTERVAL=3

# ============================================================================
# COLORS
# ============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ============================================================================
# FUNCTIONS
# ============================================================================

usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS]

Test plugin loading via OpenHands Cloud API.

Required Arguments:
  --plugin PATH       Path to plugin within the marketplace repo (e.g., plugins/city-weather)
  --message TEXT      Initial message to send (e.g., "/city-weather:now Tokyo")
  --expect STRING     String or regex pattern to expect in the response

Options:
  --regex             Treat --expect as a regex pattern (default: substring match)
  --open              Open the conversation in a browser when ready
  --verbose           Show detailed output including API responses
  --max-wait SECONDS  Maximum time to wait for conversation (default: 180)
  --poll SECONDS      Polling interval in seconds (default: 3)
  --help              Show this help message

Environment Variables:
  OPENHANDS_URL       OpenHands Cloud URL (default: https://app.all-hands.dev)
  OH_API_KEY          Your OpenHands API key (required)
  OPENHANDS_API_KEY   Alternative name for API key (fallback if OH_API_KEY not set)
  MARKETPLACE_REPO    Plugin marketplace repo (default: github:OpenHands/extensions)
  MARKETPLACE_REF     Git ref for marketplace (default: main)

Examples:
  # Test city-weather plugin
  export OH_API_KEY="sk-oh-..."
  $(basename "$0") \\
    --plugin "plugins/city-weather" \\
    --message "/city-weather:now Tokyo" \\
    --expect "Weather Report"

  # Test with custom marketplace
  MARKETPLACE_REPO="github:myorg/my-plugins" $(basename "$0") \\
    --plugin "plugins/my-plugin" \\
    --message "/my-plugin:test" \\
    --expect "success"
EOF
    exit 0
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_verbose() {
    if [ "$VERBOSE" = true ]; then
        echo -e "${CYAN}[DEBUG]${NC} $1"
    fi
}

check_dependencies() {
    local missing=()
    
    if ! command -v curl &> /dev/null; then
        missing+=("curl")
    fi
    
    if ! command -v jq &> /dev/null; then
        missing+=("jq")
    fi
    
    if [ ${#missing[@]} -gt 0 ]; then
        log_error "Missing required dependencies: ${missing[*]}"
        echo "  Install with:"
        echo "    brew install ${missing[*]}  # macOS"
        echo "    apt install ${missing[*]}   # Ubuntu/Debian"
        exit 1
    fi
}

validate_config() {
    if [ -z "$OH_API_KEY" ]; then
        log_error "OH_API_KEY environment variable is required"
        echo "  export OH_API_KEY='sk-oh-your-key-here'"
        echo "  (OPENHANDS_API_KEY is also accepted)"
        exit 1
    fi
    
    if [ -z "$PLUGIN_PATH" ]; then
        log_error "--plugin argument is required"
        exit 1
    fi
    
    if [ -z "$INITIAL_MESSAGE" ]; then
        log_error "--message argument is required"
        exit 1
    fi
    
    if [ -z "$EXPECT_STRING" ]; then
        log_error "--expect argument is required"
        exit 1
    fi
}

create_conversation() {
    log_info "Creating conversation with plugin: $PLUGIN_PATH"
    log_verbose "Marketplace: $MARKETPLACE_REPO (ref: $MARKETPLACE_REF)"
    log_verbose "Message: $INITIAL_MESSAGE"
    
    local payload
    payload=$(cat << EOF
{
  "initial_message": {
    "content": [
      {
        "type": "text",
        "text": "$INITIAL_MESSAGE"
      }
    ]
  },
  "plugins": [{
    "source": "$MARKETPLACE_REPO",
    "ref": "$MARKETPLACE_REF",
    "repo_path": "$PLUGIN_PATH"
  }]
}
EOF
)
    
    log_verbose "Request payload: $payload"
    
    RESPONSE=$(curl -s -X POST "${OPENHANDS_URL}/api/v1/app-conversations" \
      -H "Authorization: Bearer ${OH_API_KEY}" \
      -H "Content-Type: application/json" \
      -d "$payload")
    
    log_verbose "Response: $RESPONSE"
    
    TASK_ID=$(echo "$RESPONSE" | jq -r '.id // empty')
    
    if [ -z "$TASK_ID" ]; then
        log_error "Failed to create conversation"
        echo "Response: $RESPONSE"
        exit 1
    fi
    
    log_info "Task created: $TASK_ID"
}

wait_for_conversation() {
    log_info "Waiting for conversation to start (max ${MAX_WAIT}s)..."
    
    local elapsed=0
    local conversation_id=""
    
    while [ $elapsed -lt $MAX_WAIT ]; do
        # Poll the start-tasks endpoint
        TASK_RESPONSE=$(curl -s -X GET "${OPENHANDS_URL}/api/v1/app-conversations/start-tasks/search" \
          -H "Authorization: Bearer ${OH_API_KEY}")
        
        # Find our task by ID
        TASK_INFO=$(echo "$TASK_RESPONSE" | jq -r --arg id "$TASK_ID" '.items[] | select(.id == $id)')
        TASK_STATUS=$(echo "$TASK_INFO" | jq -r '.status // "WORKING"')
        conversation_id=$(echo "$TASK_INFO" | jq -r '.app_conversation_id // empty')
        
        printf "\r  Elapsed: %ds | Status: %-10s" "$elapsed" "$TASK_STATUS"
        
        if [ "$TASK_STATUS" == "READY" ] && [ -n "$conversation_id" ] && [ "$conversation_id" != "null" ]; then
            echo ""
            CONVERSATION_ID="$conversation_id"
            log_success "Conversation ready: $CONVERSATION_ID"
            return 0
        fi
        
        if [ "$TASK_STATUS" == "ERROR" ]; then
            echo ""
            local detail
            detail=$(echo "$TASK_INFO" | jq -r '.detail // "Unknown error"')
            log_error "Task failed: $detail"
            exit 1
        fi
        
        sleep "$POLL_INTERVAL"
        elapsed=$((elapsed + POLL_INTERVAL))
    done
    
    echo ""
    log_error "Timeout waiting for conversation to start"
    exit 1
}

get_agent_response() {
    log_info "Fetching conversation events..."
    
    # Get conversation details including runtime URL and session key
    CONV_RESPONSE=$(curl -s -X GET "${OPENHANDS_URL}/api/v1/app-conversations/search" \
      -H "Authorization: Bearer ${OH_API_KEY}")
    
    CONV_INFO=$(echo "$CONV_RESPONSE" | jq -r --arg id "$CONVERSATION_ID" '.items[] | select(.id == $id)')
    CONVERSATION_URL=$(echo "$CONV_INFO" | jq -r '.conversation_url // empty')
    SESSION_API_KEY=$(echo "$CONV_INFO" | jq -r '.session_api_key // empty')
    
    if [ -z "$CONVERSATION_URL" ] || [ "$CONVERSATION_URL" == "null" ]; then
        log_error "Could not get conversation URL"
        log_verbose "Conv info: $CONV_INFO"
        exit 1
    fi
    
    log_verbose "Conversation URL: $CONVERSATION_URL"
    
    # Wait a bit for agent to process and respond
    log_info "Waiting for agent response..."
    sleep 10
    
    # Query events from the Agent Server
    EVENTS_RESPONSE=$(curl -s "${CONVERSATION_URL}/events/search" \
      -H "X-Session-API-Key: ${SESSION_API_KEY}")
    
    log_verbose "Events: $EVENTS_RESPONSE"
    
    # Extract agent messages
    AGENT_RESPONSE=$(echo "$EVENTS_RESPONSE" | jq -r '
      .items[]
      | select(.kind == "MessageEvent" and .source == "agent")
      | .llm_message.content[0].text // empty
    ' 2>/dev/null | head -1)
    
    if [ -z "$AGENT_RESPONSE" ]; then
        # Try alternative event structure
        AGENT_RESPONSE=$(echo "$EVENTS_RESPONSE" | jq -r '
          .items[]
          | select(.source == "agent")
          | .message // .content // empty
        ' 2>/dev/null | head -1)
    fi
    
    if [ -n "$AGENT_RESPONSE" ]; then
        log_info "Agent responded (${#AGENT_RESPONSE} chars)"
        log_verbose "Response preview: ${AGENT_RESPONSE:0:200}..."
    else
        log_warn "No agent response captured yet"
    fi
}

verify_response() {
    log_info "Verifying response against expected pattern..."
    
    if [ -z "$AGENT_RESPONSE" ]; then
        log_error "No agent response to verify"
        return 1
    fi
    
    local match_found=false
    
    if [ "$USE_REGEX" = true ]; then
        if echo "$AGENT_RESPONSE" | grep -qE "$EXPECT_STRING"; then
            match_found=true
        fi
    else
        if echo "$AGENT_RESPONSE" | grep -qF "$EXPECT_STRING"; then
            match_found=true
        fi
    fi
    
    if [ "$match_found" = true ]; then
        log_success "Response matches expected pattern: \"$EXPECT_STRING\""
        return 0
    else
        log_error "Response does not match expected pattern: \"$EXPECT_STRING\""
        echo ""
        echo "Agent response:"
        echo "----------------------------------------"
        echo "$AGENT_RESPONSE" | head -20
        echo "----------------------------------------"
        return 1
    fi
}

open_in_browser() {
    local url="${OPENHANDS_URL}/conversations/${CONVERSATION_ID}"
    
    if [ "$OPEN_BROWSER" = true ]; then
        log_info "Opening in browser: $url"
        
        if command -v open &> /dev/null; then
            open "$url"
        elif command -v xdg-open &> /dev/null; then
            xdg-open "$url"
        else
            echo "Open in browser: $url"
        fi
    else
        echo ""
        echo "View conversation:"
        echo "  $url"
    fi
}

# ============================================================================
# PARSE ARGUMENTS
# ============================================================================

while [[ $# -gt 0 ]]; do
    case $1 in
        --plugin)
            PLUGIN_PATH="$2"
            shift 2
            ;;
        --message)
            INITIAL_MESSAGE="$2"
            shift 2
            ;;
        --expect)
            EXPECT_STRING="$2"
            shift 2
            ;;
        --regex)
            USE_REGEX=true
            shift
            ;;
        --open)
            OPEN_BROWSER=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --max-wait)
            MAX_WAIT="$2"
            shift 2
            ;;
        --poll)
            POLL_INTERVAL="$2"
            shift 2
            ;;
        --help|-h)
            usage
            ;;
        *)
            log_error "Unknown argument: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# ============================================================================
# MAIN
# ============================================================================

echo ""
echo -e "${GREEN}=== Plugin Test ===${NC}"
echo ""

check_dependencies
validate_config

echo -e "${BLUE}Configuration:${NC}"
echo "  OpenHands URL:  $OPENHANDS_URL"
echo "  Marketplace:    $MARKETPLACE_REPO (ref: $MARKETPLACE_REF)"
echo "  Plugin:         $PLUGIN_PATH"
echo "  Message:        $INITIAL_MESSAGE"
echo "  Expect:         $EXPECT_STRING $([ "$USE_REGEX" = true ] && echo "(regex)")"
echo ""

create_conversation
wait_for_conversation
get_agent_response

if verify_response; then
    echo ""
    echo -e "${GREEN}=== TEST PASSED ===${NC}"
    open_in_browser
    exit 0
else
    echo ""
    echo -e "${RED}=== TEST FAILED ===${NC}"
    open_in_browser
    exit 1
fi
