# Text-to-Schematic Guide

This guide covers the text-to-schematic conversion tools in KiCad MCP, which allow you to create electronic schematics using MermaidJS-like text descriptions.

## Overview

The text-to-schematic tools enable you to:
- Describe circuits using simple YAML or text syntax
- Generate KiCad-compatible schematic files
- Use templates for common circuit patterns
- Validate circuit descriptions before generation

## Supported Formats

### YAML Format (Recommended)

The YAML format provides a structured way to describe circuits:

```yaml
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
```

### Simple Text Format

For quick prototyping, you can use a simpler text format:

```
circuit: Simple Circuit
components:
R1 resistor 1kΩ (10, 20)
C1 capacitor 100nF (30, 20)
power:
VCC +5V (10, 10)
GND GND (10, 50)
connections:
VCC -> R1.1
R1.2 -> C1.1
```

## Component Types

The following component types are supported:

| Type | Symbol Library | Symbol Name | Description |
|------|----------------|-------------|-------------|
| `resistor` | Device | R | Resistor |
| `capacitor` | Device | C | Capacitor |
| `inductor` | Device | L | Inductor |
| `led` | Device | LED | Light Emitting Diode |
| `diode` | Device | D | Diode |
| `transistor_npn` | Device | Q_NPN_CBE | NPN Transistor |
| `transistor_pnp` | Device | Q_PNP_CBE | PNP Transistor |
| `ic` | Device | U | Integrated Circuit |
| `switch` | Switch | SW_Push | Push Switch |
| `connector` | Connector | Conn_01x02 | 2-pin Connector |

## Power Symbols

Supported power symbols:
- `VCC` - Generic positive supply
- `GND` - Ground
- `+5V` - +5V supply
- `+3V3` - +3.3V supply
- `+12V` - +12V supply
- `-12V` - -12V supply

## Position Format

Positions are specified in millimeters using the format `(x, y)`:
- `(10, 20)` - 10mm right, 20mm down from origin
- `(0, 0)` - Origin position
- `(-5, 15)` - 5mm left, 15mm down from origin

## Connection Format

Connections use arrow notation to specify wire connections:
- `VCC → R1.1` - Connect VCC to pin 1 of R1
- `R1.2 -> LED1.anode` - Connect pin 2 of R1 to LED anode
- `LED1.cathode — GND` - Connect LED cathode to GND

Supported arrow formats: `→`, `->`, `—`

## Available Tools

### `create_circuit_from_text`

Creates a KiCad schematic from text description using the existing JSON-based circuit tools.

**Parameters:**
- `project_path`: Path to KiCad project file
- `circuit_description`: Text description of the circuit
- `format_type`: "yaml" or "simple" (default: "yaml")

**Example:**
```python
result = await create_circuit_from_text(
    project_path="/path/to/project.kicad_pro",
    circuit_description=yaml_circuit,
    format_type="yaml"
)
```

### `create_kicad_schematic_from_text`

Creates a native KiCad schematic file using S-expression format (recommended for compatibility).

**Parameters:**
- `project_path`: Path to KiCad project file
- `circuit_description`: Text description of the circuit
- `format_type`: "yaml" or "simple" (default: "yaml")
- `output_format`: "sexpr" or "json" (default: "sexpr")

**Example:**
```python
result = await create_kicad_schematic_from_text(
    project_path="/path/to/project.kicad_pro",
    circuit_description=yaml_circuit,
    format_type="yaml",
    output_format="sexpr"
)
```

### `validate_circuit_description`

Validates a text circuit description without creating files.

**Parameters:**
- `circuit_description`: Text description to validate
- `format_type`: "yaml" or "simple" (default: "yaml")

**Example:**
```python
result = await validate_circuit_description(
    circuit_description=yaml_circuit,
    format_type="yaml"
)
```

### `get_circuit_template`

Gets predefined circuit templates for common patterns.

**Parameters:**
- `template_name`: Name of template (default: "led_blinker")

**Available Templates:**
- `led_blinker` - 555 timer LED blinker circuit
- `voltage_divider` - Simple voltage divider
- `rc_filter` - RC low-pass filter

**Example:**
```python
result = await get_circuit_template(template_name="voltage_divider")
```

## Circuit Templates

### LED Blinker
A classic 555 timer-based LED blinker circuit:

```yaml
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
```

### Voltage Divider
Simple resistive voltage divider:

```yaml
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
```

### RC Filter
RC low-pass filter circuit:

```yaml
circuit "RC Low-Pass Filter":
  components:
    - R1: resistor 1kΩ at (20, 20)
    - C1: capacitor 100nF at (40, 30)
  power:
    - GND: GND at (40, 50)
  connections:
    - R1.2 → C1.1
    - C1.2 → GND
```

## Best Practices

### 1. Use Descriptive Names
```yaml
# Good
- R_LED: resistor 220Ω at (10, 20)
- LED_STATUS: led red at (30, 20)

# Avoid
- R1: resistor 220Ω at (10, 20)
- D1: led red at (30, 20)
```

### 2. Organize Components Logically
Place related components near each other and use consistent spacing:

```yaml
# Power supply section
- VCC: +5V at (10, 10)
- GND: GND at (10, 50)

# Input section
- R_INPUT: resistor 10kΩ at (30, 20)
- C_INPUT: capacitor 100nF at (30, 30)

# Output section
- R_OUTPUT: resistor 1kΩ at (70, 20)
- LED_OUTPUT: led green at (70, 30)
```

### 3. Validate Before Creating
Always validate your circuit description first:

```python
# Validate first
validation = await validate_circuit_description(circuit_desc)
if validation["success"] and len(validation["warnings"]) == 0:
    # Then create the schematic
    result = await create_kicad_schematic_from_text(project_path, circuit_desc)
```

### 4. Use S-Expression Format
For maximum KiCad compatibility, use the S-expression output format:

```python
result = await create_kicad_schematic_from_text(
    project_path=project_path,
    circuit_description=circuit_desc,
    output_format="sexpr"  # Recommended
)
```

## Output Formats

### S-Expression (.kicad_sch)
The S-expression format generates native KiCad schematic files that can be opened directly in KiCad:

```lisp
(kicad_sch
  (version 20230121)
  (generator kicad-mcp)
  (uuid "12345678-1234-1234-1234-123456789abc")
  (paper "A4")

  (symbol (lib_id "Device:R") (at 100 200 0) (unit 1)
    (property "Reference" "R1" (at 125.4 187.3 0))
    (property "Value" "220Ω" (at 125.4 212.7 0))
  )
)
```

### JSON (.kicad_sch)
The JSON format uses the existing KiCad MCP circuit tools (compatible but less standard):

```json
{
  "version": 20230121,
  "generator": "kicad-mcp",
  "symbol": [
    {
      "lib_id": "Device:R",
      "at": [100, 200, 0],
      "property": [
        {"name": "Reference", "value": "R1"},
        {"name": "Value", "value": "220Ω"}
      ]
    }
  ]
}
```

## Error Handling

The tools provide comprehensive error reporting:

```python
result = await create_kicad_schematic_from_text(project_path, circuit_desc)

if not result["success"]:
    print(f"Error: {result['error']}")
elif result.get("errors"):
    print(f"Partial success with errors: {result['errors']}")
elif result.get("warnings"):
    print(f"Success with warnings: {result['warnings']}")
```

## Integration with Existing Tools

The text-to-schematic tools integrate seamlessly with other KiCad MCP tools:

1. **Create from text** → **Validate schematic** → **Run DRC** → **Generate BOM**
2. **Get template** → **Modify description** → **Create schematic** → **Export files**

## Limitations

Current limitations:
- Pin-to-pin connections are simplified (future enhancement planned)
- Limited component library (extensible)
- No hierarchical sheet support yet
- Wire routing is basic (straight lines)

## Future Enhancements

Planned features:
- Advanced pin mapping and connectivity
- Custom component libraries
- Hierarchical sheet support
- Automatic wire routing optimization
- Integration with SPICE simulation
- Import from other text formats (SPICE, Verilog)
