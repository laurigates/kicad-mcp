"""Prompt templates for KiCad interactions.

Provides general-purpose prompts for component creation, PCB debugging,
and manufacturing preparation.
"""

from fastmcp import FastMCP


def register_prompts(mcp: FastMCP) -> None:
    """Register prompt templates with the MCP server.

    Args:
        mcp: The FastMCP server instance
    """

    @mcp.prompt()
    def create_new_component() -> str:
        """Prompt for creating a new KiCad component."""
        prompt = """
        I want to create a new component in KiCad for my PCB design. I need help with:

        1. Deciding on the correct component package/footprint
        2. Creating the schematic symbol
        3. Connecting the schematic symbol to the footprint
        4. Adding the component to my design

        Please provide step-by-step instructions on how to create a new component in KiCad.
        """

        return prompt

    @mcp.prompt()
    def debug_pcb_issues() -> str:
        """Prompt for debugging common PCB issues."""
        prompt = """
        I'm having issues with my KiCad PCB design. Can you help me troubleshoot the following problems:

        1. Design rule check (DRC) errors
        2. Electrical rule check (ERC) errors
        3. Footprint mismatches
        4. Routing challenges

        Please provide a systematic approach to identifying and fixing these issues in KiCad.
        """

        return prompt

    @mcp.prompt()
    def pcb_manufacturing_checklist() -> str:
        """Prompt for PCB manufacturing preparation checklist."""
        prompt = """
        I need to prepare my KiCad PCB design for manufacturing. Please help me verify:

        1. Design rule check (DRC) passes with no errors
        2. Correct Gerber file generation settings
        3. Drill file configuration
        4. Board outline and dimensions
        5. Copper pour and ground plane integrity
        6. Silkscreen legibility and placement
        7. Solder mask and paste layer correctness

        Please provide a checklist for manufacturing preparation.
        """

        return prompt
