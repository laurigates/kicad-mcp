#!/usr/bin/env python3
"""
Example demonstrating text-to-schematic conversion in KiCad MCP.

This example shows how to:
1. Create circuits from YAML descriptions
2. Generate native KiCad schematic files
3. Validate circuit descriptions
4. Use templates for common circuits
"""

import asyncio
import os
import tempfile
import json
from pathlib import Path

# Import the text-to-schematic tools
from kicad_mcp.tools.text_to_schematic import (
    TextToSchematicParser,
    register_text_to_schematic_tools
)
from kicad_mcp.utils.sexpr_generator import SExpressionGenerator


async def create_sample_project(project_dir: str) -> str:
    """Create a sample KiCad project for testing."""
    project_name = "text_to_schematic_demo"
    project_file = os.path.join(project_dir, f"{project_name}.kicad_pro")
    schematic_file = os.path.join(project_dir, f"{project_name}.kicad_sch")
    
    # Create basic project file
    project_data = {
        "meta": {"filename": f"{project_name}.kicad_pro", "version": 1},
        "sheets": [["uuid-placeholder", ""]]
    }
    
    with open(project_file, 'w') as f:
        json.dump(project_data, f, indent=2)
    
    # Create basic schematic file
    schematic_data = {
        "version": 20230121,
        "generator": "kicad-mcp-example",
        "uuid": "demo-uuid-1234",
        "paper": "A4",
        "symbol": [],
        "wire": []
    }
    
    with open(schematic_file, 'w') as f:
        json.dump(schematic_data, f, indent=2)
    
    print(f"✓ Created sample project: {project_file}")
    return project_file


def demonstrate_parser():
    """Demonstrate the text-to-schematic parser functionality."""
    print("\n" + "="*60)
    print("PARSER DEMONSTRATION")
    print("="*60)
    
    parser = TextToSchematicParser()
    
    # Example 1: LED Blinker Circuit
    print("\n1. LED Blinker Circuit (YAML format):")
    led_blinker_yaml = '''
circuit "LED Blinker":
  components:
    - R1: resistor 220Ω at (20, 30)
    - LED1: led red at (50, 30)
    - C1: capacitor 100µF at (20, 60)
    - U1: ic 555 at (80, 45)
  power:
    - VCC: +5V at (20, 10)
    - GND: GND at (20, 80)
  connections:
    - VCC → R1.1
    - R1.2 → LED1.anode
    - LED1.cathode → GND
    - VCC → U1.8
    - U1.1 → GND
'''
    
    print("YAML Input:")
    print(led_blinker_yaml)
    
    circuit = parser.parse_yaml_circuit(led_blinker_yaml)
    print(f"\nParsed Circuit: {circuit.name}")
    print(f"Components: {len(circuit.components)}")
    print(f"Power Symbols: {len(circuit.power_symbols)}")
    print(f"Connections: {len(circuit.connections)}")
    
    for i, comp in enumerate(circuit.components):
        print(f"  Component {i+1}: {comp.reference} = {comp.component_type} {comp.value} at {comp.position}")
    
    for i, power in enumerate(circuit.power_symbols):
        print(f"  Power {i+1}: {power.reference} = {power.power_type} at {power.position}")
    
    # Example 2: Simple Text Format
    print("\n2. Voltage Divider (Simple text format):")
    voltage_divider_text = '''
circuit: Voltage Divider
components:
R1 resistor 10kΩ (30, 20)
R2 resistor 10kΩ (30, 50)
power:
VIN +5V (30, 10)
GND GND (30, 70)
connections:
VIN -> R1.1
R1.2 -> R2.1
R2.2 -> GND
'''
    
    print("Simple Text Input:")
    print(voltage_divider_text)
    
    circuit2 = parser.parse_simple_text(voltage_divider_text)
    print(f"\nParsed Circuit: {circuit2.name}")
    print(f"Components: {len(circuit2.components)}")
    print(f"Power Symbols: {len(circuit2.power_symbols)}")
    print(f"Connections: {len(circuit2.connections)}")
    
    return circuit, circuit2


def demonstrate_sexpr_generation():
    """Demonstrate S-expression file generation."""
    print("\n" + "="*60)
    print("S-EXPRESSION GENERATION DEMONSTRATION")
    print("="*60)
    
    parser = TextToSchematicParser()
    generator = SExpressionGenerator()
    
    # Simple RC filter circuit
    rc_filter_yaml = '''
circuit "RC Low-Pass Filter":
  components:
    - R1: resistor 1kΩ at (30, 30)
    - C1: capacitor 100nF at (60, 40)
  power:
    - GND: GND at (60, 60)
  connections:
    - R1.2 → C1.1
    - C1.2 → GND
'''
    
    print("Input Circuit Description:")
    print(rc_filter_yaml)
    
    circuit = parser.parse_yaml_circuit(rc_filter_yaml)
    
    # Convert to dictionaries for the generator
    components_dict = []
    for comp in circuit.components:
        components_dict.append({
            'reference': comp.reference,
            'value': comp.value,
            'position': comp.position,
            'symbol_library': comp.symbol_library,
            'symbol_name': comp.symbol_name
        })
    
    power_symbols_dict = []
    for power in circuit.power_symbols:
        power_symbols_dict.append({
            'reference': power.reference,
            'power_type': power.power_type,
            'position': power.position
        })
    
    connections_dict = []
    for conn in circuit.connections:
        connections_dict.append({
            'start_component': conn.start_component,
            'start_pin': conn.start_pin,
            'end_component': conn.end_component,
            'end_pin': conn.end_pin
        })
    
    # Generate S-expression
    sexpr_content = generator.generate_schematic(
        circuit.name,
        components_dict,
        power_symbols_dict,
        connections_dict
    )
    
    print("\nGenerated KiCad S-Expression (.kicad_sch):")
    print("-" * 40)
    # Show first 50 lines to avoid overwhelming output
    lines = sexpr_content.split('\n')
    for i, line in enumerate(lines[:50]):
        print(f"{i+1:3d}: {line}")
    
    if len(lines) > 50:
        print(f"... ({len(lines) - 50} more lines)")
    
    return sexpr_content


def demonstrate_templates():
    """Demonstrate template functionality."""
    print("\n" + "="*60)
    print("TEMPLATE DEMONSTRATION")
    print("="*60)
    
    templates = {
        "led_blinker": '''
circuit "LED Blinker":
  components:
    - R1: resistor 220Ω at (10, 20)
    - LED1: led red at (30, 20)
    - C1: capacitor 100µF at (10, 40)
    - U1: ic 555 at (50, 30)
  power:
    - VCC: +5V at (10, 10)
    - GND: GND at (10, 50)
  connections:
    - VCC → R1.1
    - R1.2 → LED1.anode
    - LED1.cathode → GND
''',
        "voltage_divider": '''
circuit "Voltage Divider":
  components:
    - R1: resistor 10kΩ at (20, 20)
    - R2: resistor 10kΩ at (20, 40)
  power:
    - VIN: +5V at (20, 10)
    - GND: GND at (20, 60)
  connections:
    - VIN → R1.1
    - R1.2 → R2.1
    - R2.2 → GND
''',
        "rc_filter": '''
circuit "RC Low-Pass Filter":
  components:
    - R1: resistor 1kΩ at (20, 20)
    - C1: capacitor 100nF at (40, 30)
  power:
    - GND: GND at (40, 50)
  connections:
    - R1.2 → C1.1
    - C1.2 → GND
'''
    }
    
    parser = TextToSchematicParser()
    
    print("Available Templates:")
    for name, description in templates.items():
        print(f"\n{name.upper()}")
        print("-" * len(name))
        print(description.strip())
        
        # Parse and validate template
        circuit = parser.parse_yaml_circuit(description)
        print(f"✓ Template parses successfully: {circuit.name}")
        print(f"  - {len(circuit.components)} components")
        print(f"  - {len(circuit.power_symbols)} power symbols")
        print(f"  - {len(circuit.connections)} connections")


async def demonstrate_integration():
    """Demonstrate full integration with file generation."""
    print("\n" + "="*60)
    print("INTEGRATION DEMONSTRATION")
    print("="*60)
    
    # Create a temporary directory for the demo
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Working in temporary directory: {temp_dir}")
        
        # Create sample project
        project_file = await create_sample_project(temp_dir)
        
        parser = TextToSchematicParser()
        generator = SExpressionGenerator()
        
        # Create a complete circuit
        amplifier_circuit = '''
circuit "Simple Amplifier":
  components:
    - R1: resistor 10kΩ at (20, 30)
    - R2: resistor 1kΩ at (60, 30)
    - C1: capacitor 10µF at (20, 60)
    - C2: capacitor 10µF at (60, 60)
    - Q1: transistor_npn 2N2222 at (40, 45)
  power:
    - VCC: +9V at (20, 10)
    - GND: GND at (20, 80)
  connections:
    - VCC → R1.1
    - R1.2 → Q1.base
    - Q1.collector → R2.1
    - R2.2 → VCC
    - Q1.emitter → GND
'''
        
        print("\nCreating amplifier circuit...")
        print(amplifier_circuit)
        
        # Parse circuit
        circuit = parser.parse_yaml_circuit(amplifier_circuit)
        print(f"✓ Parsed: {circuit.name}")
        
        # Convert to S-expression format
        components_dict = [
            {
                'reference': comp.reference,
                'value': comp.value,
                'position': comp.position,
                'symbol_library': comp.symbol_library,
                'symbol_name': comp.symbol_name
            }
            for comp in circuit.components
        ]
        
        power_symbols_dict = [
            {
                'reference': power.reference,
                'power_type': power.power_type,
                'position': power.position
            }
            for power in circuit.power_symbols
        ]
        
        connections_dict = [
            {
                'start_component': conn.start_component,
                'start_pin': conn.start_pin,
                'end_component': conn.end_component,
                'end_pin': conn.end_pin
            }
            for conn in circuit.connections
        ]
        
        sexpr_content = generator.generate_schematic(
            circuit.name,
            components_dict,
            power_symbols_dict,
            connections_dict
        )
        
        # Write to schematic file
        schematic_file = os.path.join(temp_dir, "text_to_schematic_demo.kicad_sch")
        with open(schematic_file, 'w') as f:
            f.write(sexpr_content)
        
        print(f"✓ Generated KiCad schematic: {schematic_file}")
        
        # Verify file size and content
        file_size = os.path.getsize(schematic_file)
        print(f"✓ File size: {file_size} bytes")
        
        # Show file content summary
        with open(schematic_file, 'r') as f:
            lines = f.readlines()
            print(f"✓ File contains {len(lines)} lines")
            print(f"✓ First line: {lines[0].strip()}")
            print(f"✓ Last line: {lines[-1].strip()}")
        
        print(f"\n📁 Files created in {temp_dir}:")
        for file in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, file)
            size = os.path.getsize(file_path)
            print(f"  - {file} ({size} bytes)")
        
        print("\n✅ Integration demonstration complete!")
        print("The generated files are KiCad-compatible and can be opened in KiCad.")


def print_summary():
    """Print a summary of the text-to-schematic feature."""
    print("\n" + "="*60)
    print("TEXT-TO-SCHEMATIC FEATURE SUMMARY")
    print("="*60)
    
    print("""
🎯 WHAT WE'VE BUILT:
   A MermaidJS-inspired text-to-schematic conversion system for KiCad

🔧 KEY FEATURES:
   ✓ YAML and simple text circuit descriptions
   ✓ Support for common electronic components
   ✓ Power symbol integration
   ✓ Connection specification with pin mapping
   ✓ Native KiCad S-expression file generation
   ✓ Circuit validation and error checking
   ✓ Built-in templates for common circuits
   ✓ Comprehensive test suite

📝 SUPPORTED COMPONENTS:
   • Resistors, Capacitors, Inductors
   • LEDs, Diodes
   • Transistors (NPN/PNP)
   • ICs, Switches, Connectors
   • Power symbols (VCC, GND, +5V, +3V3, etc.)

🚀 USAGE:
   1. Write circuit description in YAML or text format
   2. Use MCP tools to parse and validate
   3. Generate native KiCad schematic files
   4. Open directly in KiCad application

🔗 INTEGRATION:
   • Seamlessly integrates with existing KiCad MCP tools
   • Compatible with DRC, BOM, netlist, and export functions
   • Follows KiCad S-expression standards

📚 EXAMPLES:
   • LED blinker circuits
   • Voltage dividers  
   • RC filters
   • Amplifier circuits
   
🎉 RESULT: 
   You can now create KiCad schematics as easily as writing Markdown!
""")


async def main():
    """Main demonstration function."""
    print("🔌 KiCad MCP Text-to-Schematic Demonstration")
    print("=" * 60)
    
    try:
        # Run all demonstrations
        demonstrate_parser()
        demonstrate_sexpr_generation()
        demonstrate_templates()
        await demonstrate_integration()
        print_summary()
        
        print("\n🎉 All demonstrations completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during demonstration: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    # Run the demonstration
    exit_code = asyncio.run(main())
    exit(exit_code)