import httpx
import logging
from typing import Dict, Any, Optional
from models import PlaceOrderParams, ModifyOrderParams, CancelOrderParams

logger = logging.getLogger(__name__)

class KiteClientError(Exception):
    """Custom exception for Kite Connect client errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, error_type: str = "ClientError"):
        super().__init__(message)
        self.status_code = status_code
        self.error_type = error_type

    def __str__(self):
        if self.status_code:
            return f"[{self.error_type} / {self.status_code}] {super().__str__()}"
        else:
            return f"[{self.error_type}] {super().__str__()}"

class KiteConnectClient:
    """Asynchronous client for interacting with the Kite Connect V3 API."""

    def __init__(self, api_key: str, access_token: str, base_url: str = "https://api.kite.trade"):
        if not api_key or not access_token:
            raise ValueError("API key and access token are required.")
        self.api_key = api_key
        self.access_token = access_token
        self.base_url = base_url
        self.headers = {
            "X-Kite-Version": "3",
            "Authorization": f"token {self.api_key}:{self.access_token}",
            "Content-Type": "application/x-www-form-urlencoded" # Kite API uses form encoding
        }
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=30.0 # Set a reasonable timeout
        )

    async def _request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Makes an asynchronous HTTP request to the Kite API."""
        url = f"{self.base_url}{endpoint}"
        logger.debug(f"Sending request: {method} {url} Data: {data}")
        try:
            response = await self.client.request(method, endpoint, data=data)
            response.raise_for_status() # Raises HTTPStatusError for 4xx/5xx responses
            
            json_response = response.json()
            logger.debug(f"Received response: {response.status_code} Body: {json_response}")

            # Kite API specific success/error check within the response body
            if json_response.get("status") == "error":
                error_type = json_response.get("error_type", "UnknownApiError")
                message = json_response.get("message", "Unknown API error occurred.")
                logger.error(f"Kite API returned error: {error_type} - {message}")
                raise KiteClientError(message, status_code=response.status_code, error_type=error_type)
            
            return json_response.get("data", {}) # Successful responses are nested under 'data'

        except httpx.TimeoutException as e:
            logger.error(f"Request timed out: {method} {url}", exc_info=True)
            raise KiteClientError(f"Request timed out: {str(e)}", error_type="TimeoutError") from e
        except httpx.RequestError as e:
            logger.error(f"Request error: {method} {url} - {e}", exc_info=True)
            # E.g., DNS errors, connection refused
            raise KiteClientError(f"Network request error: {str(e)}", error_type="NetworkError") from e
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} for {method} {url}", exc_info=True)
            try:
                # Try to parse error details from Kite's response body
                error_data = e.response.json()
                error_type = error_data.get("error_type", f"HTTP{e.response.status_code}")
                message = error_data.get("message", f"HTTP error {e.response.status_code}")
            except Exception:
                # Fallback if response is not JSON or doesn't match expected format
                error_type = f"HTTP{e.response.status_code}"
                message = f"HTTP error {e.response.status_code}: {e.response.text[:200]}" # Limit error text length
            
            # Map common HTTP status codes to error types
            if e.response.status_code == 400:
                error_type = "InputException" # Or use Kite's specific type if available
            elif e.response.status_code == 403:
                # Could be TokenException, UserException, PermissionException, TwoFAException, etc.
                error_type = error_data.get("error_type", "ForbiddenError") 
            elif e.response.status_code == 404:
                error_type = "DataException" # Or specific like OrderNotFound
            elif e.response.status_code == 429:
                error_type = "NetworkException" # Kite uses this for RateLimitError
            elif e.response.status_code == 500:
                error_type = "GeneralException" # Kite's general server error
            elif e.response.status_code == 502 or e.response.status_code == 503 or e.response.status_code == 504:
                 error_type = "NetworkException" # Kite's network/gateway errors

            raise KiteClientError(message, status_code=e.response.status_code, error_type=error_type) from e
        except Exception as e:
            logger.error(f"Unexpected error during request: {method} {url}", exc_info=True)
            raise KiteClientError(f"An unexpected error occurred: {str(e)}", error_type="GeneralException") from e

    async def place_order(self, params: PlaceOrderParams) -> Dict[str, str]:
        """Places an order using the Kite API."""
        endpoint = f"/orders/{params.variety.value}"
        # Convert model to dict, excluding None values and the 'variety' field itself
        # Use model_dump for Pydantic v2+, dict() for v1
        try: 
            payload = params.model_dump(exclude={'variety'}, exclude_none=True)
        except AttributeError: # Fallback for Pydantic v1
            payload = params.dict(exclude={'variety'}, exclude_none=True)

        # Convert enum values to strings for the API
        for key, value in payload.items():
            if isinstance(value, Enum):
                payload[key] = value.value

        logger.info(f"Placing order: {endpoint} with payload: {payload}")
        response_data = await self._request("POST", endpoint, data=payload)
        
        if "order_id" not in response_data:
             logger.error(f"'order_id' not found in successful place order response: {response_data}")
             raise KiteClientError("Order placement succeeded but 'order_id' was missing in the response.", error_type="ApiResponseError")
        
        return {"order_id": response_data["order_id"]}

    async def modify_order(self, params: ModifyOrderParams) -> Dict[str, str]:
        """Modifies an existing order using the Kite API."""
        endpoint = f"/orders/{params.variety.value}/{params.order_id}"
        try:
            payload = params.model_dump(exclude={'variety', 'order_id'}, exclude_none=True)
        except AttributeError: # Fallback for Pydantic v1
            payload = params.dict(exclude={'variety', 'order_id'}, exclude_none=True)

        # Convert enum values to strings
        for key, value in payload.items():
            if isinstance(value, Enum):
                payload[key] = value.value

        logger.info(f"Modifying order: {endpoint} with payload: {payload}")
        response_data = await self._request("PUT", endpoint, data=payload)

        if "order_id" not in response_data:
             logger.error(f"'order_id' not found in successful modify order response: {response_data}")
             raise KiteClientError("Order modification succeeded but 'order_id' was missing in the response.", error_type="ApiResponseError")

        return {"order_id": response_data["order_id"]}

    async def cancel_order(self, params: CancelOrderParams) -> Dict[str, str]:
        """Cancels an existing order using the Kite API."""
        endpoint = f"/orders/{params.variety.value}/{params.order_id}"
        try:
            payload = params.model_dump(exclude={'variety', 'order_id'}, exclude_none=True)
        except AttributeError: # Fallback for Pydantic v1
             payload = params.dict(exclude={'variety', 'order_id'}, exclude_none=True)

        logger.info(f"Cancelling order: {endpoint} with payload: {payload}")
        response_data = await self._request("DELETE", endpoint, data=payload)

        if "order_id" not in response_data:
             logger.error(f"'order_id' not found in successful cancel order response: {response_data}")
             raise KiteClientError("Order cancellation succeeded but 'order_id' was missing in the response.", error_type="ApiResponseError")

        return {"order_id": response_data["order_id"]}
