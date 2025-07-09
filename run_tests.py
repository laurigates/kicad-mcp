#!/usr/bin/env python3
"""
Test runner script for KiCad MCP Server.

This script provides a centralized way to run tests with proper configuration
and reporting. It follows TDD principles by ensuring tests are properly
organized and can be run in isolation or as a complete suite.
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description):
    """Run a command and return the result."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.stdout:
        print("STDOUT:")
        print(result.stdout)
    
    if result.stderr:
        print("STDERR:")
        print(result.stderr)
    
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description='Run KiCad MCP Server tests')
    parser.add_argument('--unit', action='store_true', 
                       help='Run unit tests only')
    parser.add_argument('--integration', action='store_true', 
                       help='Run integration tests only')
    parser.add_argument('--coverage', action='store_true', 
                       help='Run with coverage reporting')
    parser.add_argument('--verbose', '-v', action='store_true', 
                       help='Verbose output')
    parser.add_argument('--module', '-m', type=str, 
                       help='Run tests for specific module (e.g., test_component_layout)')
    parser.add_argument('--no-capture', action='store_true', 
                       help='Do not capture stdout/stderr (useful for debugging)')
    
    args = parser.parse_args()
    
    # Set up base directory
    base_dir = Path(__file__).parent
    
    # Build pytest command
    cmd = [sys.executable, '-m', 'pytest']
    
    # Add verbosity
    if args.verbose:
        cmd.append('-v')
    
    # Add no-capture flag
    if args.no_capture:
        cmd.append('-s')
    
    # Add coverage if requested
    if args.coverage:
        cmd.extend(['--cov=kicad_mcp', '--cov-report=html', '--cov-report=term'])
    
    # Determine test path
    if args.module:
        # Run specific module
        module_path = base_dir / 'tests' / 'unit' / 'utils' / f'{args.module}.py'
        if not module_path.exists():
            module_path = base_dir / 'tests' / 'integration' / f'{args.module}.py'
        
        if not module_path.exists():
            print(f"Error: Module {args.module} not found in tests/unit/utils/ or tests/integration/")
            return False
            
        cmd.append(str(module_path))
    elif args.unit:
        cmd.append(str(base_dir / 'tests' / 'unit'))
    elif args.integration:
        cmd.append(str(base_dir / 'tests' / 'integration'))
    else:
        # Run all tests
        cmd.append(str(base_dir / 'tests'))
    
    # Run the tests
    success = run_command(cmd, "KiCad MCP Server Tests")
    
    if success:
        print("\n✅ All tests passed!")
        return True
    else:
        print("\n❌ Some tests failed!")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)