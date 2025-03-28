import httpx
import logging
from typing import Dict, Any, Optional, List
import json

from models import PlaceOrderParams, ModifyOrderParams, CancelOrderParams

logger = logging.getLogger(__name__)

# Custom Exception for API specific errors
class KiteApiException(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None, error_type: str = "APIError"):
        self.message = message
        self.status_code = status_code
        self.error_type = error_type
        super().__init__(f"[{error_type}/{status_code}] {message}")

class ZerodhaKiteClient:
    """Asynchronous client for interacting with the Zerodha Kite Connect v3 API."""

    def __init__(self, api_key: str, access_token: str, base_url: str = "https://api.kite.trade"):
        if not api_key or not access_token:
            raise ValueError("API key and access token are required.")

        self.api_key = api_key
        self.access_token = access_token
        self.base_url = base_url
        self.headers = {
            "X-Kite-Version": "3",
            "Authorization": f"token {self.api_key}:{self.access_token}",
            "Content-Type": "application/x-www-form-urlencoded" # Default for many Kite POST/PUT
        }
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=30.0,  # Set a reasonable timeout
            event_hooks={'response': [self._log_response], 'request': [self._log_request]}
        )

    async def _log_request(self, request: httpx.Request):
        # Be careful logging request body if it contains sensitive info
        # For form data, it might be okay, but avoid logging raw auth headers
        try:
            body = await request.aread()
            logger.debug(f"Request: {request.method} {request.url} - Headers: {request.headers} - Body: {body.decode()}")
        except Exception:
             logger.debug(f"Request: {request.method} {request.url} - Headers: {request.headers}")

    async def _log_response(self, response: httpx.Response):
        await response.aread() # Ensure response body is loaded for logging
        logger.debug(f"Response: {response.request.method} {response.request.url} - Status: {response.status_code} - Body: {response.text}")

    async def _request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any] | List[Any]:
        """Makes an asynchronous HTTP request to the Kite API."""
        try:
            response = await self.client.request(method, endpoint, params=params, data=data)

            # Check for HTTP errors
            response.raise_for_status()

            # Parse JSON response
            response_data = response.json()

            # Check for Kite API specific errors in the response body
            if response_data.get("status") == "error":
                error_type = response_data.get("error_type", "UnknownAPIError")
                message = response_data.get("message", "An unknown API error occurred.")
                logger.error(f"Kite API Error: Type={error_type}, Message={message}")
                raise KiteApiException(message=message, status_code=response.status_code, error_type=error_type)

            # Return the data part of the response
            return response_data.get("data", response_data) # Some endpoints might not have 'data' wrapper

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            error_type = f"HTTP{status_code}"
            message = f"HTTP Error {status_code}: {e.response.text[:500]}..." # Limit error message size
            # Try parsing Kite error from body even on HTTP error status
            try:
                error_data = e.response.json()
                if error_data.get("status") == "error":
                    error_type = error_data.get("error_type", error_type)
                    message = error_data.get("message", message)
            except (json.JSONDecodeError, AttributeError):
                pass # Keep the original HTTP error message

            logger.error(f"HTTP Error during API request to {e.request.url}: {status_code} - {message}")
            # Map common HTTP errors to Kite error types based on documentation/convention
            if status_code == 400:
                error_type = "InputException" # Bad request, likely invalid params
            elif status_code == 401 or status_code == 403:
                error_type = "AuthenticationError" # Unauthorized or Forbidden
            elif status_code == 429:
                error_type = "RateLimitError"
            elif status_code >= 500:
                error_type = "GeneralException" # Server-side errors

            raise KiteApiException(message=message, status_code=status_code, error_type=error_type) from e

        except httpx.RequestError as e:
            logger.error(f"Network or Request Error during API request to {e.request.url}: {e}")
            raise KiteApiException(message=f"Network error: {e}", error_type="NetworkException") from e
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON response: {e}")
            raise KiteApiException(message="Invalid JSON response from API", error_type="DataException") from e
        except Exception as e:
            logger.exception(f"An unexpected error occurred during API request: {e}")
            raise KiteApiException(message=f"An unexpected error occurred: {str(e)}", error_type="InternalError") from e

    async def place_order(self, params: PlaceOrderParams) -> Dict[str, Any]:
        """Place an order."""
        endpoint = f"/orders/{params.variety.value}"
        # Convert Pydantic model to dict, excluding None values
        data = params.dict(exclude={'variety'}, exclude_none=True)
        # Convert boolean/numeric types to string if required by API (check docs)
        # For Kite, form data typically handles types correctly, but explicit conversion might be safer
        for key, value in data.items():
            if isinstance(value, (int, float)):
                data[key] = str(value)
            elif isinstance(value, Enum):
                 data[key] = value.value # Ensure enums are sent as their string values

        logger.info(f"Placing order: POST {endpoint} with data: {data}")
        return await self._request("POST", endpoint, data=data)

    async def modify_order(self, params: ModifyOrderParams) -> Dict[str, Any]:
        """Modify an existing order."""
        endpoint = f"/orders/{params.variety.value}/{params.order_id}"
        data = params.dict(exclude={'variety', 'order_id'}, exclude_none=True)
        # Convert types if needed
        for key, value in data.items():
            if isinstance(value, (int, float)):
                data[key] = str(value)
            elif isinstance(value, Enum):
                 data[key] = value.value

        logger.info(f"Modifying order: PUT {endpoint} with data: {data}")
        return await self._request("PUT", endpoint, data=data)

    async def cancel_order(self, params: CancelOrderParams) -> Dict[str, Any]:
        """Cancel an existing order."""
        endpoint = f"/orders/{params.variety.value}/{params.order_id}"
        query_params = {}
        if params.parent_order_id:
            query_params["parent_order_id"] = params.parent_order_id

        logger.info(f"Cancelling order: DELETE {endpoint} with params: {query_params}")
        return await self._request("DELETE", endpoint, params=query_params)

    async def get_orders(self) -> List[Dict[str, Any]]:
        """Retrieve the list of orders for the day."""
        endpoint = "/orders"
        logger.info(f"Getting orders: GET {endpoint}")
        result = await self._request("GET", endpoint)
        if isinstance(result, list):
            return result
        else:
            logger.error(f"Expected list from get_orders, got {type(result)}")
            raise KiteApiException(message="API returned unexpected data format for orders.", error_type="DataException")

    async def close(self):
        """Closes the underlying HTTPX client."""
        await self.client.aclose()
        logger.info("ZerodhaKiteClient closed.")
