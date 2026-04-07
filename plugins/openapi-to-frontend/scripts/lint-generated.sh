#!/bin/bash
#
# Lint generated code to ensure quality and type correctness.
#
# Usage:
#   ./lint-generated.sh [directory]
#
# Runs:
#   - ESLint for code style and potential issues
#   - TypeScript compiler in no-emit mode for type checking
#
# Exit codes:
#   0 - All checks passed
#   1 - One or more checks failed
#

set -u

# Default directory to lint
TARGET_DIR="${1:-.}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔍 Linting generated code in: $TARGET_DIR"
echo ""

FAILED=0

# Check for package.json
if [[ ! -f "package.json" ]]; then
    echo -e "${YELLOW}Warning: No package.json found. Running checks anyway...${NC}"
fi

# Run ESLint
echo "📝 Running ESLint..."
if command -v npx &> /dev/null; then
    if npx eslint "$TARGET_DIR" --ext .ts,.tsx --max-warnings 0 2>/dev/null; then
        echo -e "${GREEN}✓ ESLint passed${NC}"
    else
        # Check if eslint is configured
        if [[ -f ".eslintrc" ]] || [[ -f ".eslintrc.js" ]] || [[ -f ".eslintrc.json" ]] || [[ -f "eslint.config.js" ]]; then
            echo -e "${RED}✗ ESLint found issues${NC}"
            FAILED=1
        else
            echo -e "${YELLOW}⚠ ESLint not configured, skipping${NC}"
        fi
    fi
else
    echo -e "${YELLOW}⚠ npx not found, skipping ESLint${NC}"
fi

echo ""

# Run TypeScript type check
echo "🔷 Running TypeScript type check..."
if command -v npx &> /dev/null; then
    if [[ -f "tsconfig.json" ]]; then
        if npx tsc --noEmit 2>&1; then
            echo -e "${GREEN}✓ TypeScript check passed${NC}"
        else
            echo -e "${RED}✗ TypeScript found type errors${NC}"
            FAILED=1
        fi
    else
        echo -e "${YELLOW}⚠ No tsconfig.json found, skipping TypeScript check${NC}"
    fi
else
    echo -e "${YELLOW}⚠ npx not found, skipping TypeScript check${NC}"
fi

echo ""

# Run Prettier check (if configured)
echo "🎨 Checking formatting with Prettier..."
if command -v npx &> /dev/null; then
    if [[ -f ".prettierrc" ]] || [[ -f ".prettierrc.js" ]] || [[ -f ".prettierrc.json" ]] || [[ -f "prettier.config.js" ]]; then
        if npx prettier --check "$TARGET_DIR/**/*.{ts,tsx}" 2>/dev/null; then
            echo -e "${GREEN}✓ Prettier check passed${NC}"
        else
            echo -e "${YELLOW}⚠ Formatting issues found (run 'npx prettier --write' to fix)${NC}"
            # Don't fail on formatting, just warn
        fi
    else
        echo -e "${YELLOW}⚠ Prettier not configured, skipping${NC}"
    fi
fi

echo ""

# Summary
if [[ $FAILED -eq 0 ]]; then
    echo -e "${GREEN}═══════════════════════════════════════${NC}"
    echo -e "${GREEN}✓ All lint checks passed!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════${NC}"
    exit 0
else
    echo -e "${RED}═══════════════════════════════════════${NC}"
    echo -e "${RED}✗ Some lint checks failed${NC}"
    echo -e "${RED}═══════════════════════════════════════${NC}"
    exit 1
fi
