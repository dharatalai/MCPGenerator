import httpx
import logging
import os
from typing import Dict, Any, Optional
from models import (
    PlaceOrderParams, PlaceOrderResponse,
    ModifyOrderParams, ModifyOrderResponse,
    ErrorResponse, VarietyEnum
)

logger = logging.getLogger(__name__)

# --- Custom Exceptions ---
class KiteConnectAPIError(Exception):
    """Base exception for Kite Connect API errors."""
    def __init__(self, status_code: int, response_data: Dict[str, Any]):
        self.status_code = status_code
        self.status = response_data.get("status", "error")
        self.message = response_data.get("message", "Unknown API error")
        self.error_type = response_data.get("error_type")
        super().__init__(f"[{self.status_code}/{self.error_type}] {self.message}")

class AuthenticationError(KiteConnectAPIError):
    """Exception for authentication errors (403)."""
    pass

class InputValidationError(KiteConnectAPIError):
    """Exception for input validation errors (400)."""
    pass

class OrderException(KiteConnectAPIError):
    """Exception for order placement/modification errors."""
    pass

class NetworkError(Exception):
    """Exception for network-related issues."""
    pass

class GeneralError(KiteConnectAPIError):
    """Exception for other API errors (e.g., 5xx)."""
    pass

# --- API Client ---
class ZerodhaKiteClient:
    """Asynchronous client for interacting with the Zerodha Kite Connect v3 API."""

    def __init__(self):
        self.api_key = os.getenv("ZERODHA_API_KEY")
        self.access_token = os.getenv("ZERODHA_ACCESS_TOKEN")
        self.base_url = os.getenv("ZERODHA_API_BASE_URL", "https://api.kite.trade")
        self.timeout = 60.0 # Default timeout for requests
        self.api_version = "3" # Kite Connect API version

        if not self.api_key or not self.access_token:
            raise ValueError("ZERODHA_API_KEY and ZERODHA_ACCESS_TOKEN must be set in environment variables.")

        self.headers = {
            "X-Kite-Version": self.api_version,
            "Authorization": f"token {self.api_key}:{self.access_token}",
            "Content-Type": "application/x-www-form-urlencoded" # Kite uses form encoding
        }
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=self.timeout
        )
        # Note: Proper rate limiting (3 requests/sec) requires a more sophisticated approach
        # (e.g., using asyncio-throttle or aiolimiter). This client does not implement it.
        logger.info(f"ZerodhaKiteClient initialized for base URL: {self.base_url}")

    async def _request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Makes an asynchronous HTTP request to the Kite Connect API."""
        url = f"{self.base_url}{endpoint}"
        logger.debug(f"Sending {method} request to {url} with data: {data}")
        try:
            response = await self.client.request(method, endpoint, data=data)

            logger.debug(f"Received response: Status={response.status_code}, Body={response.text[:500]}...")

            # Check for specific Kite Connect error responses even on 200 OK
            if response.status_code == 200:
                response_data = response.json()
                if response_data.get("status") == "error":
                    logger.error(f"API returned error in 200 OK: {response_data}")
                    # Raise specific exceptions based on error_type if possible
                    if response_data.get("error_type") == "InputException":
                        raise InputValidationError(response.status_code, response_data)
                    elif response_data.get("error_type") == "OrderException":
                        raise OrderException(response.status_code, response_data)
                    elif response_data.get("error_type") == "TokenException":
                         raise AuthenticationError(response.status_code, response_data)
                    else:
                        raise KiteConnectAPIError(response.status_code, response_data)
                return response_data.get("data", {}) # Successful responses are nested under 'data'

            # Handle HTTP errors
            response.raise_for_status() # Raises HTTPStatusError for 4xx/5xx

            # Should not happen if raise_for_status works, but as a fallback
            return response.json().get("data", {}) 

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            try:
                error_data = e.response.json()
                logger.error(f"HTTP Status Error {status_code}: {error_data}")
                if status_code == 400:
                    raise InputValidationError(status_code, error_data) from e
                elif status_code == 403:
                    raise AuthenticationError(status_code, error_data) from e
                # Add more specific error mappings if needed (e.g., 429 for rate limits)
                elif status_code >= 500:
                    raise GeneralError(status_code, error_data) from e
                else:
                    raise KiteConnectAPIError(status_code, error_data) from e
            except Exception as json_e: # Handle cases where error response is not JSON
                logger.error(f"HTTP Status Error {status_code}, could not parse JSON response: {e.response.text}")
                error_data = {"message": e.response.text, "status": "error"}
                if status_code == 403:
                    raise AuthenticationError(status_code, error_data) from e
                elif status_code >= 500:
                    raise GeneralError(status_code, error_data) from e
                else:
                    raise KiteConnectAPIError(status_code, error_data) from e

        except httpx.TimeoutException as e:
            logger.error(f"Request timed out: {e}")
            raise NetworkError(f"Request timed out after {self.timeout} seconds") from e
        except httpx.NetworkError as e:
            logger.error(f"Network error occurred: {e}")
            raise NetworkError(f"A network error occurred: {e}") from e
        except Exception as e:
            logger.exception(f"An unexpected error occurred during API request: {e}")
            raise GeneralError(500, {"message": f"An unexpected error occurred: {str(e)}", "status": "error"}) from e

    async def place_order(self, params: PlaceOrderParams) -> PlaceOrderResponse:
        """Places an order using the Kite Connect API."""
        endpoint = f"/orders/{params.variety.value}"
        # Convert Pydantic model to dict, excluding None values and 'variety'
        payload = params.dict(exclude_none=True, exclude={'variety'})

        # Convert boolean/enum fields to strings expected by Kite API if necessary
        # (httpx handles basic types, but check Kite docs if issues arise)
        # Example: payload['transaction_type'] = payload['transaction_type'].value

        logger.info(f"Placing order: {payload}")
        response_data = await self._request("POST", endpoint, data=payload)
        logger.info(f"Order placement successful: {response_data}")
        return PlaceOrderResponse(**response_data)

    async def modify_order(self, params: ModifyOrderParams) -> ModifyOrderResponse:
        """Modifies a pending order using the Kite Connect API."""
        endpoint = f"/orders/{params.variety.value}/{params.order_id}"
        # Convert Pydantic model to dict, excluding None values and path params
        payload = params.dict(exclude_none=True, exclude={'variety', 'order_id'})

        logger.info(f"Modifying order {params.order_id}: {payload}")
        response_data = await self._request("PUT", endpoint, data=payload)
        logger.info(f"Order modification successful: {response_data}")
        return ModifyOrderResponse(**response_data)

    async def close(self):
        """Closes the underlying HTTPX client."""
        await self.client.aclose()
        logger.info("ZerodhaKiteClient closed.")
