import httpx
import logging
from typing import Dict, Any, Optional, List, Union

from models import (
    PlaceOrderParams,
    ModifyOrderParams,
    CancelOrderParams,
    OrderDetails,
    OrderHistoryItem
)

logger = logging.getLogger(__name__)

# Custom Exception for Kite API specific errors
class KiteApiException(Exception):
    def __init__(self, message, status_code=None, error_type=None):
        super().__init__(message)
        self.status_code = status_code
        self.error_type = error_type
        self.message = message

    def __str__(self):
        return f"Kite API Error (Status: {self.status_code}, Type: {self.error_type}): {self.message}"

class KiteConnectClient:
    def __init__(self, api_key: str, access_token: str, base_url: str = "https://api.kite.trade", timeout: float = 30.0):
        self.api_key = api_key
        self.access_token = access_token
        self.base_url = base_url
        self.timeout = timeout
        self._headers = {
            "X-Kite-Version": "3",
            "Authorization": f"token {self.api_key}:{self.access_token}",
            "Content-Type": "application/x-www-form-urlencoded" # Kite uses form data for POST/PUT
        }
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self._headers,
            timeout=self.timeout,
            event_hooks={'request': [self._log_request], 'response': [self._log_response]}
        )

    async def _log_request(self, request):
        # Redact Authorization header before logging
        headers = dict(request.headers)
        if "Authorization" in headers:
            headers["Authorization"] = "[REDACTED]"
        logger.debug(f"Request: {request.method} {request.url} - Headers: {headers}")
        if request.content:
             # Be careful logging potentially sensitive form data
             # Consider logging only keys or omitting content logging in production
             try:
                 content = await request.aread()
                 logger.debug(f"Request Body: {content.decode()}")
             except Exception:
                 logger.debug("Could not read or decode request body for logging.")


    async def _log_response(self, response):
        await response.aread() # Ensure response body is available
        logger.debug(f"Response: {response.status_code} {response.request.method} {response.request.url} - Body: {response.text}")

    async def _request(self, method: str, endpoint: str, params: Optional[Dict] = None, data: Optional[Dict] = None) -> Any:
        """Makes an asynchronous HTTP request to the Kite API."""
        try:
            response = await self._client.request(
                method=method,
                url=endpoint,
                params=params, # For query parameters (GET, DELETE)
                data=data      # For form data (POST, PUT)
            )

            # Check for HTTP errors (4xx, 5xx)
            response.raise_for_status()

            # Parse JSON response
            json_response = response.json()

            # Check for Kite specific errors within the JSON response
            if json_response.get("status") == "error":
                error_type = json_response.get("error_type", "UnknownError")
                message = json_response.get("message", "Unknown Kite API error")
                logger.error(f"Kite API returned error: Type={error_type}, Message={message}")
                raise KiteApiException(message, status_code=response.status_code, error_type=error_type)

            # Return the 'data' part of the response if present, else the whole response
            return json_response.get("data", json_response)

        except httpx.HTTPStatusError as e:
            # Attempt to parse error details from Kite's response body
            error_type = "HTTPError"
            message = f"HTTP error occurred: {e.response.status_code} {e.response.reason_phrase}"
            try:
                error_data = e.response.json()
                error_type = error_data.get("error_type", error_type)
                message = error_data.get("message", message)
            except Exception:
                # If response is not JSON or parsing fails, use the raw text
                message = f"{message} - Response: {e.response.text[:500]}..."\ # Limit log size

            logger.error(f"HTTP error during Kite API request to {e.request.url}: {message}", exc_info=True)
            raise KiteApiException(message, status_code=e.response.status_code, error_type=error_type) from e

        except httpx.RequestError as e:
            logger.error(f"Network or request error during Kite API request to {e.request.url}: {e}", exc_info=True)
            raise KiteApiException(f"Network error: {e}", error_type="NetworkException") from e

        except Exception as e:
            logger.exception(f"An unexpected error occurred during Kite API request: {e}")
            raise KiteApiException(f"An unexpected error occurred: {e}", error_type="GeneralException") from e

    def _prepare_payload(self, params: BaseModel) -> Dict[str, Any]:
        """Converts Pydantic model to dict, removing None values."""
        return params.dict(exclude_none=True)

    async def place_order(self, params: PlaceOrderParams) -> Dict[str, str]:
        """Place an order."""
        endpoint = f"/orders/{params.variety.value}"
        data = self._prepare_payload(params)
        # Remove 'variety' as it's in the path
        data.pop('variety', None)
        # Convert enums back to strings if necessary (httpx might handle it)
        for key, value in data.items():
            if isinstance(value, Enum):
                 data[key] = value.value

        logger.info(f"Placing order via API: {endpoint} with data: {data}")
        response_data = await self._request("POST", endpoint, data=data)
        if isinstance(response_data, dict) and 'order_id' in response_data:
             return {"order_id": str(response_data['order_id'])} # Ensure string type
        else:
             logger.error(f"Unexpected response format for place_order: {response_data}")
             raise KiteApiException("Unexpected response format after placing order.", error_type="DataException")

    async def modify_order(self, params: ModifyOrderParams) -> Dict[str, str]:
        """Modify a pending order."""
        endpoint = f"/orders/{params.variety.value}/{params.order_id}"
        data = self._prepare_payload(params)
        # Remove path parameters from data payload
        data.pop('variety', None)
        data.pop('order_id', None)
        # Convert enums back to strings if necessary
        for key, value in data.items():
            if isinstance(value, Enum):
                 data[key] = value.value

        logger.info(f"Modifying order via API: {endpoint} with data: {data}")
        response_data = await self._request("PUT", endpoint, data=data)
        if isinstance(response_data, dict) and 'order_id' in response_data:
             return {"order_id": str(response_data['order_id'])} # Ensure string type
        else:
             logger.error(f"Unexpected response format for modify_order: {response_data}")
             raise KiteApiException("Unexpected response format after modifying order.", error_type="DataException")

    async def cancel_order(self, params: CancelOrderParams) -> Dict[str, str]:
        """Cancel a pending order."""
        endpoint = f"/orders/{params.variety.value}/{params.order_id}"
        query_params = {}
        if params.parent_order_id:
            query_params['parent_order_id'] = params.parent_order_id

        logger.info(f"Cancelling order via API: {endpoint} with params: {query_params}")
        response_data = await self._request("DELETE", endpoint, params=query_params)
        if isinstance(response_data, dict) and 'order_id' in response_data:
             return {"order_id": str(response_data['order_id'])} # Ensure string type
        else:
             logger.error(f"Unexpected response format for cancel_order: {response_data}")
             raise KiteApiException("Unexpected response format after cancelling order.", error_type="DataException")

    async def get_orders(self) -> List[Dict[str, Any]]: # Return raw dicts for flexibility
        """Retrieve the list of orders for the day."""
        endpoint = "/orders"
        logger.info(f"Getting orders via API: {endpoint}")
        response_data = await self._request("GET", endpoint)
        if isinstance(response_data, list):
            # TODO: Optionally parse each item into OrderDetails model if strict typing is needed
            return response_data
        else:
            logger.error(f"Unexpected response format for get_orders: {response_data}")
            raise KiteApiException("Expected a list of orders, but received different format.", error_type="DataException")

    async def get_order_history(self, order_id: str) -> List[Dict[str, Any]]: # Return raw dicts
        """Retrieve the history of a given order."""
        endpoint = f"/orders/{order_id}"
        logger.info(f"Getting order history via API: {endpoint}")
        response_data = await self._request("GET", endpoint)
        if isinstance(response_data, list):
             # TODO: Optionally parse each item into OrderHistoryItem model
             return response_data
        # Handle case where a single order detail dict might be returned instead of history list?
        # Based on plan, expecting List[OrderHistoryItem]
        elif isinstance(response_data, dict) and 'order_id' in response_data:
             logger.warning(f"Received single order detail instead of history list for {order_id}. Returning as list.")
             return [response_data] # Wrap single dict in a list if API behaves differently
        else:
             logger.error(f"Unexpected response format for get_order_history: {response_data}")
             raise KiteApiException("Expected a list of order history items.", error_type="DataException")

    async def close(self):
        """Closes the underlying HTTPX client."""
        await self._client.aclose()
        logger.info("KiteConnectClient closed.")
