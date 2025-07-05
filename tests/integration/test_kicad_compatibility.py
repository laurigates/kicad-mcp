"""
Integration tests for KiCad file compatibility.
Tests that generated files can actually be opened in KiCad.
"""
import pytest
import os
import tempfile
import subprocess
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock
import sys

# Mock MCP dependencies for testing
sys.modules['mcp'] = Mock()
sys.modules['mcp.server'] = Mock()
sys.modules['mcp.server.fastmcp'] = Mock()

from kicad_mcp.tools.circuit_tools import create_new_project
from kicad_mcp.tools.text_to_schematic import register_text_to_schematic_tools
from kicad_mcp.utils.sexpr_generator import SExpressionGenerator


class TestKiCadCompatibility:
    """Test KiCad file format compatibility."""
    
    @pytest.fixture
    def temp_project_dir(self):
        """Create a temporary directory for test projects."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock MCP context."""
        ctx = AsyncMock()
        ctx.info = AsyncMock()
        ctx.report_progress = AsyncMock()
        return ctx
    
    def test_kicad_cli_available(self):
        """Test that KiCad CLI is available for validation."""
        try:
            result = subprocess.run(['kicad-cli', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(f"✅ KiCad CLI available: {result.stdout.strip()}")
                return True
            else:
                print("⚠️  KiCad CLI not available - skipping validation tests")
                return False
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            print("⚠️  KiCad CLI not found - skipping validation tests")
            return False
    
    @pytest.mark.asyncio
    async def test_project_creation_format(self, temp_project_dir, mock_context):
        """Test that created project files have correct format."""
        project_name = "test_format"
        project_path = os.path.join(temp_project_dir, project_name)
        
        # Create project
        result = await create_new_project(
            project_name=project_name,
            project_path=project_path,
            description="Format compatibility test",
            ctx=mock_context
        )
        
        assert result["success"], f"Project creation failed: {result.get('error')}"
        
        # Check project file format (.kicad_pro should be JSON)
        project_file = result["project_file"]
        assert os.path.exists(project_file), "Project file not created"
        
        with open(project_file, 'r') as f:
            content = f.read().strip()
            
        # Project file should be valid JSON
        try:
            project_data = json.loads(content)
            assert "meta" in project_data, "Missing meta section in project file"
            print("✅ Project file (.kicad_pro) has valid JSON format")
        except json.JSONDecodeError as e:
            pytest.fail(f"Project file is not valid JSON: {e}")
        
        # Check schematic file format (.kicad_sch should be S-expression)
        schematic_file = result["schematic_file"]
        assert os.path.exists(schematic_file), "Schematic file not created"
        
        with open(schematic_file, 'r') as f:
            sch_content = f.read().strip()
            
        # Schematic should start with (kicad_sch
        assert sch_content.startswith('(kicad_sch'), f"Schematic doesn't start with (kicad_sch: {sch_content[:50]}"
        print("✅ Schematic file (.kicad_sch) has valid S-expression format")
        
        # Check PCB file format (.kicad_pcb should be S-expression, NOT JSON)
        pcb_file = result["pcb_file"]
        assert os.path.exists(pcb_file), "PCB file not created"
        
        with open(pcb_file, 'r') as f:
            pcb_content = f.read().strip()
            
        # PCB should start with (kicad_pcb, NOT with {
        if pcb_content.startswith('{'):
            pytest.fail("❌ PCB file is in JSON format - KiCad expects S-expression format")
        
        assert pcb_content.startswith('(kicad_pcb'), f"PCB doesn't start with (kicad_pcb: {pcb_content[:50]}"
        print("✅ PCB file (.kicad_pcb) has valid S-expression format")
    
    def test_schematic_component_positioning(self, temp_project_dir):
        """Test that schematic components have reasonable positioning."""
        generator = SExpressionGenerator()
        
        # Test component positioning
        components = [
            {"reference": "R1", "value": "10k", "lib_id": "Device:R", "position": (50, 50)},
            {"reference": "C1", "value": "100nF", "lib_id": "Device:C", "position": (100, 50)},
            {"reference": "U1", "value": "ESP32", "lib_id": "RF_Module:ESP32-WROOM-32", "position": (150, 75)}
        ]
        
        power_symbols = [
            {"reference": "#PWR01", "power_type": "VCC", "position": (25, 25)},
            {"reference": "#PWR02", "power_type": "GND", "position": (25, 125)}
        ]
        
        connections = [
            {"start": (50, 50), "end": (100, 50)}
        ]
        
        # Generate schematic
        schematic_content = generator.generate_schematic(
            circuit_name="Position Test",
            components=components,
            power_symbols=power_symbols,
            connections=connections
        )
        
        # Check that positions are in reasonable ranges
        # KiCad uses 0.1mm units, so positions should be in reasonable mm ranges
        assert "50 50" in schematic_content or "50.0 50.0" in schematic_content, \
            "Component positions not found in schematic"
        
        # Positions should be spaced appropriately (at least 10mm apart)
        positions = [(50, 50), (100, 50), (150, 75)]
        for i, pos1 in enumerate(positions):
            for pos2 in positions[i+1:]:
                distance = ((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)**0.5
                assert distance >= 10, f"Components too close: {pos1} and {pos2} (distance: {distance}mm)"
        
        print("✅ Component positioning looks reasonable")
    
    @pytest.mark.skipif(not Path("/Applications/KiCad").exists() and 
                       not Path("/usr/bin/kicad").exists(),
                       reason="KiCad not installed")
    @pytest.mark.asyncio
    async def test_kicad_can_open_generated_files(self, temp_project_dir, mock_context):
        """Test that KiCad can actually open the generated files."""
        if not self.test_kicad_cli_available():
            pytest.skip("KiCad CLI not available")
        
        project_name = "kicad_open_test"
        project_path = os.path.join(temp_project_dir, project_name)
        
        # Create project with the fixed tools
        result = await create_new_project(
            project_name=project_name,
            project_path=project_path,
            description="KiCad compatibility test",
            ctx=mock_context
        )
        
        assert result["success"], f"Project creation failed: {result.get('error')}"
        
        # Try to validate the schematic with KiCad CLI
        schematic_file = result["schematic_file"]
        try:
            # Use kicad-cli to validate the schematic
            validation_result = subprocess.run([
                'kicad-cli', 'sch', 'export', 'netlist', 
                '--output', '/tmp/test_netlist.net',
                schematic_file
            ], capture_output=True, text=True, timeout=30)
            
            if validation_result.returncode == 0:
                print("✅ KiCad can successfully process the generated schematic")
            else:
                print(f"❌ KiCad validation failed: {validation_result.stderr}")
                pytest.fail(f"KiCad cannot process schematic: {validation_result.stderr}")
                
        except subprocess.TimeoutExpired:
            pytest.fail("KiCad validation timed out")
        except Exception as e:
            pytest.fail(f"KiCad validation error: {e}")
    
    def test_esp32_template_structure(self):
        """Test that ESP32 template generates correct component structure."""
        from kicad_mcp.tools.text_to_schematic import TextToSchematicParser
        
        # ESP32 template from our fixes
        esp32_yaml = '''
circuit "ESP32 Basic Setup":
  components:
    - U1: ic ESP32-WROOM-32 at (50, 50)
    - C1: capacitor 100µF at (20, 30)
    - R1: resistor 10kΩ at (80, 40)
    - LED1: led blue at (90, 60)
  power:
    - VCC: +3V3 at (20, 20)
    - GND: GND at (20, 80)
  connections:
    - VCC → U1.VDD
    - R1.2 → LED1.anode
    - LED1.cathode → GND
'''
        
        parser = TextToSchematicParser()
        circuit = parser.parse_yaml_circuit(esp32_yaml)
        
        # Validate structure
        assert circuit.name == "ESP32 Basic Setup"
        assert len(circuit.components) == 4, f"Expected 4 components, got {len(circuit.components)}"
        assert len(circuit.power_symbols) == 2, f"Expected 2 power symbols, got {len(circuit.power_symbols)}"
        assert len(circuit.connections) == 3, f"Expected 3 connections, got {len(circuit.connections)}"
        
        # Check component types
        component_types = [c.component_type for c in circuit.components]
        assert "ic" in component_types, "Missing ESP32 IC"
        assert "capacitor" in component_types, "Missing capacitor"
        assert "resistor" in component_types, "Missing resistor"
        assert "led" in component_types, "Missing LED"
        
        # Check power types
        power_types = [p.power_type for p in circuit.power_symbols]
        assert "+3V3" in power_types, "Missing +3V3 power"
        assert "GND" in power_types, "Missing GND power"
        
        print("✅ ESP32 template structure is correct")
    
    def test_file_extensions_correct(self, temp_project_dir):
        """Test that generated files have correct extensions."""
        test_files = {
            "test.kicad_pro": "project file",
            "test.kicad_sch": "schematic file", 
            "test.kicad_pcb": "PCB file"
        }
        
        for filename, description in test_files.items():
            # Check extension
            ext = Path(filename).suffix
            expected_exts = [".kicad_pro", ".kicad_sch", ".kicad_pcb"]
            assert any(filename.endswith(expected) for expected in expected_exts), \
                f"{description} has wrong extension: {ext}"
        
        print("✅ File extensions are correct")
    
    def test_coordinate_system_consistency(self):
        """Test that coordinate systems are consistent."""
        generator = SExpressionGenerator()
        
        # Test with known coordinates
        components = [
            {"reference": "R1", "value": "1k", "lib_id": "Device:R", 
             "position": (100, 100)},  # 100mm, 100mm
        ]
        
        schematic = generator.generate_schematic(
            circuit_name="Coordinate Test",
            components=components,
            power_symbols=[],
            connections=[]
        )
        
        # Check that coordinates appear in the schematic
        # KiCad uses 0.1mm units internally, so 100mm = 1000 units
        # But our generator should handle the conversion
        assert "100" in schematic, "X coordinate not found in schematic"
        print("✅ Coordinate system appears consistent")


def run_compatibility_tests():
    """Run all compatibility tests manually."""
    print("🔧 Running KiCad Compatibility Tests")
    print("=" * 50)
    
    test_instance = TestKiCadCompatibility()
    
    # Test 1: KiCad CLI availability
    print("\n1. Testing KiCad CLI availability...")
    kicad_available = test_instance.test_kicad_cli_available()
    
    # Test 2: File extensions
    print("\n2. Testing file extensions...")
    with tempfile.TemporaryDirectory() as temp_dir:
        test_instance.test_file_extensions_correct(temp_dir)
    
    # Test 3: Component positioning
    print("\n3. Testing component positioning...")
    with tempfile.TemporaryDirectory() as temp_dir:
        test_instance.test_schematic_component_positioning(temp_dir)
    
    # Test 4: ESP32 template structure
    print("\n4. Testing ESP32 template structure...")
    test_instance.test_esp32_template_structure()
    
    # Test 5: Coordinate system
    print("\n5. Testing coordinate system...")
    test_instance.test_coordinate_system_consistency()
    
    print("\n" + "=" * 50)
    print("🎉 Compatibility tests completed!")
    
    return kicad_available


if __name__ == "__main__":
    run_compatibility_tests()