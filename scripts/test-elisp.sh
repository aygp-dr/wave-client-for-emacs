#!/usr/bin/env bash
# Elisp test runner script

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Running Elisp Tests${NC}"
echo "===================="

# Check if emacs is available
if ! command -v emacs &> /dev/null; then
    echo -e "${RED}Error: Emacs is not installed${NC}"
    exit 1
fi

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Run the tests
cd "$PROJECT_ROOT"

echo "Running tests with Emacs $(emacs --version | head -1)"
echo ""

# Run tests in batch mode
if emacs -Q --batch \
    -l tests/run-elisp-tests.el \
    2>&1; then
    echo -e "\n${GREEN}✓ All Elisp tests passed!${NC}"
    exit 0
else
    echo -e "\n${RED}✗ Some Elisp tests failed${NC}"
    exit 1
fi