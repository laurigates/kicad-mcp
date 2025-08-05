#!/bin/bash
#
# Shell wrapper for HTTP-based KiCad-MCP tests
# Provides simple CI integration and server management
#

set -euo pipefail

# Configuration
DEFAULT_HOST="127.0.0.1"
DEFAULT_PORT="8080"
DEFAULT_BACKEND="auto"
SERVER_WAIT_TIME=10
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Usage information
usage() {
    cat << EOF
Usage: $0 [OPTIONS] [TEST_CONFIGS...]

Run HTTP-based KiCad-MCP system tests.

OPTIONS:
    -h, --help          Show this help message
    -v, --verbose       Enable verbose output
    --host HOST         Server host (default: $DEFAULT_HOST)
    --port PORT         Server port (default: $DEFAULT_PORT)
    --backend BACKEND   HTTP backend: requests, curl, auto (default: $DEFAULT_BACKEND)
    --no-server         Don't start server (assume already running)
    --keep-server       Keep server running after tests
    --server-only       Start server and exit (for manual testing)

TEST_CONFIGS:
    Paths to test configuration files or directories.
    If not specified, runs all tests in tests/system/test_configs/

Examples:
    $0                                          # Run all tests
    $0 -v tests/system/test_configs/            # Run all tests verbosely
    $0 led_circuit.json                         # Run specific test
    $0 --server-only                            # Start server for manual testing
EOF
}

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check dependencies
check_dependencies() {
    local missing_deps=()

    # Check Python and uv
    if ! command -v uv &> /dev/null; then
        missing_deps+=("uv (Python package manager)")
    fi

    # Check if we're in the right directory
    if [[ ! -f "$PROJECT_ROOT/pyproject.toml" ]]; then
        log_error "Not in KiCad-MCP project directory"
        exit 1
    fi

    # Check if HTTP backend is available
    if [[ "$BACKEND" == "curl" ]] && ! command -v curl &> /dev/null; then
        missing_deps+=("curl")
    fi

    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "Missing dependencies:"
        for dep in "${missing_deps[@]}"; do
            echo "  - $dep"
        done
        exit 1
    fi
}

# Start MCP server
start_server() {
    log_info "Starting MCP server on $HOST:$PORT"

    cd "$PROJECT_ROOT"

    # Start server in background using our startup script
    uv run python "$SCRIPT_DIR/start_server.py" \
        --host "$HOST" \
        --port "$PORT" \
        --log-level ${VERBOSE:+info} ${VERBOSE:-error} \
        > /tmp/kicad_mcp_server.log 2>&1 &

    SERVER_PID=$!
    echo $SERVER_PID > /tmp/kicad_mcp_server.pid

    log_info "Server started with PID $SERVER_PID"

    # Wait for server to be ready
    log_info "Waiting for server to be ready..."
    local wait_count=0
    while [[ $wait_count -lt $SERVER_WAIT_TIME ]]; do
        if curl -s "http://$HOST:$PORT/" &> /dev/null; then
            log_success "Server is ready!"
            return 0
        fi
        sleep 1
        ((wait_count++))
    done

    log_error "Server failed to start within $SERVER_WAIT_TIME seconds"
    stop_server
    exit 1
}

# Stop MCP server
stop_server() {
    if [[ -f /tmp/kicad_mcp_server.pid ]]; then
        local pid
        pid=$(cat /tmp/kicad_mcp_server.pid)
        if kill -0 "$pid" 2>/dev/null; then
            log_info "Stopping server (PID: $pid)"
            kill "$pid"
            wait "$pid" 2>/dev/null || true
        fi
        rm -f /tmp/kicad_mcp_server.pid
    fi
}

# Cleanup function
cleanup() {
    if [[ "$KEEP_SERVER" != "true" ]]; then
        stop_server
    fi
}

# Run tests
run_tests() {
    local test_configs=("$@")

    # Default to all test configs if none specified
    if [[ ${#test_configs[@]} -eq 0 ]]; then
        test_configs=("$SCRIPT_DIR/test_configs")
    fi

    log_info "Running HTTP tests..."

    cd "$PROJECT_ROOT"

    local python_args=(
        "$SCRIPT_DIR/run_http_tests.py"
        "--host" "$HOST"
        "--port" "$PORT"
        "--backend" "$BACKEND"
        "--no-server"  # We manage the server ourselves
    )

    if [[ "$VERBOSE" == "true" ]]; then
        python_args+=("--verbose")
    fi

    python_args+=("${test_configs[@]}")

    if uv run python "${python_args[@]}"; then
        log_success "All tests passed!"
        return 0
    else
        log_error "Some tests failed!"
        return 1
    fi
}

# Parse command line arguments
VERBOSE=""
HOST="$DEFAULT_HOST"
PORT="$DEFAULT_PORT"
BACKEND="$DEFAULT_BACKEND"
NO_SERVER=""
KEEP_SERVER=""
SERVER_ONLY=""
TEST_CONFIGS=()

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        -v|--verbose)
            VERBOSE="true"
            shift
            ;;
        --host)
            HOST="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --backend)
            BACKEND="$2"
            shift 2
            ;;
        --no-server)
            NO_SERVER="true"
            shift
            ;;
        --keep-server)
            KEEP_SERVER="true"
            shift
            ;;
        --server-only)
            SERVER_ONLY="true"
            shift
            ;;
        -*)
            log_error "Unknown option: $1"
            usage
            exit 1
            ;;
        *)
            TEST_CONFIGS+=("$1")
            shift
            ;;
    esac
done

# Main execution
main() {
    log_info "KiCad-MCP HTTP Test Runner"

    # Check dependencies
    check_dependencies

    # Set up cleanup handler
    trap cleanup EXIT

    # Start server if needed
    if [[ "$NO_SERVER" != "true" ]]; then
        start_server

        if [[ "$SERVER_ONLY" == "true" ]]; then
            log_info "Server running at http://$HOST:$PORT"
            log_info "Press Ctrl+C to stop"
            wait
            exit 0
        fi
    fi

    # Run tests
    if [ ${#TEST_CONFIGS[@]} -eq 0 ]; then
        # No test configs specified, run with defaults
        if run_tests; then
            exit 0
        else
            exit 1
        fi
    else
        # Run with specified test configs
        if run_tests "${TEST_CONFIGS[@]}"; then
            exit 0
        else
            exit 1
        fi
    fi
}

# Run main function
main
