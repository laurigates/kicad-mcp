"""
Security tests for DRC CLI implementation.

Tests command injection vulnerabilities and ensures secure subprocess execution.
"""

import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kicad_mcp.tools.drc_impl.cli_drc import run_drc_via_cli
from kicad_mcp.utils.path_validator import PathValidationError


@pytest.mark.asyncio
class TestDRCSecurityVulnerabilities:
    """Test security vulnerabilities in DRC CLI implementation."""

    async def test_command_injection_malicious_filename(self):
        """Test that malicious filenames cannot inject commands."""
        # Create mock context
        ctx = AsyncMock()

        # Malicious filename that could cause command injection
        malicious_filename = "--malicious-flag.kicad_pcb; rm -rf /"

        # Mock the secure subprocess runner to capture the validation
        with patch("kicad_mcp.tools.drc_impl.cli_drc.get_subprocess_runner") as mock_runner:
            mock_instance = MagicMock()
            mock_runner.return_value = mock_instance

            # Configure mock to raise validation error for malicious input
            mock_instance.run_kicad_command_async = AsyncMock(
                side_effect=PathValidationError("Invalid path")
            )

            # Test that malicious filename is rejected
            result = await run_drc_via_cli(malicious_filename, ctx)

            assert result["success"] is False
            assert "error" in result
            assert "validation" in result["error"].lower() or "invalid" in result["error"].lower()

    async def test_path_traversal_attack(self):
        """Test that path traversal attacks are blocked."""
        ctx = AsyncMock()

        # Path traversal attempt
        malicious_path = "../../../etc/passwd.kicad_pcb"

        with patch("kicad_mcp.tools.drc_impl.cli_drc.get_subprocess_runner") as mock_runner:
            mock_instance = MagicMock()
            mock_runner.return_value = mock_instance

            # Configure mock to raise validation error
            mock_instance.run_kicad_command_async = AsyncMock(
                side_effect=PathValidationError("Path traversal detected")
            )

            result = await run_drc_via_cli(malicious_path, ctx)

            assert result["success"] is False
            assert "error" in result

    async def test_valid_file_accepted(self):
        """Test that valid filenames are accepted."""
        ctx = AsyncMock()

        # Create a temporary valid PCB file
        with tempfile.NamedTemporaryFile(suffix=".kicad_pcb", delete=False) as temp_file:
            temp_file.write(b"(kicad_pcb (version 20220914))")
            valid_filename = temp_file.name

        try:
            with patch("kicad_mcp.tools.drc_impl.cli_drc.get_subprocess_runner") as mock_runner:
                mock_instance = MagicMock()
                mock_runner.return_value = mock_instance

                # Mock successful DRC execution
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = ""
                mock_result.stderr = ""
                mock_instance.run_kicad_command_async = AsyncMock(return_value=mock_result)

                # Mock DRC report file creation
                with (
                    patch("os.path.exists", return_value=True),
                    patch(
                        "builtins.open",
                        return_value=MagicMock(
                            __enter__=MagicMock(
                                return_value=MagicMock(
                                    read=MagicMock(return_value='{"violations": []}')
                                )
                            ),
                            __exit__=MagicMock(return_value=None),
                        ),
                    ),
                    patch("json.load", return_value={"violations": []}),
                ):
                    await run_drc_via_cli(valid_filename, ctx)

                    # Should successfully process valid file
                    assert mock_instance.run_kicad_command_async.called

        finally:
            # Clean up temporary file
            if os.path.exists(valid_filename):
                os.unlink(valid_filename)

    async def test_subprocess_runner_called_correctly(self):
        """Test that SecureSubprocessRunner is called with correct parameters."""
        ctx = AsyncMock()
        valid_filename = "/tmp/test.kicad_pcb"

        with patch("kicad_mcp.tools.drc_impl.cli_drc.get_subprocess_runner") as mock_runner:
            mock_instance = MagicMock()
            mock_runner.return_value = mock_instance

            # Mock successful execution
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_result.stderr = ""
            mock_instance.run_kicad_command_async = AsyncMock(return_value=mock_result)

            # Mock DRC report handling
            with (
                patch("os.path.exists", return_value=True),
                patch(
                    "builtins.open",
                    return_value=MagicMock(
                        __enter__=MagicMock(
                            return_value=MagicMock(
                                read=MagicMock(return_value='{"violations": []}')
                            )
                        ),
                        __exit__=MagicMock(return_value=None),
                    ),
                ),
                patch("json.load", return_value={"violations": []}),
            ):
                await run_drc_via_cli(valid_filename, ctx)

                # Verify SecureSubprocessRunner was called with correct parameters
                mock_instance.run_kicad_command_async.assert_called_once()
                call_args = mock_instance.run_kicad_command_async.call_args

                # Extract arguments and keyword arguments
                args, kwargs = call_args

                # First positional argument should be command_args
                command_args = kwargs["command_args"]
                assert "pcb" in command_args
                assert "drc" in command_args
                assert "--format" in command_args
                assert "json" in command_args

                # input_files should contain the PCB file
                input_files = kwargs["input_files"]
                assert valid_filename in input_files
