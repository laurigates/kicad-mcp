"""
HTTP client abstraction for MCP server testing.

Provides unified interface for HTTP communication with the MCP server
using different backends (requests, curl, httpie).
"""

from abc import ABC, abstractmethod
import json
import subprocess
from typing import Any

import httpx


class HTTPClientError(Exception):
    """Base exception for HTTP client errors."""

    pass


class HTTPClient(ABC):
    """Abstract base class for HTTP clients."""

    def __init__(self, base_url: str, timeout: int = 30):
        """Initialize HTTP client.

        Args:
            base_url: Base URL for the MCP server
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @abstractmethod
    def post(
        self, path: str, data: dict[str, Any], headers: dict[str, str] | None = None
    ) -> dict[str, Any]:
        """Send POST request to the server.

        Args:
            path: URL path (will be appended to base_url)
            data: JSON data to send
            headers: Optional additional headers

        Returns:
            JSON response data

        Raises:
            HTTPClientError: If request fails
        """
        pass

    @abstractmethod
    def post_with_headers(
        self, path: str, data: dict[str, Any], headers: dict[str, str] | None = None
    ) -> tuple[dict[str, Any], dict[str, str]]:
        """Send POST request and return both response data and headers.

        Args:
            path: URL path (will be appended to base_url)
            data: JSON data to send
            headers: Optional additional headers

        Returns:
            Tuple of (JSON response data, response headers)

        Raises:
            HTTPClientError: If request fails
        """
        pass

    @abstractmethod
    def get(self, path: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
        """Send GET request to the server.

        Args:
            path: URL path (will be appended to base_url)
            headers: Optional additional headers

        Returns:
            JSON response data

        Raises:
            HTTPClientError: If request fails
        """
        pass

    def health_check(self) -> bool:
        """Check if server is responding.

        Returns:
            True if server is healthy, False otherwise
        """
        try:
            # Try a simple GET request to check connectivity
            # Even if it returns 404, it means the server is running
            self.get("/")
            return True
        except HTTPClientError as e:
            # If we get an HTTP error response, the server is running
            return "HTTP" in str(e) and ("404" in str(e) or "405" in str(e))
        except Exception:
            return False


class RequestsHTTPClient(HTTPClient):
    """HTTP client using httpx library."""

    def __init__(self, base_url: str, timeout: int = 30):
        """Initialize requests-based HTTP client."""
        super().__init__(base_url, timeout)
        self.client = httpx.Client(timeout=timeout)

    def post(
        self, path: str, data: dict[str, Any], headers: dict[str, str] | None = None
    ) -> dict[str, Any]:
        """Send POST request using httpx."""
        url = f"{self.base_url}{path}"

        # Prepare headers for MCP StreamableHTTP
        request_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if headers:
            request_headers.update(headers)

        try:
            response = self.client.post(url, json=data, headers=request_headers)
            response.raise_for_status()

            # Handle different response types
            content_type = response.headers.get("content-type", "").lower()
            if content_type.startswith("text/event-stream"):
                # Parse SSE response and extract JSON from the data field
                return self._parse_sse_response(response.text)
            else:
                # Standard JSON response
                return response.json()
        except httpx.RequestError as e:
            raise HTTPClientError(f"Request failed: {e}") from e
        except httpx.HTTPStatusError as e:
            raise HTTPClientError(f"HTTP {e.response.status_code}: {e.response.text}") from e
        except json.JSONDecodeError as e:
            raise HTTPClientError(f"Invalid JSON response: {e}") from e

    def post_with_headers(
        self, path: str, data: dict[str, Any], headers: dict[str, str] | None = None
    ) -> tuple[dict[str, Any], dict[str, str]]:
        """Send POST request and return both response data and headers."""
        url = f"{self.base_url}{path}"

        # Prepare headers for MCP StreamableHTTP
        request_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if headers:
            request_headers.update(headers)

        try:
            response = self.client.post(url, json=data, headers=request_headers)
            response.raise_for_status()

            # Handle different response types
            content_type = response.headers.get("content-type", "").lower()
            if content_type.startswith("text/event-stream"):
                # Parse SSE response and extract JSON from the data field
                response_data = self._parse_sse_response(response.text)
            else:
                # Standard JSON response
                response_data = response.json()

            # Return both data and headers
            return response_data, dict(response.headers)
        except httpx.RequestError as e:
            raise HTTPClientError(f"Request failed: {e}") from e
        except httpx.HTTPStatusError as e:
            raise HTTPClientError(f"HTTP {e.response.status_code}: {e.response.text}") from e
        except json.JSONDecodeError as e:
            raise HTTPClientError(f"Invalid JSON response: {e}") from e

    def _parse_sse_response(self, sse_text: str) -> dict[str, Any]:
        """Parse Server-Sent Events response and extract JSON data.

        Args:
            sse_text: Raw SSE response text

        Returns:
            Parsed JSON data from the SSE event

        Raises:
            HTTPClientError: If SSE parsing fails
        """
        try:
            # SSE format: "event: message\ndata: {json}\n\n"
            lines = sse_text.strip().split("\n")
            for line in lines:
                if line.startswith("data: "):
                    json_data = line[6:]  # Remove "data: " prefix
                    return json.loads(json_data)

            raise HTTPClientError("No data field found in SSE response")
        except json.JSONDecodeError as e:
            raise HTTPClientError(f"Invalid JSON in SSE data field: {e}") from e
        except Exception as e:
            raise HTTPClientError(f"Failed to parse SSE response: {e}") from e

    def get(self, path: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
        """Send GET request using httpx."""
        url = f"{self.base_url}{path}"

        # Prepare headers
        request_headers = {"Accept": "application/json"}
        if headers:
            request_headers.update(headers)

        try:
            response = self.client.get(url, headers=request_headers)
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            raise HTTPClientError(f"Request failed: {e}") from e
        except httpx.HTTPStatusError as e:
            raise HTTPClientError(f"HTTP {e.response.status_code}: {e.response.text}") from e
        except json.JSONDecodeError as e:
            raise HTTPClientError(f"Invalid JSON response: {e}") from e

    def __del__(self):
        """Clean up HTTP client."""
        if hasattr(self, "client"):
            self.client.close()


class CurlHTTPClient(HTTPClient):
    """HTTP client using curl command."""

    def post(
        self, path: str, data: dict[str, Any], headers: dict[str, str] | None = None
    ) -> dict[str, Any]:
        """Send POST request using curl."""
        url = f"{self.base_url}{path}"

        # Build curl command with MCP headers
        curl_cmd = [
            "curl",
            "-X",
            "POST",
            "-H",
            "Content-Type: application/json",
            "-H",
            "Accept: application/json, text/event-stream",
        ]

        # Add custom headers
        if headers:
            for key, value in headers.items():
                curl_cmd.extend(["-H", f"{key}: {value}"])

        curl_cmd.extend(
            [
                "-d",
                json.dumps(data),
                "--max-time",
                str(self.timeout),
                "--silent",
                "--show-error",
                "--fail",
                url,
            ]
        )

        try:
            result = subprocess.run(curl_cmd, capture_output=True, text=True, check=True)
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            raise HTTPClientError(f"Curl failed: {e.stderr}") from e
        except json.JSONDecodeError as e:
            raise HTTPClientError(f"Invalid JSON response: {e}") from e

    def post_with_headers(
        self, path: str, data: dict[str, Any], headers: dict[str, str] | None = None
    ) -> tuple[dict[str, Any], dict[str, str]]:
        """Send POST request and return both response data and headers."""
        url = f"{self.base_url}{path}"

        # Build curl command with MCP headers
        curl_cmd = [
            "curl",
            "-X",
            "POST",
            "-H",
            "Content-Type: application/json",
            "-H",
            "Accept: application/json, text/event-stream",
            "-i",  # Include response headers
        ]

        # Add custom headers
        if headers:
            for key, value in headers.items():
                curl_cmd.extend(["-H", f"{key}: {value}"])

        curl_cmd.extend(
            [
                "-d",
                json.dumps(data),
                "--max-time",
                str(self.timeout),
                "--silent",
                "--show-error",
                "--fail",
                url,
            ]
        )

        try:
            result = subprocess.run(curl_cmd, capture_output=True, text=True, check=True)

            # Parse headers and body from curl -i output
            response_text = result.stdout
            header_section, body_section = response_text.split("\r\n\r\n", 1)

            # Parse headers
            response_headers = {}
            for line in header_section.split("\n")[1:]:  # Skip status line
                if ":" in line:
                    key, value = line.split(":", 1)
                    response_headers[key.strip().lower()] = value.strip()

            # Parse body (handle SSE format)
            content_type = response_headers.get("content-type", "").lower()
            if content_type.startswith("text/event-stream"):
                # Parse SSE response
                response_data = self._parse_sse_response_curl(body_section)
            else:
                response_data = json.loads(body_section)

            return response_data, response_headers
        except subprocess.CalledProcessError as e:
            raise HTTPClientError(f"Curl failed: {e.stderr}") from e
        except json.JSONDecodeError as e:
            raise HTTPClientError(f"Invalid JSON response: {e}") from e

    def _parse_sse_response_curl(self, sse_text: str) -> dict[str, Any]:
        """Parse SSE response for curl (same logic as httpx version)."""
        try:
            lines = sse_text.strip().split("\n")
            for line in lines:
                if line.startswith("data: "):
                    json_data = line[6:]  # Remove "data: " prefix
                    return json.loads(json_data)

            raise HTTPClientError("No data field found in SSE response")
        except json.JSONDecodeError as e:
            raise HTTPClientError(f"Invalid JSON in SSE data field: {e}") from e
        except Exception as e:
            raise HTTPClientError(f"Failed to parse SSE response: {e}") from e

    def get(self, path: str, headers: dict[str, str] | None = None) -> dict[str, Any]:
        """Send GET request using curl."""
        url = f"{self.base_url}{path}"

        # Build curl command with headers
        curl_cmd = [
            "curl",
            "-H",
            "Accept: application/json",
        ]

        # Add custom headers
        if headers:
            for key, value in headers.items():
                curl_cmd.extend(["-H", f"{key}: {value}"])

        curl_cmd.extend(
            [
                "--max-time",
                str(self.timeout),
                "--silent",
                "--show-error",
                "--fail",
                url,
            ]
        )

        try:
            result = subprocess.run(curl_cmd, capture_output=True, text=True, check=True)
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            raise HTTPClientError(f"Curl failed: {e.stderr}") from e
        except json.JSONDecodeError as e:
            raise HTTPClientError(f"Invalid JSON response: {e}") from e


def create_http_client(base_url: str, backend: str = "auto", timeout: int = 30) -> HTTPClient:
    """Create an HTTP client with the specified backend.

    Args:
        base_url: Base URL for the MCP server
        backend: Backend to use ("requests", "curl", or "auto")
        timeout: Request timeout in seconds

    Returns:
        Configured HTTP client

    Raises:
        HTTPClientError: If backend is not available
    """
    if backend == "auto":
        # Try requests first, fall back to curl
        try:
            return RequestsHTTPClient(base_url, timeout)
        except ImportError:
            backend = "curl"

    if backend == "requests":
        return RequestsHTTPClient(base_url, timeout)
    elif backend == "curl":
        # Check if curl is available
        try:
            subprocess.run(["curl", "--version"], capture_output=True, check=True, timeout=5)
            return CurlHTTPClient(base_url, timeout)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            raise HTTPClientError(f"Curl not available: {e}") from e
    else:
        raise HTTPClientError(f"Unknown backend: {backend}")


def mcp_initialize_session(client: HTTPClient) -> str:
    """Initialize MCP session and return session ID.

    Args:
        client: HTTP client to use

    Returns:
        Session ID for subsequent requests

    Raises:
        HTTPClientError: If initialization fails
    """
    # Step 1: Send initialize request
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "kicad-mcp-http-test", "version": "1.0.0"},
        },
    }

    # Make the request and capture session ID from response headers
    response, headers = client.post_with_headers("/mcp/", init_request)

    if "error" in response:
        error_info = response["error"]
        error_msg = f"MCP initialize error: {error_info.get('message', 'Unknown error')}"
        if "code" in error_info:
            error_msg += f" (code: {error_info['code']})"
        raise HTTPClientError(error_msg)

    # Extract session ID from response headers
    session_id = headers.get("mcp-session-id")
    if not session_id:
        raise HTTPClientError("Server did not provide session ID in response headers")

    # Step 2: Send initialized notification (required by MCP spec)
    initialized_notification = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
        "params": {},
    }

    # Add session header for the notification
    headers_with_session = {"mcp-session-id": session_id}

    # Send the initialized notification (notifications typically return empty response)
    try:
        client.post("/mcp/", initialized_notification, headers_with_session)
    except HTTPClientError as e:
        # Notifications may return empty response (202 Accepted), which is normal
        if "Invalid JSON response" in str(e):
            pass  # This is expected for notifications
        else:
            raise

    return session_id


def mcp_tool_call(
    client: HTTPClient,
    tool_name: str,
    params: dict[str, Any],
    session_id: str | None = None,
) -> dict[str, Any]:
    """Make an MCP tool call via HTTP.

    Args:
        client: HTTP client to use
        tool_name: Name of the MCP tool to call
        params: Parameters for the tool
        session_id: Optional session ID for stateful requests

    Returns:
        Tool call result

    Raises:
        HTTPClientError: If tool call fails
    """
    # If no session ID provided, initialize a session first
    if session_id is None:
        session_id = mcp_initialize_session(client)

    # MCP uses JSON-RPC 2.0 format for tool calls
    mcp_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": params},
    }

    # Add session header
    headers = {"mcp-session-id": session_id}

    # MCP StreamableHTTP expects requests to the /mcp/ path by default
    response = client.post("/mcp/", mcp_request, headers)

    if "error" in response:
        error_info = response["error"]
        error_msg = f"MCP error: {error_info.get('message', 'Unknown error')}"
        if "code" in error_info:
            error_msg += f" (code: {error_info['code']})"
        raise HTTPClientError(error_msg)

    return response.get("result", {})
