"""
Integration tests for end-to-end KiCad MCP workflows.
Tests complete user workflows from project creation to analysis.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, Mock

from mcp.server.fastmcp import Context, FastMCP
import pytest

from kicad_mcp.tools.circuit_tools import register_circuit_tools
from kicad_mcp.tools.export_tools import register_export_tools
from kicad_mcp.tools.netlist_tools import register_netlist_tools

# Import all tool registration functions
from kicad_mcp.tools.project_tools import register_project_tools


@pytest.mark.integration
class TestFullWorkflow:
    """Integration tests for complete KiCad MCP workflows."""

    @pytest.fixture
    async def mcp_server(self):
        """Create a fully configured MCP server for testing."""
        mcp = FastMCP("kicad-mcp-test")

        # Register all tool modules
        register_project_tools(mcp)
        register_circuit_tools(mcp)
        register_netlist_tools(mcp)
        register_export_tools(mcp)

        return mcp

    @pytest.fixture
    def mock_context(self):
        """Create a mock context for async operations."""
        context = Mock(spec=Context)
        context.info = AsyncMock()
        context.report_progress = AsyncMock()
        context.emit_log = AsyncMock()
        return context

    @pytest.mark.asyncio
    async def test_complete_project_workflow(self, mcp_server, mock_context, temp_dir):
        """Test complete workflow: create project -> add components -> generate netlist -> export."""
        project_name = "integration_test_project"
        project_path = str(temp_dir / project_name)

        # Step 1: Create new project
        create_func = mcp_server._tools["create_new_circuit"].func
        result = await create_func(
            project_name=project_name,
            project_path=project_path,
            description="Integration test project",
            ctx=mock_context,
        )
        assert result["success"] is True
        project_file = f"{project_path}/{project_name}.kicad_pro"
        assert Path(project_file).exists()

        # Step 2: Add power symbols
        add_power_func = mcp_server._tools["add_power_symbols"].func
        result = await add_power_func(
            project_path=project_file, power_types=["VCC", "GND", "+3V3"], ctx=mock_context
        )
        assert result["success"] is True
        assert len(result["power_symbols"]) == 3

        # Step 3: Add main components
        add_component_func = mcp_server._tools["add_component_to_circuit"].func

        # Add ESP32
        result = await add_component_func(
            project_path=project_file,
            component_type="MCU_Espressif:ESP32-WROOM-32",
            reference="U1",
            value="ESP32-WROOM-32",
            position_x=2000,
            position_y=2000,
            ctx=mock_context,
        )
        assert result["success"] is True
        result["component_uuid"]

        # Add resistors
        resistor_uuids = []
        for i in range(3):
            result = await add_component_func(
                project_path=project_file,
                component_type="Device:R",
                reference=f"R{i + 1}",
                value="10k",
                position_x=1000 + i * 500,
                position_y=1500,
                ctx=mock_context,
            )
            assert result["success"] is True
            resistor_uuids.append(result["component_uuid"])

        # Add capacitors
        capacitor_uuids = []
        for i in range(2):
            result = await add_component_func(
                project_path=project_file,
                component_type="Device:C",
                reference=f"C{i + 1}",
                value="100nF",
                position_x=3000 + i * 500,
                position_y=1500,
                ctx=mock_context,
            )
            assert result["success"] is True
            capacitor_uuids.append(result["component_uuid"])

        # Step 4: Connect components
        connect_func = mcp_server._tools["connect_components"].func

        # Connect some components
        connections = [
            ("R1", "2", "R2", "1"),
            ("R2", "2", "R3", "1"),
            ("C1", "1", "U1", "8"),  # Assuming pin 8 exists
        ]

        for from_comp, from_pin, to_comp, to_pin in connections:
            result = await connect_func(
                project_path=project_file,
                from_component=from_comp,
                from_pin=from_pin,
                to_component=to_comp,
                to_pin=to_pin,
                ctx=mock_context,
            )
            # Connection might succeed or fail depending on component pins
            # Integration test focuses on workflow, not pin accuracy

        # Step 5: Validate circuit
        validate_func = mcp_server._tools["validate_circuit"].func
        result = await validate_func(project_path=project_file, ctx=mock_context)
        assert result["success"] is True
        validation = result["validation_results"]

        # Should have all components we added
        assert validation["component_count"] >= 8  # 3 power + 1 ESP32 + 3 resistors + 2 capacitors

        # Step 6: Extract netlist
        extract_netlist_func = mcp_server._tools["extract_schematic_netlist"].func
        schematic_file = f"{project_path}/{project_name}.kicad_sch"
        result = await extract_netlist_func(schematic_path=schematic_file, ctx=mock_context)
        assert result["success"] is True
        assert result["component_count"] >= 8
        assert "components" in result

        # Verify specific components
        components = result["components"]
        assert any("ESP32" in comp.get("lib_id", "") for comp in components)
        assert any("Device:R" in comp.get("lib_id", "") for comp in components)
        assert any("Device:C" in comp.get("lib_id", "") for comp in components)
        assert any("power:" in comp.get("lib_id", "") for comp in components)

        # Step 7: Export files (if available)
        if "export_gerbers" in mcp_server._tools:
            export_func = mcp_server._tools["export_gerbers"].func
            result = await export_func(
                project_path=project_file,
                output_directory=str(temp_dir / "gerbers"),
                ctx=mock_context,
            )
            # Export might succeed or fail depending on KiCad CLI availability

    @pytest.mark.asyncio
    async def test_project_discovery_and_analysis(
        self, mcp_server, mock_context, sample_kicad_project
    ):
        """Test project discovery and analysis workflow."""
        # Step 1: List projects in directory
        list_projects_func = mcp_server._tools["list_projects"].func
        project_dir = Path(sample_kicad_project["directory"]).parent

        result = await list_projects_func(search_directories=[str(project_dir)], ctx=mock_context)
        assert result["success"] is True
        assert len(result["projects"]) >= 1

        # Find our test project
        test_project = None
        for project in result["projects"]:
            if sample_kicad_project["name"] in project["name"]:
                test_project = project
                break

        assert test_project is not None

        # Step 2: Get project structure
        get_structure_func = mcp_server._tools["get_project_structure"].func
        result = await get_structure_func(
            project_path=sample_kicad_project["path"], ctx=mock_context
        )
        assert result["success"] is True
        assert "files" in result

        # Step 3: Extract netlist from existing project
        extract_netlist_func = mcp_server._tools["extract_schematic_netlist"].func
        result = await extract_netlist_func(
            schematic_path=sample_kicad_project["schematic"], ctx=mock_context
        )
        assert result["success"] is True

        # Step 4: Analyze netlist
        if result["component_count"] > 0:
            # Additional analysis could be done here
            assert "components" in result
            assert "nets" in result

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, mcp_server, mock_context, temp_dir):
        """Test workflow error handling and recovery."""
        project_name = "error_test_project"
        project_path = str(temp_dir / project_name)

        # Step 1: Create project successfully
        create_func = mcp_server._tools["create_new_circuit"].func
        result = await create_func(
            project_name=project_name,
            project_path=project_path,
            description="Error recovery test",
            ctx=mock_context,
        )
        assert result["success"] is True
        project_file = f"{project_path}/{project_name}.kicad_pro"

        # Step 2: Try to add invalid component
        add_component_func = mcp_server._tools["add_component_to_circuit"].func
        result = await add_component_func(
            project_path=project_file,
            component_type="NonExistent:InvalidComponent",
            reference="X1",
            value="Invalid",
            position_x=1000,
            position_y=1000,
            ctx=mock_context,
        )
        # Should handle error gracefully
        # (Success depends on implementation - might create generic component)

        # Step 3: Try to connect non-existent components
        connect_func = mcp_server._tools["connect_components"].func
        result = await connect_func(
            project_path=project_file,
            from_component="NonExistent1",
            from_pin="1",
            to_component="NonExistent2",
            to_pin="1",
            ctx=mock_context,
        )
        # Should fail gracefully
        assert result["success"] is False

        # Step 4: Validate project should still work
        validate_func = mcp_server._tools["validate_circuit"].func
        result = await validate_func(project_path=project_file, ctx=mock_context)
        assert result["success"] is True

        # Step 5: Extract netlist should still work
        extract_netlist_func = mcp_server._tools["extract_schematic_netlist"].func
        schematic_file = f"{project_path}/{project_name}.kicad_sch"
        result = await extract_netlist_func(schematic_path=schematic_file, ctx=mock_context)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_large_project_workflow(self, mcp_server, mock_context, temp_dir):
        """Test workflow with a larger project (performance test)."""
        project_name = "large_test_project"
        project_path = str(temp_dir / project_name)

        # Create project
        create_func = mcp_server._tools["create_new_circuit"].func
        result = await create_func(
            project_name=project_name,
            project_path=project_path,
            description="Large project test",
            ctx=mock_context,
        )
        assert result["success"] is True
        project_file = f"{project_path}/{project_name}.kicad_pro"

        # Add many components
        add_component_func = mcp_server._tools["add_component_to_circuit"].func

        import time

        start_time = time.time()

        # Add 50 components
        for i in range(50):
            result = await add_component_func(
                project_path=project_file,
                component_type="Device:R",
                reference=f"R{i + 1}",
                value=f"{(i + 1) * 100}",
                position_x=1000 + (i % 10) * 500,
                position_y=1000 + (i // 10) * 500,
                ctx=mock_context,
            )
            assert result["success"] is True

        component_time = time.time()

        # Extract netlist
        extract_netlist_func = mcp_server._tools["extract_schematic_netlist"].func
        schematic_file = f"{project_path}/{project_name}.kicad_sch"
        result = await extract_netlist_func(schematic_path=schematic_file, ctx=mock_context)
        assert result["success"] is True
        assert result["component_count"] >= 50

        end_time = time.time()

        # Performance assertions
        component_add_time = component_time - start_time
        netlist_extract_time = end_time - component_time
        total_time = end_time - start_time

        # Should complete within reasonable time
        assert component_add_time < 30.0  # 30 seconds for 50 components
        assert netlist_extract_time < 5.0  # 5 seconds for netlist extraction
        assert total_time < 35.0  # 35 seconds total

        print(
            f"Performance: {component_add_time:.2f}s for components, "
            f"{netlist_extract_time:.2f}s for netlist, "
            f"{total_time:.2f}s total"
        )

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, mcp_server, mock_context, temp_dir):
        """Test concurrent operations on different projects."""
        project_names = ["concurrent_1", "concurrent_2", "concurrent_3"]
        project_paths = [str(temp_dir / name) for name in project_names]

        # Create multiple projects concurrently
        create_func = mcp_server._tools["create_new_circuit"].func

        async def create_project(name, path):
            return await create_func(
                project_name=name,
                project_path=path,
                description=f"Concurrent test project {name}",
                ctx=mock_context,
            )

        # Run project creation concurrently
        results = await asyncio.gather(
            *[create_project(name, path) for name, path in zip(project_names, project_paths)]
        )

        # All should succeed
        for result in results:
            assert result["success"] is True

        # Add components to projects concurrently
        add_component_func = mcp_server._tools["add_component_to_circuit"].func

        async def add_components(project_path, project_name):
            tasks = []
            for i in range(5):
                task = add_component_func(
                    project_path=f"{project_path}/{project_name}.kicad_pro",
                    component_type="Device:R",
                    reference=f"R{i + 1}",
                    value="1k",
                    position_x=1000 + i * 200,
                    position_y=1000,
                    ctx=mock_context,
                )
                tasks.append(task)
            return await asyncio.gather(*tasks)

        # Add components to all projects concurrently
        component_results = await asyncio.gather(
            *[add_components(path, name) for name, path in zip(project_names, project_paths)]
        )

        # Verify all component additions succeeded
        for project_results in component_results:
            for result in project_results:
                assert result["success"] is True

        # Extract netlists concurrently
        extract_netlist_func = mcp_server._tools["extract_schematic_netlist"].func

        async def extract_netlist(project_path, project_name):
            return await extract_netlist_func(
                schematic_path=f"{project_path}/{project_name}.kicad_sch", ctx=mock_context
            )

        netlist_results = await asyncio.gather(
            *[extract_netlist(path, name) for name, path in zip(project_names, project_paths)]
        )

        # Verify all netlist extractions succeeded
        for result in netlist_results:
            assert result["success"] is True
            assert result["component_count"] >= 5
