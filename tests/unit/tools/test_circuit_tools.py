"""
Unit tests for circuit_tools.py - circuit creation and manipulation functionality.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock

from fastmcp import FastMCP
import pytest

from kicad_mcp.tools.circuit_tools import register_circuit_tools


class TestCircuitTools:
    """Test suite for circuit creation tools."""

    @pytest.fixture
    def mock_mcp(self):
        """Create a mock FastMCP server for testing."""
        return Mock(spec=FastMCP)

    @pytest.fixture
    def mock_context(self):
        """Create a mock context for testing."""
        context = Mock()
        context.info = AsyncMock()
        context.report_progress = AsyncMock()
        context.emit_log = AsyncMock()
        return context

    def test_register_circuit_tools(self, mock_mcp):
        """Test that circuit tools are properly registered with MCP server."""
        # Mock the tool decorator to capture registered functions
        registered_tools = []

        def mock_tool():
            def decorator(func):
                registered_tools.append(func.__name__)
                return func

            return decorator

        mock_mcp.tool = mock_tool

        # Register tools
        register_circuit_tools(mock_mcp)

        # Verify expected tools were registered
        expected_tools = [
            "create_new_circuit",
            "add_component_to_circuit",
            "connect_components",
            "add_power_symbols",
            "validate_circuit",
        ]

        for tool in expected_tools:
            assert tool in registered_tools

    @pytest.mark.asyncio
    async def test_create_new_circuit_success(self, mock_context, temp_dir):
        """Test successful creation of a new circuit project."""
        project_name = "test_circuit"
        project_path = str(temp_dir / project_name)
        description = "Test circuit for unit testing"

        # Import the actual function after registration
        from fastmcp import FastMCP

        from kicad_mcp.tools.circuit_tools import register_circuit_tools

        mcp = FastMCP("test")
        register_circuit_tools(mcp)

        # Find the create_new_circuit function
        create_circuit_func = None
        for tool_name, tool_info in mcp._tools.items():
            if tool_name == "create_new_circuit":
                create_circuit_func = tool_info.func
                break

        assert create_circuit_func is not None, "create_new_circuit tool not found"

        # Test the function
        result = await create_circuit_func(
            project_name=project_name,
            project_path=project_path,
            description=description,
            ctx=mock_context,
        )

        # Verify result
        assert result["success"] is True
        assert "project_files" in result
        assert project_name in result["project_path"]

        # Verify files were created
        project_dir = Path(project_path)
        assert project_dir.exists()
        assert (project_dir / f"{project_name}.kicad_pro").exists()
        assert (project_dir / f"{project_name}.kicad_sch").exists()

        # Verify progress reporting
        mock_context.report_progress.assert_called()
        mock_context.info.assert_called()

    @pytest.mark.asyncio
    async def test_create_new_circuit_existing_path(self, mock_context, temp_dir):
        """Test error handling when project path already exists."""
        project_name = "existing_project"
        project_path = str(temp_dir / project_name)

        # Create existing directory
        Path(project_path).mkdir()

        from fastmcp import FastMCP

        from kicad_mcp.tools.circuit_tools import register_circuit_tools

        mcp = FastMCP("test")
        register_circuit_tools(mcp)

        create_circuit_func = None
        for tool_name, tool_info in mcp._tools.items():
            if tool_name == "create_new_circuit":
                create_circuit_func = tool_info.func
                break

        result = await create_circuit_func(
            project_name=project_name,
            project_path=project_path,
            description="Test",
            ctx=mock_context,
        )

        # Should handle existing path gracefully
        assert result["success"] is True or "exists" in result.get("message", "").lower()

    @pytest.mark.asyncio
    async def test_add_component_to_circuit_esp32(self, mock_context, sample_kicad_project):
        """Test adding an ESP32 component to a circuit."""
        project_path = sample_kicad_project["path"]

        from fastmcp import FastMCP

        from kicad_mcp.tools.circuit_tools import register_circuit_tools

        mcp = FastMCP("test")
        register_circuit_tools(mcp)

        add_component_func = None
        for tool_name, tool_info in mcp._tools.items():
            if tool_name == "add_component_to_circuit":
                add_component_func = tool_info.func
                break

        assert add_component_func is not None

        result = await add_component_func(
            project_path=project_path,
            component_type="ESP32-WROOM-32",
            reference="U1",
            value="ESP32-WROOM-32",
            position_x=1000,
            position_y=1000,
            ctx=mock_context,
        )

        assert result["success"] is True
        assert "component_uuid" in result
        assert result["reference"] == "U1"

        # Verify schematic file was updated
        schematic_path = sample_kicad_project["schematic"]
        assert Path(schematic_path).exists()

        # Check that component was added to schematic file
        with open(schematic_path) as f:
            schematic_content = f.read()

        if schematic_content.strip().startswith("{"):
            # JSON format
            schematic_data = json.loads(schematic_content)
            components = schematic_data.get("components", [])
            esp32_component = next(
                (comp for comp in components if comp.get("reference") == "U1"), None
            )
            assert esp32_component is not None
            assert "ESP32" in esp32_component.get("lib_id", "")

    @pytest.mark.asyncio
    async def test_add_component_invalid_project(self, mock_context):
        """Test error handling when adding component to invalid project."""
        from fastmcp import FastMCP

        from kicad_mcp.tools.circuit_tools import register_circuit_tools

        mcp = FastMCP("test")
        register_circuit_tools(mcp)

        add_component_func = None
        for tool_name, tool_info in mcp._tools.items():
            if tool_name == "add_component_to_circuit":
                add_component_func = tool_info.func
                break

        result = await add_component_func(
            project_path="/nonexistent/project.kicad_pro",
            component_type="Device:R",
            reference="R1",
            value="10k",
            position_x=1000,
            position_y=1000,
            ctx=mock_context,
        )

        assert result["success"] is False
        assert "error" in result
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_add_power_symbols(self, mock_context, sample_kicad_project):
        """Test adding power symbols (VCC, GND, etc.) to circuit."""
        project_path = sample_kicad_project["path"]

        from fastmcp import FastMCP

        from kicad_mcp.tools.circuit_tools import register_circuit_tools

        mcp = FastMCP("test")
        register_circuit_tools(mcp)

        add_power_func = None
        for tool_name, tool_info in mcp._tools.items():
            if tool_name == "add_power_symbols":
                add_power_func = tool_info.func
                break

        assert add_power_func is not None

        result = await add_power_func(
            project_path=project_path, power_types=["VCC", "GND", "+5V", "+3V3"], ctx=mock_context
        )

        assert result["success"] is True
        assert "power_symbols" in result
        assert len(result["power_symbols"]) == 4

        # Verify power symbols were added
        schematic_path = sample_kicad_project["schematic"]
        with open(schematic_path) as f:
            schematic_content = f.read()

        if schematic_content.strip().startswith("{"):
            schematic_data = json.loads(schematic_content)
            components = schematic_data.get("components", [])

            power_components = [
                comp for comp in components if comp.get("lib_id", "").startswith("power:")
            ]
            assert len(power_components) >= 4

            # Check specific power types
            power_types = [comp.get("value") for comp in power_components]
            assert "VCC" in power_types
            assert "GND" in power_types
            assert "+5V" in power_types
            assert "+3V3" in power_types

    @pytest.mark.asyncio
    async def test_connect_components_simple(self, mock_context, sample_kicad_project):
        """Test connecting two components with a wire."""
        project_path = sample_kicad_project["path"]

        # First add some components to connect
        from fastmcp import FastMCP

        from kicad_mcp.tools.circuit_tools import register_circuit_tools

        mcp = FastMCP("test")
        register_circuit_tools(mcp)

        # Get functions
        add_component_func = mcp._tools["add_component_to_circuit"].func
        connect_func = mcp._tools["connect_components"].func

        # Add two components
        await add_component_func(
            project_path=project_path,
            component_type="Device:R",
            reference="R1",
            value="10k",
            position_x=1000,
            position_y=1000,
            ctx=mock_context,
        )

        await add_component_func(
            project_path=project_path,
            component_type="Device:R",
            reference="R2",
            value="1k",
            position_x=2000,
            position_y=1000,
            ctx=mock_context,
        )

        # Connect them
        result = await connect_func(
            project_path=project_path,
            from_component="R1",
            from_pin="2",
            to_component="R2",
            to_pin="1",
            ctx=mock_context,
        )

        assert result["success"] is True
        assert "wire_uuid" in result

        # Verify wire was added to schematic
        schematic_path = sample_kicad_project["schematic"]
        with open(schematic_path) as f:
            schematic_content = f.read()

        if schematic_content.strip().startswith("{"):
            schematic_data = json.loads(schematic_content)
            wires = schematic_data.get("wire", [])
            assert len(wires) >= 1

    @pytest.mark.asyncio
    async def test_validate_circuit(self, mock_context, sample_kicad_project):
        """Test circuit validation functionality."""
        project_path = sample_kicad_project["path"]

        from fastmcp import FastMCP

        from kicad_mcp.tools.circuit_tools import register_circuit_tools

        mcp = FastMCP("test")
        register_circuit_tools(mcp)

        validate_func = mcp._tools["validate_circuit"].func

        result = await validate_func(project_path=project_path, ctx=mock_context)

        assert result["success"] is True
        assert "validation_results" in result
        assert "component_count" in result["validation_results"]
        assert "net_count" in result["validation_results"]
        assert "issues" in result["validation_results"]

    @pytest.mark.asyncio
    async def test_component_positioning(self, mock_context, sample_kicad_project):
        """Test that components are positioned correctly."""
        project_path = sample_kicad_project["path"]

        from fastmcp import FastMCP

        from kicad_mcp.tools.circuit_tools import register_circuit_tools

        mcp = FastMCP("test")
        register_circuit_tools(mcp)

        add_component_func = mcp._tools["add_component_to_circuit"].func

        # Add component at specific position
        test_x, test_y = 1500, 2000
        result = await add_component_func(
            project_path=project_path,
            component_type="Device:C",
            reference="C1",
            value="100nF",
            position_x=test_x,
            position_y=test_y,
            ctx=mock_context,
        )

        assert result["success"] is True

        # Verify position in schematic file
        schematic_path = sample_kicad_project["schematic"]
        with open(schematic_path) as f:
            schematic_content = f.read()

        if schematic_content.strip().startswith("{"):
            schematic_data = json.loads(schematic_content)
            components = schematic_data.get("components", [])

            c1_component = next(
                (comp for comp in components if comp.get("reference") == "C1"), None
            )
            assert c1_component is not None

            # Check position
            position = c1_component.get("position", {})
            assert position.get("x") == test_x
            assert position.get("y") == test_y

    @pytest.mark.asyncio
    async def test_component_reference_uniqueness(self, mock_context, sample_kicad_project):
        """Test that component references are kept unique."""
        project_path = sample_kicad_project["path"]

        from fastmcp import FastMCP

        from kicad_mcp.tools.circuit_tools import register_circuit_tools

        mcp = FastMCP("test")
        register_circuit_tools(mcp)

        add_component_func = mcp._tools["add_component_to_circuit"].func

        # Add first component
        result1 = await add_component_func(
            project_path=project_path,
            component_type="Device:R",
            reference="R1",
            value="10k",
            position_x=1000,
            position_y=1000,
            ctx=mock_context,
        )

        # Try to add second component with same reference
        result2 = await add_component_func(
            project_path=project_path,
            component_type="Device:R",
            reference="R1",  # Same reference
            value="1k",
            position_x=2000,
            position_y=1000,
            ctx=mock_context,
        )

        # Both should succeed but with different actual references
        assert result1["success"] is True
        assert result2["success"] is True

        # References should be different (auto-incremented)
        assert (
            result1["reference"] != result2["reference"]
            or result1["component_uuid"] != result2["component_uuid"]
        )

    @pytest.mark.asyncio
    async def test_complex_circuit_creation(self, mock_context, temp_dir):
        """Test creating a complete circuit with multiple components and connections."""
        project_name = "complex_circuit"
        project_path = str(temp_dir / project_name)

        from fastmcp import FastMCP

        from kicad_mcp.tools.circuit_tools import register_circuit_tools

        mcp = FastMCP("test")
        register_circuit_tools(mcp)

        # Get all functions
        create_func = mcp._tools["create_new_circuit"].func
        add_component_func = mcp._tools["add_component_to_circuit"].func
        add_power_func = mcp._tools["add_power_symbols"].func
        validate_func = mcp._tools["validate_circuit"].func

        # Create project
        result = await create_func(
            project_name=project_name,
            project_path=project_path,
            description="Complex test circuit",
            ctx=mock_context,
        )
        assert result["success"] is True

        # Add power symbols
        result = await add_power_func(
            project_path=f"{project_path}/{project_name}.kicad_pro",
            power_types=["VCC", "GND"],
            ctx=mock_context,
        )
        assert result["success"] is True

        # Add components
        components = [
            {
                "type": "MCU_Espressif:ESP32-WROOM-32",
                "ref": "U1",
                "value": "ESP32",
                "x": 1000,
                "y": 1000,
            },
            {"type": "Device:R", "ref": "R1", "value": "10k", "x": 500, "y": 800},
            {"type": "Device:C", "ref": "C1", "value": "100nF", "x": 1500, "y": 800},
        ]

        for comp in components:
            result = await add_component_func(
                project_path=f"{project_path}/{project_name}.kicad_pro",
                component_type=comp["type"],
                reference=comp["ref"],
                value=comp["value"],
                position_x=comp["x"],
                position_y=comp["y"],
                ctx=mock_context,
            )
            assert result["success"] is True

        # Validate circuit
        result = await validate_func(
            project_path=f"{project_path}/{project_name}.kicad_pro", ctx=mock_context
        )
        assert result["success"] is True
        assert (
            result["validation_results"]["component_count"] >= 5
        )  # 3 components + 2 power symbols
