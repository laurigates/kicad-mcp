"""
Netlist extraction and analysis tools for KiCad schematics.
"""
import os
from typing import Dict, List, Any, Optional
from mcp.server.fastmcp import FastMCP, Context

from kicad_mcp.utils.file_utils import get_project_files
from kicad_mcp.utils.logger import Logger
from kicad_mcp.utils.netlist_parser import extract_netlist, analyze_netlist

# Create logger for this module
logger = Logger()

def register_netlist_tools(mcp: FastMCP) -> None:
    """Register netlist-related tools with the MCP server.
    
    Args:
        mcp: The FastMCP server instance
    """
    
    @mcp.tool()
    async def extract_schematic_netlist(schematic_path: str, ctx: Context) -> Dict[str, Any]:
        """Extract netlist information from a KiCad schematic.
        
        This tool parses a KiCad schematic file and extracts comprehensive
        netlist information including components, connections, and labels.
        
        Args:
            schematic_path: Path to the KiCad schematic file (.kicad_sch)
            ctx: MCP context for progress reporting
            
        Returns:
            Dictionary with netlist information
        """
        logger.info(f"Extracting netlist from schematic: {schematic_path}")
        
        if not os.path.exists(schematic_path):
            logger.error(f"Schematic file not found: {schematic_path}")
            ctx.info(f"Schematic file not found: {schematic_path}")
            return {"success": False, "error": f"Schematic file not found: {schematic_path}"}
        
        # Report progress
        await ctx.report_progress(10, 100)
        ctx.info(f"Loading schematic file: {os.path.basename(schematic_path)}")
        
        # Extract netlist information
        try:
            await ctx.report_progress(20, 100)
            ctx.info("Parsing schematic structure...")
            
            netlist_data = extract_netlist(schematic_path)
            
            if "error" in netlist_data:
                logger.error(f"Error extracting netlist: {netlist_data['error']}")
                ctx.info(f"Error extracting netlist: {netlist_data['error']}")
                return {"success": False, "error": netlist_data['error']}
            
            await ctx.report_progress(50, 100)
            
            # Check if the component exists
            components = netlist_data.get("components", {})
            if component_ref not in components:
                logger.error(f"Component {component_ref} not found in schematic")
                ctx.info(f"Component {component_ref} not found in schematic")
                return {
                    "success": False, 
                    "error": f"Component {component_ref} not found in schematic",
                    "available_components": list(components.keys())
                }
            
            component_info = components[component_ref]
            ctx.info(f"Found component: {component_ref} ({component_info.get('lib_id', 'unknown type')})")
            
            # Find all nets connected to this component
            await ctx.report_progress(70, 100)
            ctx.info("Analyzing component connections...")
            
            # Build connection information
            connections = []
            connected_components = set()
            
            nets = netlist_data.get("nets", {})
            for net_name, pins in nets.items():
                # Check if any pin belongs to our component
                component_pins = [pin for pin in pins if pin.get('component') == component_ref]
                
                if component_pins:
                    # This net connects to our component
                    net_info = {
                        "net_name": net_name,
                        "pins": component_pins,
                        "connected_to": []
                    }
                    
                    # Find other components connected to this net
                    for pin in pins:
                        other_component = pin.get('component')
                        if other_component and other_component != component_ref:
                            connected_components.add(other_component)
                            net_info["connected_to"].append({
                                "component": other_component,
                                "pin": pin.get('pin', 'unknown')
                            })
                    
                    connections.append(net_info)
            
            await ctx.report_progress(90, 100)
            
            # Build result
            result = {
                "success": True,
                "component_ref": component_ref,
                "component_info": component_info,
                "connections": connections,
                "connected_component_count": len(connected_components),
                "connected_components": list(connected_components)
            }
            
            # Complete progress
            await ctx.report_progress(100, 100)
            ctx.info(f"Found {len(connections)} connections to component {component_ref}")
            
            return resultf"Error extracting netlist: {netlist_data['error']}")
                ctx.info(f"Error extracting netlist: {netlist_data['error']}")
                return {"success": False, "error": netlist_data['error']}
            
            await ctx.report_progress(60, 100)
            ctx.info(f"Extracted {netlist_data['component_count']} components and {netlist_data['net_count']} nets")
            
            # Analyze the netlist
            await ctx.report_progress(70, 100)
            ctx.info("Analyzing netlist data...")
            
            analysis_results = analyze_netlist(netlist_data)
            
            await ctx.report_progress(90, 100)
            
            # Build result
            result = {
                "success": True,
                "schematic_path": schematic_path,
                "component_count": netlist_data["component_count"],
                "net_count": netlist_data["net_count"],
                "components": netlist_data["components"],
                "nets": netlist_data["nets"],
                "analysis": analysis_results
            }
            
            # Complete progress
            await ctx.report_progress(100, 100)
            ctx.info("Netlist extraction complete")
            
            return result
            
        except Exception as e:
            logger.error(f"Error extracting netlist: {str(e)}")
            ctx.info(f"Error extracting netlist: {str(e)}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def extract_project_netlist(project_path: str, ctx: Context) -> Dict[str, Any]:
        """Extract netlist from a KiCad project's schematic.
        
        This tool finds the schematic associated with a KiCad project
        and extracts its netlist information.
        
        Args:
            project_path: Path to the KiCad project file (.kicad_pro)
            ctx: MCP context for progress reporting
            
        Returns:
            Dictionary with netlist information
        """
        logger.info(f"Extracting netlist for project: {project_path}")
        
        if not os.path.exists(project_path):
            logger.error(f"Project not found: {project_path}")
            ctx.info(f"Project not found: {project_path}")
            return {"success": False, "error": f"Project not found: {project_path}"}
        
        # Report progress
        await ctx.report_progress(10, 100)
        
        # Get the schematic file
        try:
            files = get_project_files(project_path)
            
            if "schematic" not in files:
                logger.error("Schematic file not found in project")
                ctx.info("Schematic file not found in project")
                return {"success": False, "error": "Schematic file not found in project"}
            
            schematic_path = files["schematic"]
            logger.info(f"Found schematic file: {schematic_path}")
            ctx.info(f"Found schematic file: {os.path.basename(schematic_path)}")
            
            # Extract netlist
            await ctx.report_progress(20, 100)
            
            # Call the schematic netlist extraction
            result = await extract_schematic_netlist(schematic_path, ctx)
            
            # Add project path to result
            if "success" in result and result["success"]:
                result["project_path"] = project_path
            
            return result
            
        except Exception as e:
            logger.error(f"Error extracting project netlist: {str(e)}")
            ctx.info(f"Error extracting project netlist: {str(e)}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def analyze_schematic_connections(schematic_path: str, ctx: Context) -> Dict[str, Any]:
        """Analyze connections in a KiCad schematic.
        
        This tool provides detailed analysis of component connections,
        including power nets, signal paths, and potential issues.
        
        Args:
            schematic_path: Path to the KiCad schematic file (.kicad_sch)
            ctx: MCP context for progress reporting
            
        Returns:
            Dictionary with connection analysis
        """
        logger.info(f"Analyzing connections in schematic: {schematic_path}")
        
        if not os.path.exists(schematic_path):
            logger.error(f"Schematic file not found: {schematic_path}")
            ctx.info(f"Schematic file not found: {schematic_path}")
            return {"success": False, "error": f"Schematic file not found: {schematic_path}"}
        
        # Report progress
        await ctx.report_progress(10, 100)
        ctx.info(f"Extracting netlist from: {os.path.basename(schematic_path)}")
        
        # Extract netlist information
        try:
            netlist_data = extract_netlist(schematic_path)
            
            if "error" in netlist_data:
                logger.error(f"Error extracting netlist: {netlist_data['error']}")
                ctx.info(f"Error extracting netlist: {netlist_data['error']}")
                return {"success": False, "error": netlist_data['error']}
            
            await ctx.report_progress(40, 100)
            
            # Advanced connection analysis
            ctx.info("Performing connection analysis...")
            
            analysis = {
                "component_count": netlist_data["component_count"],
                "net_count": netlist_data["net_count"],
                "component_types": {},
                "power_nets": [],
                "signal_nets": [],
                "potential_issues": []
            }
            
            # Analyze component types
            components = netlist_data.get("components", {})
            for ref, component in components.items():
                # Extract component type from reference (e.g., R1 -> R)
                import re
                comp_type_match = re.match(r'^([A-Za-z_]+)', ref)
                if comp_type_match:
                    comp_type = comp_type_match.group(1)
                    if comp_type not in analysis["component_types"]:
                        analysis["component_types"][comp_type] = 0
                    analysis["component_types"][comp_type] += 1
            
            await ctx.report_progress(60, 100)
            
            # Identify power nets
            nets = netlist_data.get("nets", {})
            for net_name, pins in nets.items():
                if any(net_name.startswith(prefix) for prefix in ["VCC", "VDD", "GND", "+5V", "+3V3", "+12V"]):
                    analysis["power_nets"].append({
                        "name": net_name,
                        "pin_count": len(pins)
                    })
                else:
                    analysis["signal_nets"].append({
                        "name": net_name,
                        "pin_count": len(pins)
                    })
            
            await ctx.report_progress(80, 100)
            
            # Check for potential issues
            # 1. Nets with only one connection (floating)
            for net_name, pins in nets.items():
                if len(pins) <= 1 and not any(net_name.startswith(prefix) for prefix in ["VCC", "VDD", "GND", "+5V", "+3V3", "+12V"]):
                    analysis["potential_issues"].append({
                        "type": "floating_net",
                        "net": net_name,
                        "description": f"Net '{net_name}' appears to be floating (only has {len(pins)} connection)"
                    })
            
            # 2. Power pins without connections
            # This would require more detailed parsing of the schematic
            
            await ctx.report_progress(90, 100)
            
            # Build result
            result = {
                "success": True,
                "schematic_path": schematic_path,
                "analysis": analysis
            }
            
            # Complete progress
            await ctx.report_progress(100, 100)
            ctx.info("Connection analysis complete")
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing connections: {str(e)}")
            ctx.info(f"Error analyzing connections: {str(e)}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def find_component_connections(project_path: str, component_ref: str, ctx: Context) -> Dict[str, Any]:
        """Find all connections for a specific component in a KiCad project.
        
        This tool extracts information about how a specific component
        is connected to other components in the schematic.
        
        Args:
            project_path: Path to the KiCad project file (.kicad_pro)
            component_ref: Component reference (e.g., "R1", "U3")
            ctx: MCP context for progress reporting
            
        Returns:
            Dictionary with component connection information
        """
        logger.info(f"Finding connections for component {component_ref} in project: {project_path}")
        
        if not os.path.exists(project_path):
            logger.error(f"Project not found: {project_path}")
            ctx.info(f"Project not found: {project_path}")
            return {"success": False, "error": f"Project not found: {project_path}"}
        
        # Report progress
        await ctx.report_progress(10, 100)
        
        # Get the schematic file
        try:
            files = get_project_files(project_path)
            
            if "schematic" not in files:
                logger.error("Schematic file not found in project")
                ctx.info("Schematic file not found in project")
                return {"success": False, "error": "Schematic file not found in project"}
            
            schematic_path = files["schematic"]
            logger.info(f"Found schematic file: {schematic_path}")
            ctx.info(f"Found schematic file: {os.path.basename(schematic_path)}")
            
            # Extract netlist
            await ctx.report_progress(30, 100)
            ctx.info(f"Extracting netlist to find connections for {component_ref}...")
            
            netlist_data = extract_netlist(schematic_path)
            
            if "error" in netlist_data:
                logger.error(
