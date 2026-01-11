#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

show_help() {
    echo "Usage: ./build.sh <command>"
    echo ""
    echo "Commands:"
    echo "  install      Install dependencies"
    echo "  test         Run tests"
    echo "  lint         Run linter (ruff)"
    echo "  format       Format code (ruff)"
    echo "  check        Run lint + test"
    echo "  build        Build wheel and sdist"
    echo "  publish-local  Install locally for uvx usage"
    echo "  clean        Clean build artifacts"
    echo "  help         Show this help"
    echo ""
}

cmd_install() {
    echo -e "${GREEN}Installing dependencies...${NC}"
    uv sync --all-extras
}

cmd_test() {
    echo -e "${GREEN}Running tests...${NC}"
    uv run pytest "$@"
}

cmd_lint() {
    echo -e "${GREEN}Running linter...${NC}"
    uv run ruff check src/ tests/
}

cmd_format() {
    echo -e "${GREEN}Formatting code...${NC}"
    uv run ruff format src/ tests/
    uv run ruff check --fix src/ tests/
}

cmd_check() {
    cmd_lint
    cmd_test
}

cmd_build() {
    echo -e "${GREEN}Building package...${NC}"
    uv build
    echo ""
    echo -e "${GREEN}Built artifacts:${NC}"
    ls -la dist/
}

cmd_publish_local() {
    echo -e "${GREEN}Building and installing locally...${NC}"
    uv build

    # Install the wheel globally so uvx can find it
    echo -e "${GREEN}Installing to user site-packages...${NC}"
    uv tool install --force dist/*.whl

    echo ""
    echo -e "${GREEN}Installed! You can now run:${NC}"
    echo "  ralph --help"
    echo ""
    echo "Or with uvx:"
    echo "  uvx ralph-swarm --help"
}

cmd_clean() {
    echo -e "${GREEN}Cleaning build artifacts...${NC}"
    rm -rf dist/
    rm -rf *.egg-info/
    rm -rf src/*.egg-info/
    rm -rf .pytest_cache/
    rm -rf .ruff_cache/
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    echo "Clean!"
}

# Main
case "${1:-help}" in
    install)
        cmd_install
        ;;
    test)
        shift
        cmd_test "$@"
        ;;
    lint)
        cmd_lint
        ;;
    format)
        cmd_format
        ;;
    check)
        cmd_check
        ;;
    build)
        cmd_build
        ;;
    publish-local)
        cmd_publish_local
        ;;
    clean)
        cmd_clean
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
