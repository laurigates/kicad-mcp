"""
Unit tests for migration utilities.

Tests the migration validation and planning utilities that help with
the transition from SExpressionGenerator to SExpressionHandler.
"""

import os
from unittest.mock import MagicMock, patch

from kicad_mcp.utils.migration_utils import MigrationPlanner, MigrationValidator


class TestMigrationValidator:
    """Test suite for MigrationValidator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = MigrationValidator()

    def test_validator_initialization(self):
        """Test validator initialization."""
        assert self.validator.logger is not None
        assert self.validator.service is not None

    @patch.dict(
        os.environ,
        {
            "KICAD_MCP_ENABLE_SEXPR_HANDLER": "true",
            "KICAD_MCP_ENABLE_SEXPR_FALLBACK": "true",
            "KICAD_MCP_VALIDATE_SEXPR_OUTPUT": "true",
        },
    )
    def test_check_environment_configuration_pass(self):
        """Test environment configuration check with correct settings."""
        result = self.validator._check_environment_configuration()

        assert result["status"] == "pass"
        assert "Environment configuration is correct" in result["message"]
        assert result["details"]["missing_variables"] == []
        assert result["details"]["incorrect_variables"] == []

    def test_check_environment_configuration_missing_vars(self):
        """Test environment configuration check with missing variables."""
        # Clear all environment variables
        env_vars = [
            "KICAD_MCP_ENABLE_SEXPR_HANDLER",
            "KICAD_MCP_ENABLE_SEXPR_FALLBACK",
            "KICAD_MCP_VALIDATE_SEXPR_OUTPUT",
        ]

        with patch.dict(os.environ, {}, clear=True):
            result = self.validator._check_environment_configuration()

            assert result["status"] == "fail"
            assert "Environment configuration issues" in result["message"]
            assert len(result["details"]["missing_variables"]) == 3

    @patch.dict(
        os.environ,
        {
            "KICAD_MCP_ENABLE_SEXPR_HANDLER": "false",
            "KICAD_MCP_ENABLE_SEXPR_FALLBACK": "true",
            "KICAD_MCP_VALIDATE_SEXPR_OUTPUT": "true",
        },
    )
    def test_check_environment_configuration_incorrect_vars(self):
        """Test environment configuration check with incorrect values."""
        result = self.validator._check_environment_configuration()

        assert result["status"] == "fail"
        assert "Environment configuration issues" in result["message"]
        assert len(result["details"]["incorrect_variables"]) == 1

    def test_check_feature_flags_safe_config(self):
        """Test feature flags check with safe configuration."""
        with patch.object(self.validator.service, "get_config_info") as mock_config:
            mock_config.return_value = {
                "handler_enabled": True,
                "fallback_enabled": True,
                "rollout_percentage": 5,
                "validate_output": True,
            }

            result = self.validator._check_feature_flags()

            assert result["status"] == "pass"
            assert "properly configured" in result["message"]

    def test_check_feature_flags_risky_config(self):
        """Test feature flags check with risky configuration."""
        with patch.object(self.validator.service, "get_config_info") as mock_config:
            mock_config.return_value = {
                "handler_enabled": False,
                "fallback_enabled": False,
                "rollout_percentage": 50,
                "validate_output": False,
            }

            result = self.validator._check_feature_flags()

            assert result["status"] == "warning"
            assert "Feature flag concerns" in result["message"]
            assert len(result["details"]["issues"]) >= 2

    def test_check_implementation_compatibility_success(self):
        """Test implementation compatibility check with high compatibility."""
        # Mock the service methods to return compatible outputs
        with (
            patch.object(self.validator.service, "_generate_with_generator") as mock_gen,
            patch.object(self.validator.service, "_generate_with_handler") as mock_handler,
            patch.object(self.validator.service, "_remove_uuids") as mock_remove,
            patch.object(self.validator.service, "_structures_equal") as mock_equal,
        ):
            mock_gen.return_value = (
                "(kicad_sch (version 20240618) (generator kicad-mcp) (uuid abc123))"
            )
            mock_handler.return_value = (
                "(kicad_sch (version 20240618) (generator kicad-mcp) (uuid def456))"
            )
            mock_remove.side_effect = lambda x: x  # Return input unchanged
            mock_equal.return_value = True  # Always compatible

            result = self.validator._check_implementation_compatibility()

            assert result["status"] == "pass"
            assert result["details"]["compatibility_percentage"] == 100.0
            assert "excellent" in result["message"]

    def test_check_implementation_compatibility_low_compatibility(self):
        """Test implementation compatibility check with low compatibility."""
        with (
            patch.object(self.validator.service, "_generate_with_generator") as mock_gen,
            patch.object(self.validator.service, "_generate_with_handler") as mock_handler,
            patch.object(self.validator.service, "_remove_uuids") as mock_remove,
            patch.object(self.validator.service, "_structures_equal") as mock_equal,
        ):
            mock_gen.return_value = "(kicad_sch (version 20240618))"
            mock_handler.return_value = "(kicad_sch (version 20240618))"
            mock_remove.side_effect = lambda x: x
            mock_equal.return_value = False  # Never compatible

            result = self.validator._check_implementation_compatibility()

            assert result["status"] == "fail"
            assert result["details"]["compatibility_percentage"] == 0.0
            assert "too low" in result["message"]

    def test_check_implementation_compatibility_error(self):
        """Test implementation compatibility check with errors."""
        with patch.object(
            self.validator.service, "_generate_with_generator", side_effect=Exception("Test error")
        ):
            result = self.validator._check_implementation_compatibility()

            # The method catches exceptions and logs them but continues processing
            # So we check that test results include errors
            assert "test_results" in result["details"]
            test_results = result["details"]["test_results"]
            assert any("error" in test_result for test_result in test_results)

    def test_check_test_coverage_passing(self):
        """Test test coverage check with passing tests."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "23 passed"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result):
            result = self.validator._check_test_coverage()

            assert result["status"] == "pass"
            assert result["details"]["service_tests"] == "passing"

    def test_check_test_coverage_failing(self):
        """Test test coverage check with failing tests."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "1 failed"
        mock_result.stderr = "AssertionError"

        with patch("subprocess.run", return_value=mock_result):
            result = self.validator._check_test_coverage()

            assert result["status"] == "fail"
            assert "failing" in result["message"]
            assert result["details"]["service_tests"] == "failing"

    def test_get_test_cases(self):
        """Test test case generation."""
        test_cases = self.validator._get_test_cases()

        assert len(test_cases) >= 4
        assert all(
            len(case) == 4 for case in test_cases
        )  # name, components, power_symbols, connections

        # Check for expected test cases
        case_names = [case[0] for case in test_cases]
        assert "Empty Circuit" in case_names
        assert "Simple Resistor" in case_names
        assert "Complex Circuit" in case_names

    def test_generate_recommendations_all_pass(self):
        """Test recommendation generation when all checks pass."""
        checks = {
            "environment": {"status": "pass"},
            "feature_flags": {"status": "pass"},
            "compatibility": {"status": "pass"},
            "test_coverage": {"status": "pass"},
        }

        recommendations = self.validator._generate_recommendations(checks)

        assert len(recommendations) == 1
        assert "ready for migration" in recommendations[0]

    def test_generate_recommendations_with_issues(self):
        """Test recommendation generation with various issues."""
        checks = {
            "environment": {
                "status": "fail",
                "details": {"missing_variables": ["KICAD_MCP_ENABLE_SEXPR_HANDLER"]},
            },
            "feature_flags": {"status": "warning"},
            "compatibility": {"status": "fail"},
            "test_coverage": {"status": "fail"},
        }

        recommendations = self.validator._generate_recommendations(checks)

        assert len(recommendations) >= 4
        assert any("environment variables" in rec for rec in recommendations)
        assert any("feature flag" in rec for rec in recommendations)
        assert any("compatibility" in rec for rec in recommendations)
        assert any("tests" in rec for rec in recommendations)

    def test_validate_migration_readiness_integration(self):
        """Test full migration readiness validation."""
        # Mock all sub-checks to pass
        with (
            patch.object(self.validator, "_check_environment_configuration") as mock_env,
            patch.object(self.validator, "_check_feature_flags") as mock_flags,
            patch.object(self.validator, "_check_implementation_compatibility") as mock_compat,
            patch.object(self.validator, "_check_test_coverage") as mock_tests,
        ):
            mock_env.return_value = {"status": "pass"}
            mock_flags.return_value = {"status": "pass"}
            mock_compat.return_value = {"status": "pass"}
            mock_tests.return_value = {"status": "pass"}

            result = self.validator.validate_migration_readiness()

            assert result["ready_for_migration"] is True
            assert "timestamp" in result
            assert len(result["checks"]) == 4
            assert len(result["recommendations"]) == 1


class TestMigrationPlanner:
    """Test suite for MigrationPlanner class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.planner = MigrationPlanner()

    def test_planner_initialization(self):
        """Test planner initialization."""
        assert self.planner.logger is not None

    def test_create_migration_plan_default(self):
        """Test migration plan creation with default settings."""
        plan = self.planner.create_migration_plan()

        assert plan["target_rollout"] == 100
        assert "created_at" in plan
        assert "phases" in plan
        assert len(plan["phases"]) >= 6  # Multiple phases for gradual rollout

        # Check phase structure
        for phase in plan["phases"]:
            assert "phase" in phase
            assert "name" in phase
            assert "duration" in phase
            assert "rollout_percentage" in phase
            assert "environment_vars" in phase
            assert "tasks" in phase
            assert "success_criteria" in phase

    def test_create_migration_plan_partial_rollout(self):
        """Test migration plan creation with partial rollout."""
        plan = self.planner.create_migration_plan(target_rollout=50)

        assert plan["target_rollout"] == 50

        # Should not include full deployment phase
        final_phase = plan["phases"][-1]
        assert final_phase["rollout_percentage"] <= 50

    def test_create_migration_plan_phase_progression(self):
        """Test that migration plan phases progress logically."""
        plan = self.planner.create_migration_plan()

        rollout_percentages = [phase["rollout_percentage"] for phase in plan["phases"]]

        # Should start at 0 and increase
        assert rollout_percentages[0] == 0
        assert rollout_percentages[-1] == 100

        # Should be in ascending order
        for i in range(1, len(rollout_percentages)):
            assert rollout_percentages[i] >= rollout_percentages[i - 1]

    def test_execute_migration_step_success(self):
        """Test successful migration step execution."""
        phase = {
            "phase": 1,
            "name": "Test Phase",
            "environment_vars": {"TEST_VAR": "test_value", "ANOTHER_VAR": "another_value"},
        }

        # Clear environment first
        old_env = {}
        for var in phase["environment_vars"]:
            old_env[var] = os.environ.get(var)

        try:
            result = self.planner.execute_migration_step(phase)

            assert result["phase"] == 1
            assert result["status"] == "completed"
            assert len(result["environment_changes"]) == 2
            assert result["errors"] == []

            # Check environment variables were set
            for var, expected_value in phase["environment_vars"].items():
                assert os.environ.get(var) == expected_value

            # Check change tracking
            changes = {change["variable"]: change for change in result["environment_changes"]}
            assert "TEST_VAR" in changes
            assert changes["TEST_VAR"]["new_value"] == "test_value"

        finally:
            # Restore environment
            for var, old_value in old_env.items():
                if old_value is None:
                    os.environ.pop(var, None)
                else:
                    os.environ[var] = old_value

    def test_execute_migration_step_error(self):
        """Test migration step execution with error."""
        # Create a phase that will cause an error
        phase = {"phase": 1, "name": "Error Phase", "environment_vars": {}}

        # Mock an error in the execution
        with patch.object(self.planner.logger, "info", side_effect=Exception("Test error")):
            result = self.planner.execute_migration_step(phase)

            assert result["status"] == "failed"
            assert len(result["errors"]) == 1
            assert "Test error" in result["errors"][0]


class TestMigrationUtilsIntegration:
    """Integration tests for migration utilities."""

    def test_full_migration_workflow(self):
        """Test complete migration workflow."""
        validator = MigrationValidator()
        planner = MigrationPlanner()

        # Step 1: Validate readiness
        with (
            patch.object(validator, "_check_environment_configuration") as mock_env,
            patch.object(validator, "_check_feature_flags") as mock_flags,
            patch.object(validator, "_check_implementation_compatibility") as mock_compat,
            patch.object(validator, "_check_test_coverage") as mock_tests,
        ):
            # Mock all checks to pass
            mock_env.return_value = {"status": "pass"}
            mock_flags.return_value = {"status": "pass"}
            mock_compat.return_value = {"status": "pass"}
            mock_tests.return_value = {"status": "pass"}

            validation_result = validator.validate_migration_readiness()
            assert validation_result["ready_for_migration"] is True

        # Step 2: Create migration plan
        plan = planner.create_migration_plan()
        assert len(plan["phases"]) >= 6

        # Step 3: Execute first phase
        first_phase = plan["phases"][0]
        execution_result = planner.execute_migration_step(first_phase)

        assert execution_result["status"] == "completed"
        assert len(execution_result["environment_changes"]) > 0

    def test_migration_validation_cli_function(self):
        """Test the CLI validation function."""
        from kicad_mcp.utils.migration_utils import run_migration_validation

        # Mock the validator to avoid actual validation
        with patch("kicad_mcp.utils.migration_utils.MigrationValidator") as mock_validator_class:
            mock_validator = mock_validator_class.return_value
            mock_validator.validate_migration_readiness.return_value = {
                "timestamp": "2024-01-01T00:00:00",
                "ready_for_migration": True,
                "checks": {
                    "environment": {"status": "pass", "message": "All good"},
                    "feature_flags": {"status": "pass", "message": "Configured properly"},
                },
                "recommendations": ["System is ready for migration"],
            }

            # This should not raise an exception
            with patch("builtins.print"):  # Suppress output
                run_migration_validation()

            mock_validator.validate_migration_readiness.assert_called_once()
