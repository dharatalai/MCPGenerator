import logging
from typing import Dict, Any, Optional

import httpx

from models import PlaceOrderParams, ModifyOrderParams

logger = logging.getLogger(__name__)

class KiteApiException(Exception):
    """Custom exception for Kite Connect API errors."""
    def __init__(self, status_code: int, error_type: str, message: str):
        self.status_code = status_code
        self.error_type = error_type
        self.message = message
        super().__init__(f"[{status_code}|{error_type}] {message}")

class KiteConnectClient:
    """Asynchronous client for interacting with the Zerodha Kite Connect v3 API.

    Handles authentication, request formatting, and error handling.
    """
    def __init__(self, api_key: str, access_token: str, base_url: str = "https://api.kite.trade", timeout: float = 30.0):
        self.api_key = api_key
        self.access_token = access_token
        self.base_url = base_url
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Initializes and returns the httpx.AsyncClient instance."""
        if self._client is None or self._client.is_closed:
            headers = {
                "X-Kite-Version": "3",
                "Authorization": f"token {self.api_key}:{self.access_token}",
                # Content-Type is set by httpx based on 'data' or 'json'
            }
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=self.timeout
            )
            logger.info("Initialized KiteConnectClient httpx client.")
        return self._client

    async def close(self):
        """Closes the underlying httpx client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            logger.info("Closed KiteConnectClient httpx client.")

    async def _request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Makes an asynchronous request to the Kite Connect API."""
        client = await self._get_client()
        url = f"{self.base_url}{endpoint}"
        logger.debug(f"Making {method} request to {url} with data: {data}")

        try:
            response = await client.request(method, endpoint, data=data)
            logger.debug(f"Received response: Status={response.status_code}, Body={response.text[:500]}") # Log truncated body

            # Check for specific Kite API error responses
            if response.status_code >= 400:
                try:
                    error_data = response.json()
                    error_type = error_data.get("error_type", "UnknownError")
                    message = error_data.get("message", "No error message provided.")
                    raise KiteApiException(response.status_code, error_type, message)
                except (ValueError, KeyError):
                    # If response is not JSON or doesn't match expected error format
                    raise KiteApiException(response.status_code, "UnknownApiError", response.text)

            # Check for non-JSON success responses (shouldn't happen for orders, but good practice)
            try:
                response_data = response.json()
                if response_data.get("status") == "error":
                     error_type = response_data.get("error_type", "UnknownError")
                     message = response_data.get("message", "Unknown error from API.")
                     raise KiteApiException(response.status_code, error_type, message)

                return response_data.get("data", {}) # Orders API returns data field
            except ValueError:
                 raise KiteApiException(response.status_code, "InvalidResponseFormat", "API response was not valid JSON.")

        except httpx.TimeoutException as e:
            logger.error(f"Request timed out: {e}")
            raise KiteApiException(504, "TimeoutError", f"Request timed out after {self.timeout} seconds.")
        except httpx.RequestError as e:
            logger.error(f"HTTP request error: {e}")
            raise KiteApiException(500, "NetworkError", f"An error occurred during the request: {e}")
        except KiteApiException: # Re-raise specific API errors
            raise
        except Exception as e:
            logger.exception(f"An unexpected error occurred during the API request: {e}")
            raise KiteApiException(500, "InternalClientError", f"An unexpected client error occurred: {e}")

    async def place_order(self, params: PlaceOrderParams) -> Dict[str, str]:
        """Places an order using the Kite Connect API.

        Args:
            params: PlaceOrderParams containing order details.

        Returns:
            A dictionary containing the 'order_id'.

        Raises:
            KiteApiException: If the API returns an error.
        """
        endpoint = f"/orders/{params.variety}"
        # Prepare form data, excluding None values and the path parameter 'variety'
        form_data = {
            k: v for k, v in params.dict().items()
            if k != 'variety' and v is not None
        }
        logger.info(f"Placing order: endpoint={endpoint}, data={form_data}")
        response_data = await self._request("POST", endpoint, data=form_data)

        if "order_id" not in response_data:
             logger.error(f"'order_id' not found in response: {response_data}")
             raise KiteApiException(500, "MalformedResponse", f"'order_id' missing from successful place order response: {response_data}")

        return {"order_id": str(response_data["order_id"]) # Ensure it's a string
}

    async def modify_order(self, params: ModifyOrderParams) -> Dict[str, str]:
        """Modifies a pending order using the Kite Connect API.

        Args:
            params: ModifyOrderParams containing modification details.

        Returns:
            A dictionary containing the 'order_id'.

        Raises:
            KiteApiException: If the API returns an error.
        """
        endpoint = f"/orders/{params.variety}/{params.order_id}"
        # Prepare form data, excluding None values and path parameters
        form_data = {
            k: v for k, v in params.dict().items()
            if k not in ['variety', 'order_id'] and v is not None
        }
        logger.info(f"Modifying order: endpoint={endpoint}, data={form_data}")
        response_data = await self._request("PUT", endpoint, data=form_data)

        if "order_id" not in response_data:
             logger.error(f"'order_id' not found in response: {response_data}")
             raise KiteApiException(500, "MalformedResponse", f"'order_id' missing from successful modify order response: {response_data}")

        return {"order_id": str(response_data["order_id"]) # Ensure it's a string
}
