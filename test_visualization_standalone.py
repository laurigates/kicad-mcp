#!/usr/bin/env python3
"""
Standalone test for visualization tools without MCP dependencies.
"""

import asyncio
import os
import subprocess
import tempfile

import pytest


@pytest.mark.asyncio
async def test_kicad_cli_availability():
    """Test if kicad-cli is available."""
    print("🔧 Testing KiCad CLI availability...")

    # Try macOS path first, then PATH
    kicad_cli_paths = ["/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli", "kicad-cli"]

    for cli_path in kicad_cli_paths:
        try:
            result = subprocess.run(
                [cli_path, "--version"], capture_output=True, text=True, timeout=10
            )

            if result.returncode == 0:
                print(f"✅ KiCad CLI available at {cli_path}: {result.stdout.strip()}")
                return cli_path
        except FileNotFoundError:
            continue
        except Exception as e:
            print(f"⚠️  Error testing {cli_path}: {e}")
            continue

    print("❌ KiCad CLI not found in any location")
    return None


@pytest.mark.asyncio
async def test_svg_conversion():
    """Test SVG to PNG conversion."""
    print("\n🔧 Testing SVG to PNG conversion...")

    try:
        import cairosvg
        from PIL import Image

        # Create a simple test SVG
        test_svg_content = """<?xml version="1.0" encoding="UTF-8"?>
<svg width="200" height="100" xmlns="http://www.w3.org/2000/svg">
  <rect x="10" y="10" width="80" height="60" fill="red" stroke="black" stroke-width="2"/>
  <text x="50" y="45" text-anchor="middle" font-family="Arial" font-size="12">Test</text>
</svg>"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".svg", delete=False) as svg_file:
            svg_file.write(test_svg_content)
            svg_path = svg_file.name

        # Convert to PNG
        png_path = svg_path.replace(".svg", ".png")

        cairosvg.svg2png(
            url=svg_path,
            write_to=png_path,
            output_width=400,
            output_height=200,
            background_color="white",
        )

        # Verify PNG was created
        if os.path.exists(png_path):
            # Check if it's a valid image
            with Image.open(png_path) as img:
                print(f"✅ SVG to PNG conversion successful: {img.size}")

            # Cleanup
            os.unlink(svg_path)
            os.unlink(png_path)
            return True
        else:
            print("❌ PNG file not created")
            return False

    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        return False
    except Exception as e:
        print(f"❌ SVG conversion error: {e}")
        return False


@pytest.mark.asyncio
async def test_schematic_export():
    """Test schematic export with available project."""
    print("\n🔧 Testing schematic export...")

    # Find available schematic files
    schematic_files = []
    for root, _dirs, files in os.walk("."):
        for file in files:
            if file.endswith(".kicad_sch"):
                schematic_files.append(os.path.join(root, file))

    if not schematic_files:
        print("⚠️  No .kicad_sch files found to test with")
        return False

    schematic_file = schematic_files[0]
    print(f"📁 Testing with schematic: {schematic_file}")

    # Check if kicad-cli is available
    kicad_cli = await test_kicad_cli_availability()
    if not kicad_cli:
        print("⚠️  KiCad CLI not available, skipping export test")
        return False

    # Create output directory
    output_dir = "tests/visual_output"
    os.makedirs(output_dir, exist_ok=True)

    try:
        # Export schematic to SVG
        cmd = [
            kicad_cli,
            "sch",
            "export",
            "svg",
            "--output",
            output_dir,
            "--no-background-color",
            "--exclude-drawing-sheet",
            schematic_file,
        ]

        print(f"🔄 Running: {' '.join(cmd)}")

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            # Check if SVG was created
            svg_files = [f for f in os.listdir(output_dir) if f.endswith(".svg")]
            if svg_files:
                svg_file = os.path.join(output_dir, svg_files[0])
                print(f"✅ SVG export successful: {svg_file}")

                # Test SVG to PNG conversion
                try:
                    import cairosvg

                    png_file = svg_file.replace(".svg", ".png")

                    cairosvg.svg2png(
                        url=svg_file,
                        write_to=png_file,
                        output_width=1200,
                        output_height=800,
                        background_color="white",
                    )

                    if os.path.exists(png_file):
                        file_size = os.path.getsize(png_file)
                        print(f"✅ PNG conversion successful: {png_file} ({file_size} bytes)")
                        return True
                    else:
                        print("❌ PNG file not created")
                        return False

                except ImportError:
                    print("⚠️  cairosvg not available for PNG conversion")
                    return True  # SVG export worked at least
                except Exception as e:
                    print(f"❌ PNG conversion failed: {e}")
                    return False
            else:
                print("❌ No SVG files found after export")
                return False
        else:
            print(f"❌ SVG export failed: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print("❌ Export command timed out")
        return False
    except Exception as e:
        print(f"❌ Export error: {e}")
        return False


async def create_test_schematic():
    """Create a simple test schematic for visualization testing."""
    print("\n🔧 Creating test schematic...")

    try:
        from kicad_mcp.utils.sexpr_generator import SExpressionGenerator

        # Create simple test circuit
        components = [
            {
                "reference": "R1",
                "value": "1kΩ",
                "symbol_library": "Device",
                "symbol_name": "R",
                "component_type": "resistor",
                "position": (50, 50),
            },
            {
                "reference": "LED1",
                "value": "Red",
                "symbol_library": "Device",
                "symbol_name": "LED",
                "component_type": "led",
                "position": (100, 50),
            },
        ]

        power_symbols = [
            {"reference": "#PWR01", "power_type": "VCC", "position": (25, 25)},
            {"reference": "#PWR02", "power_type": "GND", "position": (25, 75)},
        ]

        connections = [{"start_x": 50, "start_y": 50, "end_x": 100, "end_y": 50}]

        # Generate schematic
        generator = SExpressionGenerator()
        schematic_content = generator.generate_schematic(
            circuit_name="Visualization Test Circuit",
            components=components,
            power_symbols=power_symbols,
            connections=connections,
        )

        # Save to file
        output_dir = "tests/visual_output"
        os.makedirs(output_dir, exist_ok=True)
        schematic_file = os.path.join(output_dir, "test_circuit.kicad_sch")

        with open(schematic_file, "w") as f:
            f.write(schematic_content)

        print(f"✅ Test schematic created: {schematic_file}")
        return schematic_file

    except Exception as e:
        print(f"❌ Error creating test schematic: {e}")
        return None


async def main():
    """Run all visualization tests."""
    print("🚀 KiCad Visualization Tools Test Suite")
    print("=" * 50)

    results = []

    # Test 1: KiCad CLI availability
    kicad_cli = await test_kicad_cli_availability()
    results.append(("KiCad CLI", kicad_cli is not None))

    # Test 2: SVG conversion
    svg_conversion = await test_svg_conversion()
    results.append(("SVG Conversion", svg_conversion))

    # Test 3: Create test schematic
    test_schematic = await create_test_schematic()
    results.append(("Test Schematic Creation", test_schematic is not None))

    # Test 4: Full workflow test
    if test_schematic and kicad_cli:
        export_success = await test_schematic_export()
        results.append(("Schematic Export", export_success))

    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print("-" * 30)

    passed = 0
    total = len(results)

    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name}: {status}")
        if success:
            passed += 1

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All visualization tests passed!")
        print("\nNext steps:")
        print("1. Check 'tests/visual_output/' for generated files")
        print("2. Verify images look correct")
        print("3. Integration with MCP framework ready")
    else:
        print("⚠️  Some tests failed - check error messages above")

    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
