import logging
from typing import Dict, Any, Optional
import httpx
from pydantic import ValidationError

from models import (
    PlaceOrderParams, ModifyOrderParams, CancelOrderParams, OrderIdResponse,
    KiteApiResponse, KiteConnectError, InputException, TokenException,
    PermissionException, NetworkException, GeneralException, RateLimitException
)

logger = logging.getLogger(__name__)

class KiteConnectClient:
    """Asynchronous client for interacting with Kite Connect API v3 order endpoints."""

    def __init__(self, api_key: str, access_token: str, base_url: str = "https://api.kite.trade", timeout: float = 30.0):
        """Initializes the Kite Connect client.

        Args:
            api_key: Your Kite Connect API key.
            access_token: The access token obtained after successful login.
            base_url: The base URL for the Kite Connect API.
            timeout: Default request timeout in seconds.
        """
        if not api_key or not access_token:
            raise ValueError("API Key and Access Token cannot be empty.")

        self.api_key = api_key
        self.access_token = access_token
        self.base_url = base_url
        self._timeout = timeout
        self._headers = {
            "X-Kite-Version": "3",
            "Authorization": f"token {self.api_key}:{self.access_token}",
            # Content-Type is set per request based on method
        }
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self._headers,
            timeout=self._timeout
        )
        logger.info(f"KiteConnectClient initialized for base URL: {self.base_url}")

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Makes an asynchronous HTTP request to the Kite Connect API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            endpoint: API endpoint path (e.g., '/orders').
            params: URL query parameters.
            data: Request body data (for POST, PUT), sent as form-encoded.

        Returns:
            The parsed JSON response data upon success.

        Raises:
            NetworkException: For connection errors or timeouts.
            RateLimitException: If rate limit (429) is hit.
            TokenException: For authentication errors (403).
            InputException: For client-side validation errors (400).
            PermissionException: For permission denied errors (403).
            GeneralException: For other API-specific errors (non-2xx status codes).
            KiteConnectError: For unexpected errors during request/response handling.
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._headers.copy()
        request_kwargs = {
            "method": method,
            "url": url,
            "params": params,
            "headers": headers
        }

        # Kite API expects form data for POST/PUT
        if data:
            # Filter out None values from data payload
            filtered_data = {k: v for k, v in data.items() if v is not None}
            request_kwargs["data"] = filtered_data
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            # Ensure Content-Type is not set if there's no body data
            if "Content-Type" in headers:
                del headers["Content-Type"]

        logger.debug(f"Request: {method} {url} Params: {params} Data: {data}")

        try:
            response = await self.client.request(**request_kwargs)
            logger.debug(f"Response Status: {response.status_code} Body: {response.text[:500]}") # Log truncated body

            # Handle different status codes
            if response.status_code == 429:
                raise RateLimitException("Rate limit exceeded.", status_code=429)
            if response.status_code == 403:
                # Could be TokenException or PermissionException
                # Check response body for specifics if available
                try:
                    resp_json = response.json()
                    error_type = resp_json.get("error_type")
                    message = resp_json.get("message", "Forbidden.")
                    if error_type == "TokenException":
                        raise TokenException(message, status_code=403)
                    elif error_type == "PermissionException":
                        raise PermissionException(message, status_code=403)
                    else:
                        raise TokenException(f"Authentication/Authorization error: {message}", status_code=403)
                except (ValueError, KeyError):
                    raise TokenException("Authentication/Authorization failed (403).", status_code=403)

            # Check for other client/server errors indicated by status code
            response.raise_for_status()  # Raises HTTPStatusError for 4xx/5xx

            # Parse successful response
            response_json = response.json()
            parsed_response = KiteApiResponse.parse_obj(response_json)

            if parsed_response.status == "success":
                return parsed_response.data or {} # Return data or empty dict if data is null
            else:
                # Handle errors reported in the JSON body even with 2xx status (if API does that)
                error_type = parsed_response.error_type or "GeneralException"
                message = parsed_response.message or "Unknown API error"
                self._raise_specific_exception(error_type, message, response.status_code)

        except httpx.TimeoutException as e:
            logger.error(f"Request timed out: {e}")
            raise NetworkException(f"Request timed out after {self._timeout} seconds.") from e
        except httpx.RequestError as e:
            logger.error(f"Network request error: {e}")
            raise NetworkException(f"Network error connecting to Kite API: {e}") from e
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.status_code} - {e.response.text}")
            try:
                resp_json = e.response.json()
                error_type = resp_json.get("error_type", "GeneralException")
                message = resp_json.get("message", f"HTTP error {e.status_code}")
                self._raise_specific_exception(error_type, message, e.status_code)
            except ValueError:
                # If response is not JSON
                self._raise_specific_exception("GeneralException", f"HTTP error {e.status_code}: {e.response.text}", e.status_code)
        except ValidationError as e:
            logger.error(f"Failed to parse API response: {e}")
            raise KiteConnectError(f"Invalid API response format: {e}") from e
        except KiteConnectError: # Re-raise known exceptions
            raise
        except Exception as e:
            logger.exception(f"An unexpected error occurred during the API request: {e}")
            raise KiteConnectError(f"An unexpected error occurred: {e}") from e

        # Should not be reached if error handling is correct
        raise KiteConnectError("Reached unexpected end of _request method.")

    def _raise_specific_exception(self, error_type: str, message: str, status_code: Optional[int]):
        """Raises a specific exception based on the error type string."""
        exception_map = {
            "InputException": InputException,
            "TokenException": TokenException,
            "PermissionException": PermissionException,
            "NetworkException": NetworkException, # Less likely from API, more from client side
            "GeneralException": GeneralException,
            "OrderException": GeneralException, # Map specific API errors if needed
            "FundsException": GeneralException,
            "RMSException": GeneralException,
            # Add more specific mappings as identified
        }
        exception_class = exception_map.get(error_type, GeneralException)
        raise exception_class(message, status_code=status_code)

    async def place_order(self, params: PlaceOrderParams) -> OrderIdResponse:
        """Places an order.

        Args:
            params: PlaceOrderParams object containing order details.

        Returns:
            OrderIdResponse containing the order ID.
        """
        endpoint = f"/orders/{params.variety}"
        # Pydantic model converts to dict, httpx handles form encoding
        data = params.dict(exclude={'variety'}) # Variety is in the path
        logger.info(f"Placing order: {data}")
        response_data = await self._request("POST", endpoint, data=data)
        try:
            return OrderIdResponse.parse_obj(response_data)
        except ValidationError as e:
            logger.error(f"Failed to parse place_order response: {response_data}, Error: {e}")
            raise KiteConnectError(f"Invalid response format for place_order: {e}") from e

    async def modify_order(self, params: ModifyOrderParams) -> OrderIdResponse:
        """Modifies an existing order.

        Args:
            params: ModifyOrderParams object containing modification details.

        Returns:
            OrderIdResponse containing the order ID.
        """
        endpoint = f"/orders/{params.variety}/{params.order_id}"
        data = params.dict(exclude={'variety', 'order_id'}) # Path parameters excluded
        logger.info(f"Modifying order {params.order_id}: {data}")
        response_data = await self._request("PUT", endpoint, data=data)
        try:
            # Modify response also returns {'order_id': '...'}
            return OrderIdResponse.parse_obj(response_data)
        except ValidationError as e:
            logger.error(f"Failed to parse modify_order response: {response_data}, Error: {e}")
            raise KiteConnectError(f"Invalid response format for modify_order: {e}") from e

    async def cancel_order(self, params: CancelOrderParams) -> OrderIdResponse:
        """Cancels an existing order.

        Args:
            params: CancelOrderParams object containing cancellation details.

        Returns:
            OrderIdResponse containing the order ID.
        """
        endpoint = f"/orders/{params.variety}/{params.order_id}"
        # DELETE requests might need parameters in query or body depending on API spec.
        # Kite API DELETE for orders uses path params and potentially parent_order_id in query/body.
        # Assuming parent_order_id goes in query params if needed, but it's usually not required for DELETE.
        query_params = {}
        if params.parent_order_id:
             # Check Kite Docs: Does DELETE take parent_order_id? If so, where? Assuming query for now.
             # query_params['parent_order_id'] = params.parent_order_id
             # Or maybe it should be in data? Unlikely for DELETE.
             logger.warning("parent_order_id specified for cancel_order, but its placement (query/body) is ambiguous based on standard REST/Kite docs. Ignoring for now.")

        logger.info(f"Cancelling order {params.order_id} (variety: {params.variety})")
        response_data = await self._request("DELETE", endpoint, params=query_params)
        try:
            # Cancel response also returns {'order_id': '...'}
            return OrderIdResponse.parse_obj(response_data)
        except ValidationError as e:
            logger.error(f"Failed to parse cancel_order response: {response_data}, Error: {e}")
            raise KiteConnectError(f"Invalid response format for cancel_order: {e}") from e
