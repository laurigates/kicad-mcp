"""
Migration utilities for transitioning from SExpressionGenerator to SExpressionHandler.

This module provides utilities to help with the gradual migration from the
original string-based S-expression generator to the new sexpdata-based handler.
"""

from datetime import datetime
import logging
import os
from typing import Any

import sexpdata

from kicad_mcp.utils.sexpr_service import SExpressionService


class MigrationValidator:
    """Validates the migration from generator to handler implementations."""

    def __init__(self):
        """Initialize the migration validator."""
        self.logger = logging.getLogger(__name__)
        self.service = SExpressionService()

    def validate_migration_readiness(self) -> dict[str, Any]:
        """
        Validate that the system is ready for migration.

        Returns:
            Dictionary with validation results and recommendations
        """
        results = {
            "timestamp": datetime.now().isoformat(),
            "ready_for_migration": False,
            "checks": {},
            "recommendations": [],
        }

        # Check 1: Environment configuration
        env_check = self._check_environment_configuration()
        results["checks"]["environment"] = env_check

        # Check 2: Feature flag configuration
        feature_check = self._check_feature_flags()
        results["checks"]["feature_flags"] = feature_check

        # Check 3: Implementation compatibility
        compat_check = self._check_implementation_compatibility()
        results["checks"]["compatibility"] = compat_check

        # Check 4: Test coverage
        test_check = self._check_test_coverage()
        results["checks"]["test_coverage"] = test_check

        # Overall readiness assessment
        all_checks_passed = all(
            check.get("status") == "pass" for check in results["checks"].values()
        )
        results["ready_for_migration"] = all_checks_passed

        # Generate recommendations
        results["recommendations"] = self._generate_recommendations(results["checks"])

        return results

    def _check_environment_configuration(self) -> dict[str, Any]:
        """Check environment variable configuration."""
        check = {"status": "pass", "message": "Environment configuration is correct", "details": {}}

        # Required environment variables for safe migration
        required_vars = {
            "KICAD_MCP_ENABLE_SEXPR_HANDLER": "true",
            "KICAD_MCP_ENABLE_SEXPR_FALLBACK": "true",
            "KICAD_MCP_VALIDATE_SEXPR_OUTPUT": "true",
        }

        missing_vars = []
        incorrect_vars = []

        for var, expected_value in required_vars.items():
            actual_value = os.environ.get(var)
            if actual_value is None:
                missing_vars.append(var)
            elif actual_value.lower() != expected_value.lower():
                incorrect_vars.append(f"{var}={actual_value} (expected {expected_value})")

        check["details"]["missing_variables"] = missing_vars
        check["details"]["incorrect_variables"] = incorrect_vars

        if missing_vars or incorrect_vars:
            check["status"] = "fail"
            check["message"] = (
                f"Environment configuration issues: {len(missing_vars)} missing, {len(incorrect_vars)} incorrect"
            )

        return check

    def _check_feature_flags(self) -> dict[str, Any]:
        """Check feature flag configuration."""
        check = {
            "status": "pass",
            "message": "Feature flags are properly configured",
            "details": {},
        }

        config = self.service.get_config_info()
        check["details"]["current_config"] = config

        # Validate configuration for safe migration
        issues = []

        if not config["handler_enabled"]:
            issues.append("Handler is not enabled")

        if not config["fallback_enabled"]:
            issues.append("Fallback mechanism is not enabled")

        if config["rollout_percentage"] > 10 and not config["validate_output"]:
            issues.append("High rollout percentage without output validation is risky")

        if issues:
            check["status"] = "warning"
            check["message"] = f"Feature flag concerns: {', '.join(issues)}"
            check["details"]["issues"] = issues

        return check

    def _check_implementation_compatibility(self) -> dict[str, Any]:
        """Check compatibility between implementations."""
        check = {"status": "pass", "message": "Implementations are compatible", "details": {}}

        try:
            # Test with various circuit configurations
            test_cases = self._get_test_cases()

            compatibility_results = []
            for _i, (name, components, power_symbols, connections) in enumerate(test_cases):
                try:
                    # Generate with both implementations
                    generator_output = self.service._generate_with_generator(
                        name, components, power_symbols, connections
                    )
                    handler_output = self.service._generate_with_handler(
                        name, components, power_symbols, connections, False
                    )

                    # Parse both outputs
                    generator_parsed = sexpdata.loads(generator_output)
                    handler_parsed = sexpdata.loads(handler_output)

                    # Remove UUIDs for comparison
                    generator_clean = self.service._remove_uuids(generator_parsed)
                    handler_clean = self.service._remove_uuids(handler_parsed)

                    # Check structural equality
                    is_compatible = self.service._structures_equal(generator_clean, handler_clean)

                    compatibility_results.append(
                        {
                            "test_case": name,
                            "compatible": is_compatible,
                            "generator_length": len(generator_output),
                            "handler_length": len(handler_output),
                        }
                    )

                except Exception as e:
                    compatibility_results.append(
                        {"test_case": name, "compatible": False, "error": str(e)}
                    )

            check["details"]["test_results"] = compatibility_results

            # Calculate compatibility percentage
            compatible_count = sum(
                1 for result in compatibility_results if result.get("compatible", False)
            )
            total_count = len(compatibility_results)
            compatibility_percentage = (
                (compatible_count / total_count * 100) if total_count > 0 else 0
            )

            check["details"]["compatibility_percentage"] = compatibility_percentage

            if compatibility_percentage < 90:
                check["status"] = "fail"
                check["message"] = (
                    f"Implementation compatibility too low: {compatibility_percentage:.1f}%"
                )
            elif compatibility_percentage < 95:
                check["status"] = "warning"
                check["message"] = (
                    f"Implementation compatibility acceptable but not ideal: {compatibility_percentage:.1f}%"
                )
            else:
                check["message"] = (
                    f"Implementation compatibility excellent: {compatibility_percentage:.1f}%"
                )

        except Exception as e:
            check["status"] = "fail"
            check["message"] = f"Failed to check implementation compatibility: {e}"
            check["details"]["error"] = str(e)

        return check

    def _check_test_coverage(self) -> dict[str, Any]:
        """Check test coverage for S-expression components."""
        check = {"status": "pass", "message": "Test coverage is adequate", "details": {}}

        # This would ideally integrate with coverage tools
        # For now, we'll do a basic check
        try:
            import subprocess

            result = subprocess.run(
                ["uv", "run", "pytest", "tests/unit/utils/test_sexpr_service.py", "--no-cov", "-q"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                check["details"]["service_tests"] = "passing"
            else:
                check["status"] = "fail"
                check["message"] = "S-expression service tests are failing"
                check["details"]["service_tests"] = "failing"
                check["details"]["test_output"] = result.stdout + result.stderr

        except subprocess.TimeoutExpired:
            check["status"] = "warning"
            check["message"] = "Test execution timed out"
        except Exception as e:
            check["status"] = "warning"
            check["message"] = f"Could not run test coverage check: {e}"

        return check

    def _get_test_cases(self) -> list[tuple[str, list[dict], list[dict], list[dict]]]:
        """Get test cases for compatibility checking."""
        return [
            # Empty circuit
            ("Empty Circuit", [], [], []),
            # Simple resistor circuit
            (
                "Simple Resistor",
                [
                    {
                        "reference": "R1",
                        "value": "1k",
                        "symbol_library": "Device",
                        "symbol_name": "R",
                        "position": (10, 10),
                    }
                ],
                [],
                [],
            ),
            # Power symbol test
            (
                "Power Symbol Test",
                [],
                [{"reference": "#PWR001", "power_type": "VCC", "position": (10, 20)}],
                [],
            ),
            # Complex circuit
            (
                "Complex Circuit",
                [
                    {
                        "reference": "R1",
                        "value": "1k",
                        "symbol_library": "Device",
                        "symbol_name": "R",
                        "position": (10, 10),
                    },
                    {
                        "reference": "C1",
                        "value": "10uF",
                        "symbol_library": "Device",
                        "symbol_name": "C",
                        "position": (20, 10),
                    },
                ],
                [
                    {"reference": "#PWR001", "power_type": "VCC", "position": (10, 20)},
                    {"reference": "#PWR002", "power_type": "GND", "position": (20, 20)},
                ],
                [{"start_x": 10, "start_y": 15, "end_x": 20, "end_y": 15}],
            ),
        ]

    def _generate_recommendations(self, checks: dict[str, Any]) -> list[str]:
        """Generate recommendations based on check results."""
        recommendations = []

        env_check = checks.get("environment", {})
        if env_check.get("status") == "fail":
            recommendations.append("Configure required environment variables before migration")
            missing = env_check.get("details", {}).get("missing_variables", [])
            if missing:
                recommendations.append(f"Set these environment variables: {', '.join(missing)}")

        feature_check = checks.get("feature_flags", {})
        if feature_check.get("status") in ["fail", "warning"]:
            recommendations.append("Review and adjust feature flag configuration")

        compat_check = checks.get("compatibility", {})
        if compat_check.get("status") == "fail":
            recommendations.append("Fix implementation compatibility issues before migration")
        elif compat_check.get("status") == "warning":
            recommendations.append("Consider fixing compatibility issues for smoother migration")

        test_check = checks.get("test_coverage", {})
        if test_check.get("status") != "pass":
            recommendations.append("Ensure all tests are passing before migration")

        if not recommendations:
            recommendations.append("System is ready for migration")

        return recommendations


class MigrationPlanner:
    """Plans and executes gradual migration steps."""

    def __init__(self):
        """Initialize the migration planner."""
        self.logger = logging.getLogger(__name__)

    def create_migration_plan(self, target_rollout: int = 100) -> dict[str, Any]:
        """
        Create a step-by-step migration plan.

        Args:
            target_rollout: Target rollout percentage (0-100)

        Returns:
            Migration plan with steps and timelines
        """
        plan = {
            "created_at": datetime.now().isoformat(),
            "target_rollout": target_rollout,
            "estimated_duration": "2-4 weeks",
            "phases": [],
        }

        # Phase 1: Preparation (Days 1-3)
        plan["phases"].append(
            {
                "phase": 1,
                "name": "Preparation and Validation",
                "duration": "3 days",
                "rollout_percentage": 0,
                "environment_vars": {
                    "KICAD_MCP_ENABLE_SEXPR_HANDLER": "true",
                    "KICAD_MCP_ENABLE_SEXPR_FALLBACK": "true",
                    "KICAD_MCP_VALIDATE_SEXPR_OUTPUT": "true",
                    "KICAD_MCP_SEXPR_ROLLOUT_PERCENTAGE": "0",
                },
                "tasks": [
                    "Run migration validation",
                    "Set up monitoring and logging",
                    "Prepare rollback procedures",
                    "Train team on new system",
                ],
                "success_criteria": [
                    "All validation checks pass",
                    "Monitoring dashboard operational",
                    "Rollback procedures tested",
                ],
            }
        )

        # Phase 2: Canary deployment (Days 4-7)
        plan["phases"].append(
            {
                "phase": 2,
                "name": "Canary Deployment",
                "duration": "4 days",
                "rollout_percentage": 5,
                "environment_vars": {
                    "KICAD_MCP_SEXPR_ROLLOUT_PERCENTAGE": "5",
                    "KICAD_MCP_ENABLE_SEXPR_COMPARISON": "true",
                    "KICAD_MCP_ENABLE_PERFORMANCE_LOGGING": "true",
                },
                "tasks": [
                    "Deploy to 5% of requests",
                    "Monitor error rates and performance",
                    "Collect compatibility metrics",
                    "Review A/B comparison results",
                ],
                "success_criteria": [
                    "Error rate < 0.1%",
                    "Performance within 20% of baseline",
                    "> 95% compatibility rate",
                ],
            }
        )

        # Phase 3: Gradual rollout (Days 8-14)
        rollout_steps = [10, 25, 50, 75]
        for i, rollout in enumerate(rollout_steps):
            # Only add phases that don't exceed target rollout
            if rollout <= target_rollout:
                plan["phases"].append(
                    {
                        "phase": 3 + i,
                        "name": f"Gradual Rollout - {rollout}%",
                        "duration": "1-2 days",
                        "rollout_percentage": rollout,
                        "environment_vars": {"KICAD_MCP_SEXPR_ROLLOUT_PERCENTAGE": str(rollout)},
                        "tasks": [
                            f"Increase rollout to {rollout}%",
                            "Monitor system health",
                            "Collect user feedback",
                            "Adjust configuration if needed",
                        ],
                        "success_criteria": [
                            "Error rate remains stable",
                            "No performance degradation",
                            "Positive user feedback",
                        ],
                    }
                )

        # Final phase: Full deployment
        if target_rollout == 100:
            plan["phases"].append(
                {
                    "phase": len(plan["phases"]) + 1,
                    "name": "Full Deployment",
                    "duration": "2 days",
                    "rollout_percentage": 100,
                    "environment_vars": {
                        "KICAD_MCP_SEXPR_IMPLEMENTATION": "handler",
                        "KICAD_MCP_SEXPR_ROLLOUT_PERCENTAGE": "100",
                        "KICAD_MCP_ENABLE_SEXPR_COMPARISON": "false",
                    },
                    "tasks": [
                        "Switch to 100% new implementation",
                        "Disable A/B testing",
                        "Update documentation",
                        "Plan deprecation of old implementation",
                    ],
                    "success_criteria": [
                        "System stable at 100% rollout",
                        "All metrics within acceptable ranges",
                        "Migration considered successful",
                    ],
                }
            )

        return plan

    def execute_migration_step(self, phase: dict[str, Any]) -> dict[str, Any]:
        """
        Execute a single migration step.

        Args:
            phase: Phase configuration from migration plan

        Returns:
            Execution results and status
        """
        result = {
            "phase": phase["phase"],
            "started_at": datetime.now().isoformat(),
            "status": "in_progress",
            "environment_changes": [],
            "errors": [],
        }

        try:
            # Apply environment variable changes
            env_vars = phase.get("environment_vars", {})
            for var, value in env_vars.items():
                old_value = os.environ.get(var)
                os.environ[var] = value
                result["environment_changes"].append(
                    {"variable": var, "old_value": old_value, "new_value": value}
                )

            self.logger.info(f"Migration phase {phase['phase']} executed: {phase['name']}")
            result["status"] = "completed"

        except Exception as e:
            result["status"] = "failed"
            result["errors"].append(str(e))
            self.logger.error(f"Migration phase {phase['phase']} failed: {e}")

        result["completed_at"] = datetime.now().isoformat()
        return result


def run_migration_validation() -> None:
    """CLI function to run migration validation."""
    validator = MigrationValidator()
    results = validator.validate_migration_readiness()

    print("=== MIGRATION VALIDATION RESULTS ===")
    print(f"Timestamp: {results['timestamp']}")
    print(f"Ready for migration: {'✅ YES' if results['ready_for_migration'] else '❌ NO'}")
    print()

    print("CHECK RESULTS:")
    for check_name, check_result in results["checks"].items():
        status_icon = {"pass": "✅", "warning": "⚠️", "fail": "❌"}.get(check_result["status"], "❓")
        print(f"  {status_icon} {check_name}: {check_result['message']}")

    print()
    print("RECOMMENDATIONS:")
    for i, recommendation in enumerate(results["recommendations"], 1):
        print(f"  {i}. {recommendation}")

    if results["ready_for_migration"]:
        print("\n🎉 System is ready for migration!")
    else:
        print("\n⚠️  Please address the issues above before proceeding with migration.")


if __name__ == "__main__":
    run_migration_validation()
