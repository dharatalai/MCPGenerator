import httpx
import logging
from typing import Dict, Any, List, Optional
import json

logger = logging.getLogger(__name__)

# Custom Exception for Kite Connect specific errors
class KiteConnectError(Exception):
    """Represents an error returned by the Kite Connect API."""
    def __init__(self, message: str, error_type: str = "GeneralError", status_code: Optional[int] = None):
        self.message = message
        self.error_type = error_type
        self.status_code = status_code
        super().__init__(f"[{error_type}/{status_code}] {message}")

class KiteConnectClient:
    """Asynchronous client for interacting with the Zerodha Kite Connect API (v3)."""

    def __init__(self, api_key: str, access_token: str, base_url: str = "https://api.kite.trade"):
        """
        Initializes the KiteConnectClient.

        Args:
            api_key: Your Kite Connect API key.
            access_token: The access token obtained after successful login.
            base_url: The base URL for the Kite Connect API (default: https://api.kite.trade).
        """
        if not api_key or not access_token:
            raise ValueError("API key and access token are required.")

        self.api_key = api_key
        self.access_token = access_token
        self.base_url = base_url.rstrip('/')
        self._headers = {
            "X-Kite-Version": "3",
            "Authorization": f"token {self.api_key}:{self.access_token}",
            "Content-Type": "application/x-www-form-urlencoded" # Kite uses form encoding
        }
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self._headers,
            timeout=30.0, # Default timeout for requests
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20), # Default limits
            event_hooks={'response': [self._log_response]}
        )

    async def _log_response(self, response: httpx.Response):
        """Hook to log response status before raising exceptions."""
        await response.aread()
        logger.debug(f"Request: {response.request.method} {response.request.url}")
        logger.debug(f"Response Status: {response.status_code}")
        # Avoid logging potentially sensitive data in production by default
        # logger.debug(f"Response Body: {response.text}")

    async def _request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any] | List[Dict[str, Any]]:
        """Makes an asynchronous request to the Kite Connect API."""
        url = f"{self.base_url}{endpoint}"
        try:
            # Filter out None values from data payload
            filtered_data = {k: v for k, v in data.items() if v is not None} if data else None

            response = await self.client.request(
                method=method,
                url=url,
                params=params, # For GET requests
                data=filtered_data # For POST/PUT/DELETE (form-encoded)
            )

            # Check for specific Kite Connect error structure first
            try:
                response_data = response.json()
                if response.status_code >= 400:
                    error_type = response_data.get("error_type", "UnknownError")
                    message = response_data.get("message", "No error message provided.")
                    logger.error(f"Kite API Error ({response.status_code}): {error_type} - {message} for {method} {url}")
                    raise KiteConnectError(message, error_type, response.status_code)

                # Check if 'data' key exists and return its content, otherwise return the full response
                # Common pattern in Kite API responses
                return response_data.get("data", response_data)

            except json.JSONDecodeError:
                # If response is not JSON, still check status code
                if response.status_code >= 400:
                    logger.error(f"Kite API Error ({response.status_code}): Non-JSON response for {method} {url}. Body: {response.text[:500]}")
                    raise KiteConnectError(f"API returned status {response.status_code} with non-JSON body: {response.text[:200]}", "NetworkError", response.status_code)
                else:
                    # Handle successful non-JSON responses if any exist (unlikely for Kite v3)
                    logger.warning(f"Received non-JSON success response ({response.status_code}) for {method} {url}")
                    return {"status": "success", "message": "Received non-JSON success response", "content": response.text}

        except httpx.TimeoutException as e:
            logger.error(f"Request timed out: {method} {url} - {e}")
            raise KiteConnectError("The request timed out.", "NetworkError") from e
        except httpx.RequestError as e:
            logger.error(f"Request error: {method} {url} - {e}")
            # E.g., DNS errors, connection refused
            raise KiteConnectError(f"Network request failed: {e}", "NetworkError") from e
        except KiteConnectError: # Re-raise specific Kite errors
            raise
        except Exception as e:
            logger.exception(f"An unexpected error occurred during the API request: {method} {url} - {e}")
            raise KiteConnectError(f"An unexpected error occurred: {str(e)}", "ServerError") from e

    async def place_order(self, variety: str, data: Dict[str, Any]) -> Dict[str, str]:
        """Place an order."""
        endpoint = f"/orders/{variety}"
        response = await self._request("POST", endpoint, data=data)
        if isinstance(response, dict) and 'order_id' in response:
            return {"order_id": str(response['order_id'])}
        logger.error(f"Place order response did not contain 'order_id': {response}")
        raise KiteConnectError("Invalid response format from place_order", "ServerError")

    async def modify_order(self, variety: str, order_id: str, data: Dict[str, Any]) -> Dict[str, str]:
        """Modify an order."""
        endpoint = f"/orders/{variety}/{order_id}"
        response = await self._request("PUT", endpoint, data=data)
        if isinstance(response, dict) and 'order_id' in response:
            return {"order_id": str(response['order_id'])}
        logger.error(f"Modify order response did not contain 'order_id': {response}")
        raise KiteConnectError("Invalid response format from modify_order", "ServerError")

    async def cancel_order(self, variety: str, order_id: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """Cancel an order."""
        endpoint = f"/orders/{variety}/{order_id}"
        response = await self._request("DELETE", endpoint, data=data or {}) # DELETE might need form data for parent_order_id
        if isinstance(response, dict) and 'order_id' in response:
            return {"order_id": str(response['order_id'])}
        logger.error(f"Cancel order response did not contain 'order_id': {response}")
        raise KiteConnectError("Invalid response format from cancel_order", "ServerError")

    async def get_orders(self) -> List[Dict[str, Any]]:
        """Get list of orders."""
        endpoint = "/orders"
        response = await self._request("GET", endpoint)
        if isinstance(response, list):
            return response
        logger.error(f"Get orders response was not a list: {response}")
        raise KiteConnectError("Invalid response format from get_orders", "ServerError")

    async def get_order_history(self, order_id: str) -> List[Dict[str, Any]]:
        """Get history for a specific order."""
        endpoint = f"/orders/{order_id}"
        response = await self._request("GET", endpoint)
        if isinstance(response, list):
            return response
        logger.error(f"Get order history response was not a list: {response}")
        raise KiteConnectError("Invalid response format from get_order_history", "ServerError")

    async def get_trades(self) -> List[Dict[str, Any]]:
        """Get list of trades."""
        endpoint = "/trades"
        response = await self._request("GET", endpoint)
        if isinstance(response, list):
            return response
        logger.error(f"Get trades response was not a list: {response}")
        raise KiteConnectError("Invalid response format from get_trades", "ServerError")

    async def get_order_trades(self, order_id: str) -> List[Dict[str, Any]]:
        """Get trades for a specific order."""
        endpoint = f"/orders/{order_id}/trades"
        response = await self._request("GET", endpoint)
        if isinstance(response, list):
            return response
        logger.error(f"Get order trades response was not a list: {response}")
        raise KiteConnectError("Invalid response format from get_order_trades", "ServerError")

    async def close(self):
        """Closes the underlying HTTPX client."""
        await self.client.aclose()
        logger.info("KiteConnectClient closed.")
