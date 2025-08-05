"""
Main HTTP test runner for KiCad-MCP system tests.

Orchestrates HTTP-based testing of KiCad project creation and validation.
"""

import argparse
from pathlib import Path
import sys
import time
from typing import Any

import uvicorn

from kicad_mcp.server import create_server
from tests.system.http_client import HTTPClientError, create_http_client, mcp_tool_call
from tests.system.temp_manager import TempDirectoryManager
from tests.system.test_config import TestConfig, TestConfigLoader
from tests.system.validators import ValidationRunner


class TestResult:
    """Result of a single test execution."""

    def __init__(
        self,
        test_name: str,
        success: bool,
        duration: float,
        error: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        """Initialize test result.

        Args:
            test_name: Name of the test
            success: Whether test passed
            duration: Test execution time in seconds
            error: Error message if test failed
            details: Additional test details
        """
        self.test_name = test_name
        self.success = success
        self.duration = duration
        self.error = error
        self.details = details or {}

    def __str__(self) -> str:
        """String representation of test result."""
        status = "PASS" if self.success else "FAIL"
        return f"[{status}] {self.test_name} ({self.duration:.2f}s)"


class HTTPTestRunner:
    """Main test runner for HTTP-based tests."""

    def __init__(
        self,
        server_host: str = "127.0.0.1",
        server_port: int = 8080,
        http_backend: str = "auto",
        verbose: bool = False,
    ):
        """Initialize HTTP test runner.

        Args:
            server_host: Host for MCP server
            server_port: Port for MCP server
            http_backend: HTTP client backend ("requests", "curl", or "auto")
            verbose: Enable verbose logging
        """
        self.server_host = server_host
        self.server_port = server_port
        self.base_url = f"http://{server_host}:{server_port}"
        self.http_backend = http_backend
        self.verbose = verbose

        self.config_loader = TestConfigLoader()
        self.validation_runner = ValidationRunner()
        self.temp_manager = TempDirectoryManager()

    async def start_test_server(self) -> None:
        """Start the MCP server for testing."""
        if self.verbose:
            print(f"Starting MCP server on {self.base_url}")

        # Create the FastMCP server
        server = create_server()

        # Start server in background
        config = uvicorn.Config(
            server.http_app(transport="http"),
            host=self.server_host,
            port=self.server_port,
            log_level="error" if not self.verbose else "info",
        )
        server_instance = uvicorn.Server(config)

        # Start server in a background task
        await server_instance.serve()

    def wait_for_server(self, timeout: int = 30) -> bool:
        """Wait for server to be ready.

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if server is ready, False if timeout
        """
        if self.verbose:
            print("Waiting for server to be ready...")

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                client = create_http_client(self.base_url, self.http_backend)
                if client.health_check():
                    if self.verbose:
                        print("Server is ready!")
                    return True
            except Exception:
                pass

            time.sleep(1)

        return False

    def run_single_test(self, config: TestConfig) -> TestResult:
        """Run a single test configuration.

        Args:
            config: Test configuration to run

        Returns:
            Test result
        """
        if self.verbose:
            print(f"Running test: {config.test_name}")

        start_time = time.time()

        try:
            # Create temporary directory for this test
            temp_dir = self.temp_manager.create_temp_dir(prefix=f"test_{config.test_name}_")

            if self.verbose:
                print(f"  Using temp directory: {temp_dir}")

            # Create HTTP client
            client = create_http_client(self.base_url, self.http_backend)

            # Execute MCP calls
            for i, mcp_call in enumerate(config.mcp_calls):
                if self.verbose:
                    print(f"  Executing MCP call {i + 1}/{len(config.mcp_calls)}: {mcp_call.tool}")

                # Substitute templates in parameters
                params = self.temp_manager.substitute_dict_templates(mcp_call.params, temp_dir)

                # Make the MCP call
                try:
                    result = mcp_tool_call(client, mcp_call.tool, params)
                    if self.verbose:
                        print(f"    Result: {result}")
                except HTTPClientError as e:
                    raise Exception(f"MCP call {mcp_call.tool} failed: {e}") from e

            # Run validations
            validation_results = []
            for i, validation in enumerate(config.validations):
                if self.verbose:
                    print(
                        f"  Running validation {i + 1}/{len(config.validations)}: {validation.type}"
                    )

                # Substitute templates in validation path
                validation_path = self.temp_manager.substitute_templates(validation.path, temp_dir)

                # Extract validation parameters
                validation_params = {
                    k: v for k, v in validation.dict().items() if k not in ("type", "path")
                }

                # Run validation
                result = self.validation_runner.run_validation(
                    validation.type, validation_path, **validation_params
                )
                validation_results.append(result)

                if self.verbose:
                    print(f"    {result}")

                if not result.success:
                    # Test failed validation
                    duration = time.time() - start_time
                    return TestResult(
                        config.test_name,
                        False,
                        duration,
                        f"Validation failed: {result.message}",
                        {"validation_results": [str(r) for r in validation_results]},
                    )

            # All validations passed
            duration = time.time() - start_time
            return TestResult(
                config.test_name,
                True,
                duration,
                details={
                    "temp_dir": temp_dir,
                    "validation_results": [str(r) for r in validation_results],
                },
            )

        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                config.test_name,
                False,
                duration,
                str(e),
            )

        finally:
            # Cleanup unless specified otherwise
            if not config.skip_cleanup and self.verbose:
                print(f"  Cleaning up temp directory: {temp_dir}")
            # Cleanup will happen automatically via temp_manager

    def run_tests(self, config_paths: list[str]) -> list[TestResult]:
        """Run multiple tests from configuration files.

        Args:
            config_paths: List of paths to test configuration files or directories

        Returns:
            List of test results
        """
        # Load all test configurations
        configs = {}
        for config_path in config_paths:
            path = Path(config_path)
            if path.is_file():
                config = self.config_loader.load_config_file(path)
                configs[config.test_name] = config
            elif path.is_dir():
                dir_configs = self.config_loader.load_config_directory(path)
                configs.update(dir_configs)
            else:
                print(f"Warning: Path not found: {config_path}")

        if not configs:
            print("No test configurations found!")
            return []

        if self.verbose:
            print(f"Loaded {len(configs)} test configurations:")
            for name in configs:
                print(f"  - {name}")

        # Run all tests
        results = []
        for config in configs.values():
            result = self.run_single_test(config)
            results.append(result)

        return results

    def print_summary(self, results: list[TestResult]) -> None:
        """Print test results summary.

        Args:
            results: List of test results
        """
        if not results:
            print("No tests were run.")
            return

        passed = sum(1 for r in results if r.success)
        failed = len(results) - passed
        total_duration = sum(r.duration for r in results)

        print("\n" + "=" * 60)
        print("TEST RESULTS SUMMARY")
        print("=" * 60)

        for result in results:
            print(result)
            if not result.success and result.error:
                print(f"    Error: {result.error}")

        print(f"\nTotal: {len(results)} tests")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Duration: {total_duration:.2f}s")

        if failed > 0:
            print(f"\n{failed} test(s) failed!")
            sys.exit(1)
        else:
            print("\nAll tests passed!")


def main() -> None:
    """Main entry point for HTTP test runner."""
    parser = argparse.ArgumentParser(description="HTTP-based KiCad-MCP test runner")
    parser.add_argument(
        "configs",
        nargs="+",
        help="Test configuration files or directories",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host for MCP server (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for MCP server (default: 8000)",
    )
    parser.add_argument(
        "--backend",
        choices=["requests", "curl", "auto"],
        default="auto",
        help="HTTP client backend (default: auto)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--no-server",
        action="store_true",
        help="Don't start server (assume already running)",
    )

    args = parser.parse_args()

    # Create test runner
    runner = HTTPTestRunner(
        server_host=args.host,
        server_port=args.port,
        http_backend=args.backend,
        verbose=args.verbose,
    )

    try:
        if not args.no_server:
            # Start server (this would need to be async in practice)
            print("Note: Server management not fully implemented yet")
            print("Please start the server manually with:")
            print(
                f"  uvicorn kicad_mcp.server:create_server().http_app() --host {args.host} --port {args.port}"
            )
            print()

        # Wait for server to be ready
        if not runner.wait_for_server():
            print(f"Failed to connect to server at {runner.base_url}")
            sys.exit(1)

        # Run tests
        results = runner.run_tests(args.configs)

        # Print summary
        runner.print_summary(results)

    except KeyboardInterrupt:
        print("\nTest run interrupted!")
        sys.exit(1)
    except Exception as e:
        print(f"Test run failed: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)
    finally:
        # Cleanup will happen automatically via temp_manager
        pass


if __name__ == "__main__":
    main()
