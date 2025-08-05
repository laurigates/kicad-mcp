# KiCad-MCP HTTP System Tests

This directory contains HTTP-based system tests for the KiCad-MCP project. These tests validate KiCad project creation and file generation without requiring LLM agents in the loop.

## Overview

The HTTP testing system provides:

- **End-to-end validation** of KiCad project creation through HTTP API calls
- **File format validation** ensuring generated files are KiCad-compatible
- **KiCad CLI integration** for real compatibility testing
- **Test isolation** with automatic cleanup
- **CI/CD integration** through simple shell scripts
- **Multiple HTTP backends** (requests/httpx and curl)

## Architecture

```
tests/system/
├── __init__.py                 # Package initialization
├── http_client.py             # HTTP client abstraction (requests/curl)
├── temp_manager.py            # Temporary directory management
├── test_config.py             # JSON test configuration parser
├── validators.py              # File validation framework
├── run_http_tests.py          # Main test runner
├── run_tests.sh              # Shell wrapper for CI
├── test_configs/             # JSON test definitions
│   ├── basic_project_creation.json
│   └── led_circuit.json
└── README.md                 # This file
```

## Quick Start

### 1. Run All Tests

```bash
# Run all tests with automatic server management
./tests/system/run_tests.sh

# Run with verbose output
./tests/system/run_tests.sh --verbose
```

### 2. Run Specific Tests

```bash
# Run specific test configuration
./tests/system/run_tests.sh tests/system/test_configs/led_circuit.json

# Run multiple specific tests
./tests/system/run_tests.sh led_circuit.json basic_project_creation.json
```

### 3. Manual Server Testing

```bash
# Start server for manual testing
./tests/system/run_tests.sh --server-only

# In another terminal, run tests against running server
./tests/system/run_tests.sh --no-server
```

## Test Configuration Format

Tests are defined in JSON files with the following structure:

```json
{
  "test_name": "basic_led_circuit",
  "description": "Create basic LED circuit with resistor",
  "mcp_calls": [
    {
      "tool": "create_new_project",
      "params": {
        "project_name": "led_test",
        "project_path": "{temp_dir}/led_test"
      }
    },
    {
      "tool": "create_kicad_schematic_from_text",
      "params": {
        "project_path": "{temp_dir}/led_test/led_test.kicad_pro",
        "circuit_description": "circuit \"LED\":\n  components:\n    - R1: resistor 220Ω at (50, 50)\n    - LED1: led red at (100, 50)\n  power:\n    - VCC: +5V at (30, 30)\n    - GND: GND at (30, 70)"
      }
    }
  ],
  "validations": [
    {
      "type": "file_exists",
      "path": "{temp_dir}/led_test/led_test.kicad_pro"
    },
    {
      "type": "file_format",
      "path": "{temp_dir}/led_test/led_test.kicad_sch",
      "format": "sexpr"
    },
    {
      "type": "component_count",
      "path": "{temp_dir}/led_test/led_test.kicad_sch",
      "expected": 2
    }
  ],
  "timeout": 60,
  "skip_cleanup": false
}
```

### Template Variables

- `{temp_dir}` - Replaced with test-specific temporary directory path
- `{project_name}` - Project name (future expansion)

### Available MCP Tools

- `create_new_project` - Create a new KiCad project
- `create_kicad_schematic_from_text` - Generate schematic from text description
- `add_component` - Add components to schematic
- `add_power_symbol` - Add power symbols
- `create_wire_connection` - Create wire connections

### Available Validators

- `file_exists` - Check if file exists
- `file_format` - Validate JSON or S-expression format
- `kicad_cli_validate` - Use KiCad CLI for validation
- `component_count` - Count components in schematic
- `power_symbol_count` - Count power symbols in schematic

## Advanced Usage

### Python API

```python
from tests.system.run_http_tests import HTTPTestRunner
from tests.system.test_config import TestConfigLoader

# Create test runner
runner = HTTPTestRunner(
    server_host="127.0.0.1",
    server_port=8080,
    http_backend="requests",
    verbose=True
)

# Load and run tests
loader = TestConfigLoader()
config = loader.load_config_file("my_test.json")
result = runner.run_single_test(config)
print(result)
```

### Custom Validators

```python
from tests.system.validators import Validator, ValidationResult

class CustomValidator(Validator):
    def validate(self, path: str, **kwargs) -> ValidationResult:
        # Custom validation logic
        return ValidationResult(True, "Custom validation passed")

# Register with validation runner
runner = ValidationRunner()
runner.validators["custom"] = CustomValidator()
```

### HTTP Backends

The system supports multiple HTTP backends:

- **`requests`** (default) - Uses httpx library for Python-native HTTP
- **`curl`** - Uses curl command-line tool
- **`auto`** - Tries requests first, falls back to curl

```bash
# Use specific backend
./tests/system/run_tests.sh --backend curl
./tests/system/run_tests.sh --backend requests
```

## CI/CD Integration

### GitHub Actions

```yaml
name: HTTP System Tests
on: [push, pull_request]

jobs:
  http-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install uv
          uv sync
      - name: Run HTTP tests
        run: ./tests/system/run_tests.sh --verbose
```

### Local CI Testing

```bash
# Run tests in CI-like environment
docker run -v $(pwd):/workspace -w /workspace python:3.12 \
  bash -c "pip install uv && uv sync && ./tests/system/run_tests.sh"
```

## Troubleshooting

### Common Issues

1. **Server Won't Start**
   ```bash
   # Check if port is in use
   lsof -i :8080

   # Use different port
   ./tests/system/run_tests.sh --port 8081
   ```

2. **KiCad CLI Not Found**
   ```bash
   # Install KiCad or ensure it's in PATH
   which kicad-cli

   # Tests will skip KiCad CLI validation if not available
   ```

3. **HTTP Backend Issues**
   ```bash
   # Try different backend
   ./tests/system/run_tests.sh --backend curl

   # Check dependencies
   curl --version
   python -c "import httpx; print('httpx available')"
   ```

4. **Test Failures**
   ```bash
   # Run with verbose output for debugging
   ./tests/system/run_tests.sh --verbose

   # Keep temp directories for inspection
   # Edit test config: "skip_cleanup": true
   ```

### Debugging Tests

1. **Enable Verbose Mode**
   ```bash
   ./tests/system/run_tests.sh --verbose
   ```

2. **Keep Server Running**
   ```bash
   ./tests/system/run_tests.sh --keep-server
   # Server stays up after tests for manual inspection
   ```

3. **Manual Server Interaction**
   ```bash
   # Start server
   ./tests/system/run_tests.sh --server-only

   # In another terminal, test manually
   curl -X POST http://127.0.0.1:8080/mcp \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"create_new_project","arguments":{"project_name":"test","project_path":"/tmp/test"}}}'
   ```

4. **Inspect Generated Files**
   ```bash
   # Set skip_cleanup: true in test config
   # Files will remain in /tmp/kicad_mcp_test_* directories
   ls -la /tmp/kicad_mcp_test_*
   ```

## Performance Considerations

- Tests run in isolation with separate temporary directories
- Server startup adds ~2-3 seconds overhead
- KiCad CLI validation adds ~1-2 seconds per file
- Parallel test execution not yet implemented (future enhancement)

## Contributing

When adding new tests:

1. Create JSON configuration in `test_configs/`
2. Follow naming convention: `feature_description.json`
3. Include comprehensive validations
4. Test both success and failure cases
5. Document any special requirements

When adding new validators:

1. Extend `Validator` base class in `validators.py`
2. Register in `ValidationRunner.__init__()`
3. Add documentation and examples
4. Include error handling for edge cases

## Future Enhancements

- [ ] Parallel test execution
- [ ] Test result caching
- [ ] Performance baseline tracking
- [ ] Integration with existing pytest infrastructure
- [ ] Advanced circuit template system
- [ ] Real-time progress reporting
- [ ] Test result artifacts and screenshots
