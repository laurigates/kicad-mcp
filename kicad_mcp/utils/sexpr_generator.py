"""
S-expression generator for KiCad schematic files.

Converts circuit descriptions to proper KiCad S-expression format.
"""
import uuid
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass


class SExpressionGenerator:
    """Generator for KiCad S-expression format schematics."""
    
    def __init__(self):
        self.symbol_libraries = {}
        self.component_uuid_map = {}
    
    def generate_schematic(self, circuit_name: str, components: List[Dict], 
                          power_symbols: List[Dict], connections: List[Dict]) -> str:
        """Generate a complete KiCad schematic in S-expression format.
        
        Args:
            circuit_name: Name of the circuit
            components: List of component dictionaries
            power_symbols: List of power symbol dictionaries  
            connections: List of connection dictionaries
            
        Returns:
            S-expression formatted schematic as string
        """
        # Generate main schematic UUID
        main_uuid = str(uuid.uuid4())
        
        # Start building the S-expression
        sexpr_lines = [
            "(kicad_sch",
            "  (version 20230121)",
            "  (generator kicad-mcp)",
            f'  (uuid "{main_uuid}")',
            '  (paper "A4")',
            "",
            "  (title_block",
            f'    (title "{circuit_name}")',
            '    (date "")',
            '    (rev "")',
            '    (company "")',
            "  )",
            ""
        ]
        
        # Add symbol libraries
        lib_symbols = self._generate_lib_symbols(components, power_symbols)
        if lib_symbols:
            sexpr_lines.extend(lib_symbols)
            sexpr_lines.append("")
        
        # Add components (symbols)
        for component in components:
            symbol_lines = self._generate_component_symbol(component)
            sexpr_lines.extend(symbol_lines)
            sexpr_lines.append("")
        
        # Add power symbols
        for power_symbol in power_symbols:
            symbol_lines = self._generate_power_symbol(power_symbol)
            sexpr_lines.extend(symbol_lines)
            sexpr_lines.append("")
        
        # Add wires for connections
        for connection in connections:
            wire_lines = self._generate_wire(connection)
            sexpr_lines.extend(wire_lines)
        
        if connections:
            sexpr_lines.append("")
        
        # Add sheet instances (required)
        sexpr_lines.extend([
            "  (sheet_instances",
            '    (path "/" (page "1"))',
            "  )",
            ")"
        ])
        
        return "\n".join(sexpr_lines)
    
    def _generate_lib_symbols(self, components: List[Dict], 
                             power_symbols: List[Dict]) -> List[str]:
        """Generate lib_symbols section."""
        lines = ["  (lib_symbols"]
        
        # Collect unique symbol libraries
        symbols_needed = set()
        
        for component in components:
            lib_id = f"{component.get('symbol_library', 'Device')}:{component.get('symbol_name', 'R')}"
            symbols_needed.add(lib_id)
        
        for power_symbol in power_symbols:
            power_type = power_symbol.get('power_type', 'VCC')
            lib_id = f"power:{power_type}"
            symbols_needed.add(lib_id)
        
        # Generate basic symbol definitions
        for lib_id in sorted(symbols_needed):
            library, symbol = lib_id.split(':')
            symbol_def = self._generate_symbol_definition(library, symbol)
            lines.extend([f"    {line}" for line in symbol_def])
        
        lines.append("  )")
        return lines
    
    def _generate_symbol_definition(self, library: str, symbol: str) -> List[str]:
        """Generate a basic symbol definition."""
        if library == "Device":
            if symbol == "R":
                return self._generate_resistor_symbol()
            elif symbol == "C":
                return self._generate_capacitor_symbol()
            elif symbol == "L":
                return self._generate_inductor_symbol()
            elif symbol == "LED":
                return self._generate_led_symbol()
            elif symbol == "D":
                return self._generate_diode_symbol()
        elif library == "power":
            return self._generate_power_symbol_definition(symbol)
        
        # Default symbol (resistor-like)
        return self._generate_resistor_symbol()
    
    def _generate_resistor_symbol(self) -> List[str]:
        """Generate resistor symbol definition."""
        return [
            '(symbol "Device:R"',
            '  (pin_numbers hide)',
            '  (pin_names (offset 0))',
            '  (exclude_from_sim no)',
            '  (in_bom yes)',
            '  (on_board yes)',
            '  (property "Reference" "R" (at 2.032 0 90))',
            '  (property "Value" "R" (at 0 0 90))',
            '  (property "Footprint" "" (at -1.778 0 90))',
            '  (property "Datasheet" "~" (at 0 0 0))',
            '  (symbol "R_0_1"',
            '    (rectangle (start -1.016 -2.54) (end 1.016 2.54))',
            '  )',
            '  (symbol "R_1_1"',
            '    (pin passive line (at 0 3.81 270) (length 1.27)',
            '      (name "~" (effects (font (size 1.27 1.27))))',
            '      (number "1" (effects (font (size 1.27 1.27))))',
            '    )',
            '    (pin passive line (at 0 -3.81 90) (length 1.27)',
            '      (name "~" (effects (font (size 1.27 1.27))))',
            '      (number "2" (effects (font (size 1.27 1.27))))',
            '    )',
            '  )',
            ')'
        ]
    
    def _generate_capacitor_symbol(self) -> List[str]:
        """Generate capacitor symbol definition."""
        return [
            '(symbol "Device:C"',
            '  (pin_numbers hide)',
            '  (pin_names (offset 0.254))',
            '  (exclude_from_sim no)',
            '  (in_bom yes)',
            '  (on_board yes)',
            '  (property "Reference" "C" (at 0.635 2.54 0))',
            '  (property "Value" "C" (at 0.635 -2.54 0))',
            '  (property "Footprint" "" (at 0.9652 -3.81 0))',
            '  (property "Datasheet" "~" (at 0 0 0))',
            '  (symbol "C_0_1"',
            '    (polyline',
            '      (pts (xy -2.032 -0.762) (xy 2.032 -0.762))',
            '    )',
            '    (polyline',
            '      (pts (xy -2.032 0.762) (xy 2.032 0.762))',
            '    )',
            '  )',
            '  (symbol "C_1_1"',
            '    (pin passive line (at 0 3.81 270) (length 2.794)',
            '      (name "~" (effects (font (size 1.27 1.27))))',
            '      (number "1" (effects (font (size 1.27 1.27))))',
            '    )',
            '    (pin passive line (at 0 -3.81 90) (length 2.794)',
            '      (name "~" (effects (font (size 1.27 1.27))))',
            '      (number "2" (effects (font (size 1.27 1.27))))',
            '    )',
            '  )',
            ')'
        ]
    
    def _generate_inductor_symbol(self) -> List[str]:
        """Generate inductor symbol definition."""
        return [
            '(symbol "Device:L"',
            '  (pin_numbers hide)',
            '  (pin_names (offset 1.016) hide)',
            '  (exclude_from_sim no)',
            '  (in_bom yes)',
            '  (on_board yes)',
            '  (property "Reference" "L" (at -1.27 0 90))',
            '  (property "Value" "L" (at 1.905 0 90))',
            '  (property "Footprint" "" (at 0 0 0))',
            '  (property "Datasheet" "~" (at 0 0 0))',
            '  (symbol "L_0_1"',
            '    (arc (start 0 -2.54) (mid 0.6323 -1.905) (end 0 -1.27))',
            '    (arc (start 0 -1.27) (mid 0.6323 -0.635) (end 0 0))',
            '    (arc (start 0 0) (mid 0.6323 0.635) (end 0 1.27))',
            '    (arc (start 0 1.27) (mid 0.6323 1.905) (end 0 2.54))',
            '  )',
            '  (symbol "L_1_1"',
            '    (pin passive line (at 0 3.81 270) (length 1.27)',
            '      (name "1" (effects (font (size 1.27 1.27))))',
            '      (number "1" (effects (font (size 1.27 1.27))))',
            '    )',
            '    (pin passive line (at 0 -3.81 90) (length 1.27)',
            '      (name "2" (effects (font (size 1.27 1.27))))',
            '      (number "2" (effects (font (size 1.27 1.27))))',
            '    )',
            '  )',
            ')'
        ]
    
    def _generate_led_symbol(self) -> List[str]:
        """Generate LED symbol definition."""
        return [
            '(symbol "Device:LED"',
            '  (pin_numbers hide)',
            '  (pin_names (offset 1.016) hide)',
            '  (exclude_from_sim no)',
            '  (in_bom yes)',
            '  (on_board yes)',
            '  (property "Reference" "D" (at 0 2.54 0))',
            '  (property "Value" "LED" (at 0 -2.54 0))',
            '  (property "Footprint" "" (at 0 0 0))',
            '  (property "Datasheet" "~" (at 0 0 0))',
            '  (symbol "LED_0_1"',
            '    (polyline',
            '      (pts (xy -1.27 -1.27) (xy -1.27 1.27))',
            '    )',
            '    (polyline',
            '      (pts (xy -1.27 0) (xy 1.27 0))',
            '    )',
            '    (polyline',
            '      (pts (xy 1.27 -1.27) (xy 1.27 1.27) (xy -1.27 0) (xy 1.27 -1.27))',
            '    )',
            '  )',
            '  (symbol "LED_1_1"',
            '    (pin passive line (at -3.81 0 0) (length 2.54)',
            '      (name "K" (effects (font (size 1.27 1.27))))',
            '      (number "1" (effects (font (size 1.27 1.27))))',
            '    )',
            '    (pin passive line (at 3.81 0 180) (length 2.54)',
            '      (name "A" (effects (font (size 1.27 1.27))))',
            '      (number "2" (effects (font (size 1.27 1.27))))',
            '    )',
            '  )',
            ')'
        ]
    
    def _generate_diode_symbol(self) -> List[str]:
        """Generate diode symbol definition."""
        return [
            '(symbol "Device:D"',
            '  (pin_numbers hide)',
            '  (pin_names (offset 1.016) hide)',
            '  (exclude_from_sim no)',
            '  (in_bom yes)',
            '  (on_board yes)',
            '  (property "Reference" "D" (at 0 2.54 0))',
            '  (property "Value" "D" (at 0 -2.54 0))',
            '  (property "Footprint" "" (at 0 0 0))',
            '  (property "Datasheet" "~" (at 0 0 0))',
            '  (symbol "D_0_1"',
            '    (polyline',
            '      (pts (xy -1.27 -1.27) (xy -1.27 1.27))',
            '    )',
            '    (polyline',
            '      (pts (xy -1.27 0) (xy 1.27 0))',
            '    )',
            '    (polyline',
            '      (pts (xy 1.27 -1.27) (xy 1.27 1.27) (xy -1.27 0) (xy 1.27 -1.27))',
            '    )',
            '  )',
            '  (symbol "D_1_1"',
            '    (pin passive line (at -3.81 0 0) (length 2.54)',
            '      (name "K" (effects (font (size 1.27 1.27))))',
            '      (number "1" (effects (font (size 1.27 1.27))))',
            '    )',
            '    (pin passive line (at 3.81 0 180) (length 2.54)',
            '      (name "A" (effects (font (size 1.27 1.27))))',
            '      (number "2" (effects (font (size 1.27 1.27))))',
            '    )',
            '  )',
            ')'
        ]
    
    def _generate_power_symbol_definition(self, power_type: str) -> List[str]:
        """Generate power symbol definition."""
        return [
            f'(symbol "power:{power_type}"',
            '  (power)',
            '  (pin_names (offset 0) hide)',
            '  (exclude_from_sim no)',
            '  (in_bom yes)',
            '  (on_board yes)',
            f'  (property "Reference" "#PWR" (at 0 -3.81 0))',
            f'  (property "Value" "{power_type}" (at 0 3.556 0))',
            '  (property "Footprint" "" (at 0 0 0))',
            '  (property "Datasheet" "" (at 0 0 0))',
            f'  (symbol "{power_type}_0_1"',
            '    (polyline',
            '      (pts (xy -0.762 1.27) (xy 0 2.54))',
            '    )',
            '    (polyline',
            '      (pts (xy 0 0) (xy 0 2.54))',
            '    )',
            '    (polyline',
            '      (pts (xy 0 2.54) (xy 0.762 1.27))',
            '    )',
            '  )',
            f'  (symbol "{power_type}_1_1"',
            '    (pin power_in line (at 0 0 90) (length 0) hide',
            '      (name "1" (effects (font (size 1.27 1.27))))',
            '      (number "1" (effects (font (size 1.27 1.27))))',
            '    )',
            '  )',
            ')'
        ]
    
    def _generate_component_symbol(self, component: Dict) -> List[str]:
        """Generate component symbol instance."""
        comp_uuid = str(uuid.uuid4())
        self.component_uuid_map[component['reference']] = comp_uuid
        
        # Convert position from mm to KiCad internal units (0.1mm)
        x_pos = component['position'][0] * 10
        y_pos = component['position'][1] * 10
        
        lib_id = f"{component.get('symbol_library', 'Device')}:{component.get('symbol_name', 'R')}"
        
        lines = [
            f'  (symbol (lib_id "{lib_id}") (at {x_pos} {y_pos} 0) (unit 1)',
            '    (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)',
            f'    (uuid "{comp_uuid}")',
            f'    (property "Reference" "{component["reference"]}" (at {x_pos + 25.4} {y_pos - 12.7} 0))',
            f'    (property "Value" "{component["value"]}" (at {x_pos + 25.4} {y_pos + 12.7} 0))',
            f'    (property "Footprint" "" (at {x_pos} {y_pos} 0))',
            f'    (property "Datasheet" "~" (at {x_pos} {y_pos} 0))',
        ]
        
        # Add pin UUIDs (basic 2-pin component)
        lines.extend([
            f'    (pin "1" (uuid "{str(uuid.uuid4())}"))',
            f'    (pin "2" (uuid "{str(uuid.uuid4())}"))',
            '  )'
        ])
        
        return lines
    
    def _generate_power_symbol(self, power_symbol: Dict) -> List[str]:
        """Generate power symbol instance."""
        power_uuid = str(uuid.uuid4())
        ref = power_symbol.get('reference', f"#PWR0{len(self.component_uuid_map) + 1:03d}")
        self.component_uuid_map[ref] = power_uuid
        
        # Convert position from mm to KiCad internal units
        x_pos = power_symbol['position'][0] * 10
        y_pos = power_symbol['position'][1] * 10
        
        power_type = power_symbol['power_type']
        lib_id = f"power:{power_type}"
        
        lines = [
            f'  (symbol (lib_id "{lib_id}") (at {x_pos} {y_pos} 0) (unit 1)',
            '    (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)',
            f'    (uuid "{power_uuid}")',
            f'    (property "Reference" "{ref}" (at {x_pos} {y_pos - 25.4} 0))',
            f'    (property "Value" "{power_type}" (at {x_pos} {y_pos + 35.56} 0))',
            f'    (property "Footprint" "" (at {x_pos} {y_pos} 0))',
            f'    (property "Datasheet" "" (at {x_pos} {y_pos} 0))',
            f'    (pin "1" (uuid "{str(uuid.uuid4())}"))',
            '  )'
        ]
        
        return lines
    
    def _generate_wire(self, connection: Dict) -> List[str]:
        """Generate wire connection."""
        wire_uuid = str(uuid.uuid4())
        
        # For now, generate simple point-to-point wires
        # In a real implementation, you'd need to calculate actual pin positions
        start_x = connection.get('start_x', 100) * 10
        start_y = connection.get('start_y', 100) * 10
        end_x = connection.get('end_x', 200) * 10
        end_y = connection.get('end_y', 100) * 10
        
        lines = [
            f'  (wire (pts (xy {start_x} {start_y}) (xy {end_x} {end_y})) (stroke (width 0) (type default))',
            f'    (uuid "{wire_uuid}")',
            '  )'
        ]
        
        return lines