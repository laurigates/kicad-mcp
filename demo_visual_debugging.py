#!/usr/bin/env python3
"""
Demo script showing how the visual rendering system helps debug
component positioning and wire connectivity issues.
"""
import os
import asyncio
from unittest.mock import AsyncMock

async def demo_visual_debugging():
    """Demonstrate visual debugging capabilities."""
    print("🎬 Visual Debugging Demo for KiCad MCP")
    print("=" * 45)
    
    # Test schematic that we generated earlier
    test_schematic = "tests/visual_output/test_circuit.kicad_sch"
    
    if not os.path.exists(test_schematic):
        print("❌ Test schematic not found. Run test_visualization_standalone.py first.")
        return
    
    print(f"📁 Using test schematic: {test_schematic}")
    
    # Demonstrate the issues we're solving
    print("\n🔍 Issues this system helps debug:")
    print("   • Issue #3: Components positioned outside schematic boundaries")
    print("   • Issue #4: Components not connected to each other with wires")
    print("   • Visual verification that circuits look correct")
    
    # Show both rendering approaches
    print("\n🖼️  Available Rendering Methods:")
    
    # Method 1: KiCad CLI (if available)
    kicad_svg = "tests/visual_output/test_circuit.svg"
    if os.path.exists(kicad_svg):
        print(f"   ✅ KiCad CLI SVG: {kicad_svg}")
        print("      → High-quality, KiCad-native rendering")
        print("      → Shows exact component symbols and positioning")
    else:
        print("   ⚠️  KiCad CLI SVG not available")
    
    # Method 2: Mock renderer (always available)
    mock_svg = "tests/visual_output/test_circuit_mock.svg"
    if os.path.exists(mock_svg):
        print(f"   ✅ Mock Renderer SVG: {mock_svg}")
        print("      → Development-friendly fallback rendering")
        print("      → Works without KiCad installation")
    else:
        print("   ⚠️  Mock renderer SVG not available")
    
    # Demonstrate component positioning analysis
    print("\n📊 Component Positioning Analysis:")
    
    try:
        from kicad_mcp.utils.mock_renderer import MockSchematicRenderer
        
        renderer = MockSchematicRenderer()
        schematic_data = renderer.parse_schematic_components(test_schematic)
        
        print(f"   Circuit: {schematic_data['title']}")
        print(f"   Components found: {len(schematic_data['components'])}")
        print(f"   Power symbols: {len(schematic_data['power_symbols'])}")
        print(f"   Wire connections: {len(schematic_data['wires'])}")
        
        print("\n   Component Positions:")
        for comp in schematic_data['components']:
            x, y = comp['position']
            print(f"      {comp['reference']} ({comp['value']}): ({x:.1f}, {y:.1f}) mm")
        
        print("\n   Power Symbol Positions:")
        for power in schematic_data['power_symbols']:
            x, y = power['position']
            print(f"      {power['reference']} ({power['value']}): ({x:.1f}, {y:.1f}) mm")
        
        # Analyze positioning issues
        print("\n🔬 Positioning Issue Detection:")
        
        # Check if components are outside reasonable boundaries
        all_positions = [comp['position'] for comp in schematic_data['components'] + schematic_data['power_symbols']]
        if all_positions:
            xs = [pos[0] for pos in all_positions]
            ys = [pos[1] for pos in all_positions]
            
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            
            print(f"   Bounding box: ({min_x:.1f}, {min_y:.1f}) to ({max_x:.1f}, {max_y:.1f}) mm")
            
            # Check for issues
            issues = []
            
            # Issue #3: Components outside typical schematic area
            typical_max = 300  # mm (A4 page is ~297mm wide)
            if max_x > typical_max or max_y > typical_max:
                issues.append(f"Components extend beyond typical page size ({typical_max}mm)")
            
            # Check component spacing
            if len(all_positions) > 1:
                distances = []
                for i in range(len(all_positions)):
                    for j in range(i+1, len(all_positions)):
                        x1, y1 = all_positions[i]
                        x2, y2 = all_positions[j]
                        distance = ((x2-x1)**2 + (y2-y1)**2)**0.5
                        distances.append(distance)
                
                min_distance = min(distances)
                if min_distance < 20:  # Less than 20mm apart
                    issues.append(f"Components too close together (min: {min_distance:.1f}mm)")
            
            # Issue #4: Check wire connectivity
            if len(schematic_data['wires']) == 0 and len(schematic_data['components']) > 1:
                issues.append("No wire connections found between components")
            
            if issues:
                print("   ⚠️  Issues detected:")
                for issue in issues:
                    print(f"      • {issue}")
            else:
                print("   ✅ No positioning issues detected")
        
    except Exception as e:
        print(f"   ❌ Error analyzing positioning: {e}")
    
    # Show how to use this in development workflow
    print("\n🔧 Development Workflow Integration:")
    print("   1. Generate schematic with circuit_tools")
    print("   2. Capture screenshot with visualization_tools")
    print("   3. Analyze positioning and connectivity visually")
    print("   4. Iterate on component layout and wire routing")
    print("   5. Compare before/after screenshots")
    
    print("\n📋 Next Steps for Issue Resolution:")
    print("   • Use this visual feedback to fix component positioning (#3)")
    print("   • Implement proper wire routing between component pins (#4)")
    print("   • Add visual regression tests to prevent regressions")
    print("   • Integrate screenshot generation into devloop workflow")
    
    # Show file locations
    print(f"\n📁 Generated Files Location:")
    if os.path.exists("tests/visual_output"):
        for file in os.listdir("tests/visual_output"):
            file_path = os.path.join("tests/visual_output", file)
            if os.path.isfile(file_path):
                print(f"   {file_path}")
    
    print("\n🎉 Visual rendering system successfully implemented!")
    print("   You can now see exactly how your schematics look and debug issues visually.")


if __name__ == "__main__":
    asyncio.run(demo_visual_debugging())