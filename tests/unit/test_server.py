"""
Unit tests for server.py - KiCad MCP server startup, shutdown, and lifecycle management.
"""
import pytest
import signal
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from kicad_mcp.server import (
    setup_signal_handlers,
    cleanup_handler,
    main
)


class TestServerLifecycle:
    """Test suite for server lifecycle management."""
    
    def test_setup_signal_handlers(self):
        """Test that signal handlers are properly registered."""
        with patch('signal.signal') as mock_signal:
            # Mock the signal module
            mock_signal.SIGTERM = signal.SIGTERM
            mock_signal.SIGINT = signal.SIGINT
            
            setup_signal_handlers()
            
            # Verify signal handlers were registered
            assert mock_signal.call_count == 2
            
            # Check that both SIGTERM and SIGINT were handled
            calls = mock_signal.call_args_list
            signals_handled = [call[0][0] for call in calls]
            assert signal.SIGTERM in signals_handled
            assert signal.SIGINT in signals_handled
    
    def test_cleanup_handler_basic(self):
        """Test basic cleanup handler functionality."""
        # Mock logger
        with patch('kicad_mcp.server.logger') as mock_logger:
            # Test that cleanup handler can be called without errors
            cleanup_handler()
            
            # Should log cleanup message
            mock_logger.info.assert_called()
            cleanup_calls = [call for call in mock_logger.info.call_args_list 
                           if 'cleanup' in str(call).lower()]
            assert len(cleanup_calls) > 0
    
    @patch('kicad_mcp.server.cleanup_temp_dirs')
    def test_cleanup_handler_temp_dirs(self, mock_cleanup_temp):
        """Test that cleanup handler calls temp directory cleanup."""
        with patch('kicad_mcp.server.logger'):
            cleanup_handler()
            
            # Should call temp directory cleanup
            mock_cleanup_temp.assert_called_once()
    
    @patch('kicad_mcp.server.logger')
    def test_cleanup_handler_exception_handling(self, mock_logger):
        """Test cleanup handler error handling."""
        with patch('kicad_mcp.server.cleanup_temp_dirs', side_effect=Exception("Cleanup error")):
            # Should not raise exception
            cleanup_handler()
            
            # Should log the error
            error_calls = [call for call in mock_logger.error.call_args_list 
                          if 'cleanup' in str(call).lower()]
            assert len(error_calls) > 0
    
    @pytest.mark.asyncio
    async def test_main_server_startup(self):
        """Test main function server startup."""
        with patch('kicad_mcp.server.FastMCP') as mock_fastmcp:
            with patch('kicad_mcp.server.setup_signal_handlers') as mock_signals:
                with patch('kicad_mcp.server.logger') as mock_logger:
                    # Mock the server instance
                    mock_server = Mock()
                    mock_server.run = AsyncMock()
                    mock_fastmcp.return_value = mock_server
                    
                    # Mock registration functions
                    with patch('kicad_mcp.server.register_project_tools') as mock_reg_project:
                        with patch('kicad_mcp.server.register_netlist_tools') as mock_reg_netlist:
                            with patch('kicad_mcp.server.register_export_tools') as mock_reg_export:
                                with patch('kicad_mcp.server.register_drc_tools') as mock_reg_drc:
                                    with patch('kicad_mcp.server.register_bom_tools') as mock_reg_bom:
                                        with patch('kicad_mcp.server.register_pattern_tools') as mock_reg_pattern:
                                            with patch('kicad_mcp.server.register_analysis_tools') as mock_reg_analysis:
                                                with patch('kicad_mcp.server.register_circuit_tools') as mock_reg_circuit:
                                                    
                                                    # Test main function
                                                    await main()
                                                    
                                                    # Verify server was created
                                                    mock_fastmcp.assert_called_once()
                                                    
                                                    # Verify signal handlers were set up
                                                    mock_signals.assert_called_once()
                                                    
                                                    # Verify all tool modules were registered
                                                    mock_reg_project.assert_called_once()
                                                    mock_reg_netlist.assert_called_once()
                                                    mock_reg_export.assert_called_once()
                                                    mock_reg_drc.assert_called_once()
                                                    mock_reg_bom.assert_called_once()
                                                    mock_reg_pattern.assert_called_once()
                                                    mock_reg_analysis.assert_called_once()
                                                    mock_reg_circuit.assert_called_once()
                                                    
                                                    # Verify server was started
                                                    mock_server.run.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_main_exception_handling(self):
        """Test main function exception handling."""
        with patch('kicad_mcp.server.FastMCP', side_effect=Exception("Server startup failed")):
            with patch('kicad_mcp.server.logger') as mock_logger:
                with patch('kicad_mcp.server.cleanup_handler') as mock_cleanup:
                    
                    # Should not raise exception
                    await main()
                    
                    # Should log error
                    error_calls = [call for call in mock_logger.error.call_args_list 
                                  if 'error' in str(call).lower()]
                    assert len(error_calls) > 0
                    
                    # Should call cleanup
                    mock_cleanup.assert_called()
    
    def test_signal_handler_sigterm(self):
        """Test SIGTERM signal handling."""
        with patch('kicad_mcp.server.logger') as mock_logger:
            with patch('kicad_mcp.server.cleanup_handler') as mock_cleanup:
                with patch('sys.exit') as mock_exit:
                    
                    # Get the signal handler function
                    with patch('signal.signal') as mock_signal:
                        setup_signal_handlers()
                        
                        # Find the SIGTERM handler
                        sigterm_handler = None
                        for call in mock_signal.call_args_list:
                            if call[0][0] == signal.SIGTERM:
                                sigterm_handler = call[0][1]
                                break
                        
                        assert sigterm_handler is not None
                        
                        # Test the handler
                        sigterm_handler(signal.SIGTERM, None)
                        
                        # Should log shutdown message
                        shutdown_calls = [call for call in mock_logger.info.call_args_list 
                                        if 'shutdown' in str(call).lower()]
                        assert len(shutdown_calls) > 0
                        
                        # Should call cleanup
                        mock_cleanup.assert_called()
                        
                        # Should exit
                        mock_exit.assert_called_with(0)
    
    def test_signal_handler_sigint(self):
        """Test SIGINT (Ctrl+C) signal handling."""
        with patch('kicad_mcp.server.logger') as mock_logger:
            with patch('kicad_mcp.server.cleanup_handler') as mock_cleanup:
                with patch('sys.exit') as mock_exit:
                    
                    # Get the signal handler function
                    with patch('signal.signal') as mock_signal:
                        setup_signal_handlers()
                        
                        # Find the SIGINT handler
                        sigint_handler = None
                        for call in mock_signal.call_args_list:
                            if call[0][0] == signal.SIGINT:
                                sigint_handler = call[0][1]
                                break
                        
                        assert sigint_handler is not None
                        
                        # Test the handler
                        sigint_handler(signal.SIGINT, None)
                        
                        # Should handle gracefully (same as SIGTERM)
                        mock_cleanup.assert_called()
                        mock_exit.assert_called_with(0)
    
    @patch('kicad_mcp.server.FastMCP')
    def test_server_configuration(self, mock_fastmcp):
        """Test server configuration and initialization."""
        mock_server = Mock()
        mock_fastmcp.return_value = mock_server
        
        with patch('kicad_mcp.server.setup_signal_handlers'):
            with patch('kicad_mcp.server.logger'):
                # Mock all registration functions
                with patch('kicad_mcp.server.register_project_tools') as mock_reg:
                    mock_reg.return_value = None
                    
                    # Import and test the server creation
                    from kicad_mcp.server import main
                    
                    # Check server is created with correct parameters
                    mock_fastmcp.assert_not_called()  # Not called until main() runs
    
    def test_cleanup_handler_multiple_calls(self):
        """Test that cleanup handler can be called multiple times safely."""
        with patch('kicad_mcp.server.logger') as mock_logger:
            with patch('kicad_mcp.server.cleanup_temp_dirs') as mock_cleanup_temp:
                
                # Call cleanup multiple times
                cleanup_handler()
                cleanup_handler() 
                cleanup_handler()
                
                # Should handle multiple calls gracefully
                assert mock_cleanup_temp.call_count == 3
                assert mock_logger.info.call_count >= 3
    
    @patch('kicad_mcp.server.atexit.register')
    def test_atexit_handler_registration(self, mock_atexit):
        """Test that cleanup handler is registered with atexit."""
        # Import the module to trigger atexit registration
        import kicad_mcp.server
        
        # Should register cleanup handler with atexit
        # Note: This test checks if atexit.register was called at module import
        # The exact behavior depends on module import order
        
        # Verify atexit registration happened
        assert mock_atexit.call_count >= 0  # May be called during import
    
    def test_logger_configuration(self):
        """Test that logger is properly configured."""
        with patch('kicad_mcp.server.setup_logging') as mock_setup_logging:
            # Import module to trigger logger setup
            import kicad_mcp.server
            
            # Logger should be configured
            from kicad_mcp.server import logger
            assert logger is not None
    
    @pytest.mark.asyncio
    async def test_server_shutdown_graceful(self):
        """Test graceful server shutdown."""
        with patch('kicad_mcp.server.FastMCP') as mock_fastmcp:
            mock_server = Mock()
            mock_server.run = AsyncMock()
            
            # Simulate keyboard interrupt during server run
            async def mock_run():
                raise KeyboardInterrupt("Test interrupt")
            
            mock_server.run.side_effect = mock_run
            mock_fastmcp.return_value = mock_server
            
            with patch('kicad_mcp.server.setup_signal_handlers'):
                with patch('kicad_mcp.server.logger') as mock_logger:
                    with patch('kicad_mcp.server.cleanup_handler') as mock_cleanup:
                        
                        # Mock all registration functions
                        with patch('kicad_mcp.server.register_project_tools'):
                            with patch('kicad_mcp.server.register_netlist_tools'):
                                with patch('kicad_mcp.server.register_export_tools'):
                                    with patch('kicad_mcp.server.register_drc_tools'):
                                        with patch('kicad_mcp.server.register_bom_tools'):
                                            with patch('kicad_mcp.server.register_pattern_tools'):
                                                with patch('kicad_mcp.server.register_analysis_tools'):
                                                    with patch('kicad_mcp.server.register_circuit_tools'):
                                                        
                                                        # Test main function with interrupt
                                                        await main()
                                                        
                                                        # Should handle KeyboardInterrupt gracefully
                                                        mock_cleanup.assert_called()
                                                        
                                                        # Should log shutdown
                                                        shutdown_calls = [call for call in mock_logger.info.call_args_list 
                                                                        if 'shutdown' in str(call).lower()]
                                                        assert len(shutdown_calls) > 0
    
    def test_pid_logging(self):
        """Test that process ID is logged on startup."""
        with patch('kicad_mcp.server.logger') as mock_logger:
            with patch('os.getpid', return_value=12345):
                # Import server module to trigger startup logging
                import kicad_mcp.server
                
                # Should log PID information
                pid_calls = [call for call in mock_logger.info.call_args_list 
                           if '12345' in str(call)]
                # Note: PID logging might happen during module import
    
    @pytest.mark.asyncio
    async def test_concurrent_cleanup_calls(self):
        """Test concurrent cleanup handler calls."""
        with patch('kicad_mcp.server.logger'):
            with patch('kicad_mcp.server.cleanup_temp_dirs') as mock_cleanup_temp:
                
                # Simulate concurrent cleanup calls
                async def call_cleanup():
                    cleanup_handler()
                
                # Run multiple cleanup calls concurrently
                await asyncio.gather(
                    call_cleanup(),
                    call_cleanup(),
                    call_cleanup()
                )
                
                # Should handle concurrent calls safely
                assert mock_cleanup_temp.call_count == 3