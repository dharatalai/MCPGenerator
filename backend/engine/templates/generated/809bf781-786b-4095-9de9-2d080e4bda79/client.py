import httpx
import logging
import os
from typing import Dict, Any, Optional, Union
from models import PlaceOrderParams, ModifyOrderParams, OrderResponse, ErrorResponse, VarietyEnum

logger = logging.getLogger(__name__)

class KiteConnectError(Exception):
    """Base exception class for Kite Connect client errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, error_type: Optional[str] = None):
        self.message = message
        self.status_code = status_code
        self.error_type = error_type
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": "error",
            "message": self.message,
            "error_type": self.error_type or self.__class__.__name__,
            "status_code": self.status_code
        }

class AuthenticationError(KiteConnectError):
    """Raised for authentication failures (403 Forbidden)."""
    pass

class BadRequestError(KiteConnectError):
    """Raised for general 4xx client errors (e.g., invalid input)."""
    pass

class RateLimitError(KiteConnectError):
    """Raised for 429 Too Many Requests errors."""
    pass

class ServerError(KiteConnectError):
    """Raised for 5xx server errors."""
    pass

class NetworkError(KiteConnectError):
    """Raised for network-related issues (timeouts, connection errors)."""
    pass

class KiteConnectClient:
    """Asynchronous client for interacting with the Kite Connect Orders API (v3)."""

    def __init__(self):
        self.api_key = os.getenv("KITE_API_KEY")
        self.access_token = os.getenv("KITE_ACCESS_TOKEN")
        self.base_url = os.getenv("KITE_BASE_URL", "https://api.kite.trade")
        self.api_version = "3"

        if not self.api_key or not self.access_token:
            raise ValueError("KITE_API_KEY and KITE_ACCESS_TOKEN must be set in environment variables.")

        self.headers = {
            "X-Kite-Version": self.api_version,
            "Authorization": f"token {self.api_key}:{self.access_token}",
            "Content-Type": "application/x-www-form-urlencoded" # Kite API uses form encoding
        }
        # Increased timeout for potentially slower trading operations
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=30.0
        )

    async def _request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Makes an asynchronous HTTP request to the Kite Connect API."""
        url = f"{self.base_url}{endpoint}"
        logger.info(f"Making Kite API request: {method} {url}")
        if data:
            # Filter out None values before sending
            payload = {k: v for k, v in data.items() if v is not None}
            logger.debug(f"Request payload: {payload}")
        else:
            payload = None

        try:
            response = await self.client.request(method, endpoint, data=payload)

            # Check for specific Kite Connect error structure in JSON response
            try:
                json_response = response.json()
                if isinstance(json_response, dict) and json_response.get("status") == "error":
                    error_message = json_response.get("message", "Unknown API error")
                    error_type = json_response.get("error_type", "APIError")
                    logger.error(f"Kite API Error ({response.status_code}): {error_message} (Type: {error_type})")
                    # Map Kite error types to custom exceptions if needed, or raise a general one
                    if response.status_code == 403:
                         raise AuthenticationError(error_message, response.status_code, error_type)
                    elif response.status_code == 429:
                         raise RateLimitError(error_message, response.status_code, error_type)
                    elif 400 <= response.status_code < 500:
                         raise BadRequestError(error_message, response.status_code, error_type)
                    else:
                         raise KiteConnectError(error_message, response.status_code, error_type)
            except ValueError: # Handle cases where response is not valid JSON
                pass # Let raise_for_status handle non-JSON errors

            response.raise_for_status() # Raise HTTPError for 4xx/5xx status codes if not caught above
            logger.info(f"Kite API request successful ({response.status_code})")
            return response.json()

        except httpx.TimeoutException as e:
            logger.error(f"Kite API request timed out: {e}")
            raise NetworkError(f"Request timed out: {e}", error_type="TimeoutError")
        except httpx.RequestError as e:
            logger.error(f"Kite API request network error: {e}")
            raise NetworkError(f"Network error during request: {e}", error_type="NetworkException")
        except httpx.HTTPStatusError as e:
            logger.error(f"Kite API HTTP error: {e.response.status_code} - {e.response.text}")
            if e.response.status_code == 403:
                raise AuthenticationError(f"Authentication failed: {e.response.text}", e.response.status_code, "TokenException")
            elif e.response.status_code == 400:
                 raise BadRequestError(f"Bad request: {e.response.text}", e.response.status_code, "InputException")
            elif e.response.status_code == 429:
                raise RateLimitError(f"Rate limit exceeded: {e.response.text}", e.response.status_code, "RateLimitError")
            elif 500 <= e.response.status_code < 600:
                raise ServerError(f"Kite API server error: {e.response.text}", e.response.status_code, "GeneralException")
            else:
                raise KiteConnectError(f"HTTP error: {e.response.text}", e.response.status_code, "HTTPError")
        except KiteConnectError: # Re-raise errors caught and processed from JSON response
             raise
        except Exception as e:
            logger.exception(f"An unexpected error occurred during Kite API request: {e}")
            raise KiteConnectError(f"An unexpected error occurred: {str(e)}", error_type="UnexpectedError")

    async def place_order(self, params: PlaceOrderParams) -> Union[OrderResponse, ErrorResponse]:
        """Places an order with the specified parameters."""
        endpoint = f"/orders/{params.variety.value}"
        try:
            # Convert Pydantic model to dict, excluding 'variety' as it's in the path
            data = params.dict(exclude={'variety'}, exclude_none=True)
            response_data = await self._request("POST", endpoint, data=data)

            # Kite API returns {'status': 'success', 'data': {'order_id': '...'}}
            if response_data.get("status") == "success" and "data" in response_data and "order_id" in response_data["data"]:
                return OrderResponse(order_id=response_data["data"]["order_id"])
            else:
                logger.error(f"Unexpected successful response format from place_order: {response_data}")
                # Attempt to parse as error just in case
                if response_data.get("status") == "error":
                     return ErrorResponse(
                         message=response_data.get("message", "Unknown error during order placement."),
                         error_type=response_data.get("error_type", "OrderException")
                     )
                # Fallback error
                return ErrorResponse(message="Order placement status unknown or failed. Unexpected response format.", error_type="UnexpectedResponse")

        except KiteConnectError as e:
            logger.error(f"Failed to place order: {e.message} (Type: {e.error_type}, Code: {e.status_code})")
            return ErrorResponse(message=e.message, error_type=e.error_type)
        except Exception as e:
            logger.exception("Unexpected error in place_order tool execution")
            return ErrorResponse(message=f"An unexpected server error occurred: {str(e)}", error_type="InternalServerError")

    async def modify_order(self, params: ModifyOrderParams) -> Union[OrderResponse, ErrorResponse]:
        """Modifies a pending order with the specified parameters."""
        endpoint = f"/orders/{params.variety.value}/{params.order_id}"
        try:
            # Convert Pydantic model to dict, excluding 'variety' and 'order_id'
            data = params.dict(exclude={'variety', 'order_id'}, exclude_none=True)
            response_data = await self._request("PUT", endpoint, data=data)

            # Kite API returns {'status': 'success', 'data': {'order_id': '...'}}
            if response_data.get("status") == "success" and "data" in response_data and "order_id" in response_data["data"]:
                # Modification successful, returns the same order_id
                return OrderResponse(order_id=response_data["data"]["order_id"])
            else:
                logger.error(f"Unexpected successful response format from modify_order: {response_data}")
                if response_data.get("status") == "error":
                     return ErrorResponse(
                         message=response_data.get("message", "Unknown error during order modification."),
                         error_type=response_data.get("error_type", "OrderException")
                     )
                return ErrorResponse(message="Order modification status unknown or failed. Unexpected response format.", error_type="UnexpectedResponse")

        except KiteConnectError as e:
            logger.error(f"Failed to modify order {params.order_id}: {e.message} (Type: {e.error_type}, Code: {e.status_code})")
            return ErrorResponse(message=e.message, error_type=e.error_type)
        except Exception as e:
            logger.exception(f"Unexpected error in modify_order tool execution for order {params.order_id}")
            return ErrorResponse(message=f"An unexpected server error occurred: {str(e)}", error_type="InternalServerError")

    async def close(self):
        """Closes the underlying HTTPX client."""
        await self.client.aclose()
        logger.info("Kite Connect client closed.")
