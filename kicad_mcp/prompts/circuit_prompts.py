"""
Prompt templates for circuit creation in KiCad.
"""

from fastmcp import FastMCP


def register_circuit_prompts(mcp: FastMCP) -> None:
    """Register circuit creation prompt templates with the MCP server.

    Args:
        mcp: The FastMCP server instance
    """

    @mcp.prompt()
    def create_basic_circuit() -> str:
        """Prompt for creating a basic circuit from scratch."""
        prompt = """
        I'd like to create a new KiCad circuit design. Can you help me:

        1. Create a new KiCad project
        2. Add basic components (resistors, capacitors, etc.)
        3. Connect the components with wires
        4. Add power symbols (VCC, GND)
        5. Validate the schematic for common issues

        Project details:
        - Project name: [Enter your project name]
        - Project location: [Enter the directory path]
        - Circuit type: [Describe what kind of circuit you want to create]

        Please guide me through each step and create the circuit systematically.
        """
        return prompt.strip()

    @mcp.prompt()
    def create_led_circuit() -> str:
        """Prompt for creating a simple LED circuit."""
        prompt = """
        I want to create a simple LED circuit in KiCad. Please help me:

        1. Create a new project for an LED circuit
        2. Add the following components:
           - LED
           - Current limiting resistor
           - Power source connections (VCC and GND)
        3. Connect all components properly
        4. Calculate the appropriate resistor value for the LED
        5. Validate the circuit design

        Circuit specifications:
        - Supply voltage: [Enter voltage, e.g., 5V, 3.3V]
        - LED forward voltage: [Enter LED Vf, e.g., 2.1V]
        - LED forward current: [Enter LED If, e.g., 20mA]
        - Project location: [Enter directory path]

        Please create the complete circuit with proper component values.
        """
        return prompt.strip()

    @mcp.prompt()
    def create_power_supply_circuit() -> str:
        """Prompt for creating a power supply circuit."""
        prompt = """
        I need to design a power supply circuit in KiCad. Can you help me create:

        1. A new KiCad project for the power supply
        2. Input power connector
        3. Voltage regulator circuit (linear or switching)
        4. Input and output filtering capacitors
        5. Protection components if needed
        6. Power indicator LED
        7. Output connector

        Power supply specifications:
        - Input voltage range: [e.g., 7-12V DC]
        - Output voltage: [e.g., 5V, 3.3V]
        - Output current: [e.g., 500mA, 1A]
        - Regulation type: [Linear/Switching]
        - Project location: [Enter directory path]

        Please create a complete power supply schematic with appropriate component values.
        """
        return prompt.strip()

    @mcp.prompt()
    def create_microcontroller_circuit() -> str:
        """Prompt for creating a basic microcontroller circuit."""
        prompt = """
        I want to create a microcontroller-based circuit in KiCad. Please help me:

        1. Create a new project for the microcontroller circuit
        2. Add a microcontroller (Arduino-compatible or specific MCU)
        3. Add power supply connections and decoupling capacitors
        4. Add crystal oscillator circuit if needed
        5. Add programming/debug connector
        6. Add basic I/O connections (LEDs, buttons, headers)
        7. Add power indicator and status LEDs

        Circuit specifications:
        - Microcontroller type: [e.g., ATmega328P, ESP32, STM32]
        - Operating voltage: [e.g., 3.3V, 5V]
        - Crystal frequency: [e.g., 16MHz, 8MHz]
        - I/O requirements: [Describe needed pins/connectors]
        - Project location: [Enter directory path]

        Please create a complete microcontroller circuit with all necessary support components.
        """
        return prompt.strip()

    @mcp.prompt()
    def create_amplifier_circuit() -> str:
        """Prompt for creating an amplifier circuit."""
        prompt = """
        I need to design an amplifier circuit in KiCad. Can you help me create:

        1. A new KiCad project for the amplifier
        2. Op-amp or transistor-based amplifier circuit
        3. Input and output coupling/filtering
        4. Bias and feedback networks
        5. Power supply connections
        6. Input/output connectors

        Amplifier specifications:
        - Amplifier type: [Op-amp/Transistor/Instrumentation]
        - Gain required: [e.g., 10x, 100x]
        - Frequency range: [e.g., Audio, DC-100kHz]
        - Input impedance: [e.g., High/Low/Specific value]
        - Power supply: [e.g., ±15V, Single 5V]
        - Project location: [Enter directory path]

        Please design a complete amplifier circuit with proper component selection.
        """
        return prompt.strip()

    @mcp.prompt()
    def create_filter_circuit() -> str:
        """Prompt for creating a filter circuit."""
        prompt = """
        I want to design a filter circuit in KiCad. Please help me:

        1. Create a new project for the filter circuit
        2. Design the filter topology (active/passive)
        3. Calculate and place appropriate components
        4. Add input/output connectors
        5. Add power connections if needed (for active filters)
        6. Validate the filter design

        Filter specifications:
        - Filter type: [Low-pass/High-pass/Band-pass/Band-stop]
        - Filter implementation: [Active/Passive]
        - Cutoff frequency: [e.g., 1kHz, 10kHz]
        - Filter order: [1st/2nd/3rd order]
        - Power supply (if active): [e.g., ±15V, Single 5V]
        - Project location: [Enter directory path]

        Please create a complete filter circuit with calculated component values.
        """
        return prompt.strip()

    @mcp.prompt()
    def add_components_to_existing() -> str:
        """Prompt for adding components to an existing circuit."""
        prompt = """
        I have an existing KiCad project and want to add components to it. Can you help me:

        1. Open my existing project
        2. Add new components to the schematic
        3. Connect the new components to existing circuit
        4. Update component values if needed
        5. Validate the updated circuit

        Existing project:
        - Project path: [Enter path to .kicad_pro file]

        Components to add:
        - Component list: [Describe what components you want to add]
        - Connection requirements: [How should they connect to existing circuit]
        - Specific values: [Any specific component values needed]

        Please help me extend my existing circuit design.
        """
        return prompt.strip()

    @mcp.prompt()
    def troubleshoot_circuit() -> str:
        """Prompt for troubleshooting circuit issues."""
        prompt = """
        I have a KiCad circuit design that needs troubleshooting. Can you help me:

        1. Analyze my existing schematic
        2. Check for common design issues
        3. Validate component connections
        4. Verify component values and ratings
        5. Suggest improvements or fixes

        Project information:
        - Project path: [Enter path to .kicad_pro file]
        - Issue description: [Describe the problem you're experiencing]
        - Expected behavior: [What should the circuit do]
        - Observed behavior: [What is actually happening]

        Please analyze my circuit and suggest solutions for any issues found.
        """
        return prompt.strip()

    @mcp.prompt()
    def convert_breadboard_to_pcb() -> str:
        """Prompt for converting a breadboard circuit to KiCad schematic."""
        prompt = """
        I have a working breadboard circuit that I want to convert to a proper KiCad schematic. Can you help me:

        1. Create a new KiCad project
        2. Recreate the breadboard circuit as a schematic
        3. Add proper component references and values
        4. Organize the schematic for clarity
        5. Validate the converted design

        Breadboard circuit details:
        - Circuit description: [Describe what your breadboard circuit does]
        - Component list: [List all components used]
        - Connection details: [Describe how components are connected]
        - Operating voltage: [Power supply voltage]
        - Project location: [Enter directory path]

        Please help me create a clean, professional schematic from my breadboard prototype.
        """
        return prompt.strip()

    @mcp.prompt()
    def create_sensor_interface() -> str:
        """Prompt for creating a sensor interface circuit."""
        prompt = """
        I need to create a sensor interface circuit in KiCad. Can you help me:

        1. Create a new project for the sensor interface
        2. Add appropriate signal conditioning circuits
        3. Add protection and filtering components
        4. Add connectors for sensor and output
        5. Add power supply and indicator circuits

        Sensor interface specifications:
        - Sensor type: [e.g., Temperature, Pressure, Current, Voltage]
        - Sensor output: [e.g., 0-5V, 4-20mA, Digital]
        - Required conditioning: [Amplification, Filtering, Level shifting]
        - Output interface: [Analog, Digital, Communication protocol]
        - Power requirements: [Operating voltage and current]
        - Project location: [Enter directory path]

        Please design a complete sensor interface circuit with proper signal conditioning.
        """
        return prompt.strip()
