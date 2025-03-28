import httpx
import logging
import asyncio
from typing import Dict, Any, Optional, List, Union

from models import (
    PlaceOrderParams,
    ModifyOrderParams,
    CancelOrderParams,
    GetOrderHistoryParams
)

logger = logging.getLogger(__name__)

# Define a custom exception for Kite API errors
class KiteApiException(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None, error_type: Optional[str] = None, response_data: Optional[Any] = None):
        self.message = message
        self.status_code = status_code
        self.error_type = error_type
        self.response_data = response_data
        super().__init__(self.message)

    def __str__(self):
        return f"KiteApiException(status_code={self.status_code}, error_type='{self.error_type}', message='{self.message}')"

class AsyncKiteClient:
    """Asynchronous client for interacting with the Zerodha Kite Connect API v3."""

    def __init__(self, api_key: str, access_token: str, base_url: str = "https://api.kite.trade", timeout: float = 30.0, retries: int = 1, backoff_factor: float = 0.5):
        """Initialize the client.

        Args:
            api_key: Your Kite Connect API key.
            access_token: The access token obtained after successful login.
            base_url: The base URL for the Kite API.
            timeout: Default request timeout in seconds.
            retries: Number of retries for transient errors (e.g., 5xx, timeouts).
            backoff_factor: Factor to determine delay between retries (delay = backoff_factor * (2 ** retry_attempt)).
        """
        if not api_key or not access_token:
            raise ValueError("API Key and Access Token cannot be empty.")

        self.api_key = api_key
        self.access_token = access_token
        self.base_url = base_url
        self.timeout = timeout
        self.retries = retries
        self.backoff_factor = backoff_factor

        self.headers = {
            "X-Kite-Version": "3",
            "Authorization": f"token {self.api_key}:{self.access_token}",
            # Content-Type is set per request by httpx based on 'json' or 'data' parameter
        }

        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=self.timeout,
            # Enable HTTP/2 if supported by the server
            http2=True
        )

    async def _request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None, data: Optional[Dict[str, Any]] = None) -> Any:
        """Makes an asynchronous HTTP request with retry logic."""
        url = f"{self.base_url}{endpoint}"
        logger.debug(f"Making request: {method} {url} | Params: {params} | Data: {data}")

        last_exception = None
        for attempt in range(self.retries + 1):
            try:
                response = await self.client.request(
                    method,
                    endpoint, # Use relative endpoint with base_url in client
                    params=params,
                    data=data # Use data for form-encoded, json for JSON body
                )

                # Check for specific Kite error response structure
                try:
                    response_data = response.json()
                except Exception:
                    response_data = response.text # If not JSON

                # Raise specific exception for HTTP errors (4xx, 5xx)
                if response.is_error:
                    status_code = response.status_code
                    error_type = None
                    message = f"HTTP error {status_code}"

                    if isinstance(response_data, dict):
                        error_type = response_data.get("error_type")
                        message = response_data.get("message", message)

                    # Handle rate limiting (429)
                    if status_code == 429:
                        message = response_data.get("message", "Rate limit exceeded")
                        error_type = response_data.get("error_type", "TooManyRequests")
                        logger.warning(f"Rate limit hit (429). Attempt {attempt + 1}/{self.retries + 1}. {message}")
                        # If retries remain, back off and retry
                        if attempt < self.retries:
                            retry_after = self.backoff_factor * (2 ** attempt)
                            logger.info(f"Waiting {retry_after:.2f}s before retrying...")
                            await asyncio.sleep(retry_after)
                            continue # Go to next attempt
                        else:
                            logger.error("Rate limit exceeded after all retries.")
                            raise KiteApiException(message, status_code, error_type, response_data)

                    # Handle other client/server errors
                    logger.error(f"Kite API Error: Status={status_code}, Type={error_type}, Msg='{message}', Response={response_data}")
                    raise KiteApiException(message, status_code, error_type, response_data)

                # Success (2xx)
                logger.debug(f"Request successful: {method} {endpoint} -> Status {response.status_code}")
                return response_data # Return parsed JSON

            except httpx.TimeoutException as e:
                logger.warning(f"Request timed out: {method} {endpoint}. Attempt {attempt + 1}/{self.retries + 1}. Error: {e}")
                last_exception = e
                if attempt < self.retries:
                    retry_after = self.backoff_factor * (2 ** attempt)
                    await asyncio.sleep(retry_after)
                else:
                    raise KiteApiException(f"Request timed out after {self.retries} retries: {e}", status_code=408, error_type="Timeout") from e

            except httpx.RequestError as e:
                # Includes network errors, connection errors etc.
                logger.warning(f"Request failed: {method} {endpoint}. Attempt {attempt + 1}/{self.retries + 1}. Error: {e}")
                last_exception = e
                # Only retry potentially transient network errors, not configuration errors like invalid URL
                if isinstance(e, (httpx.NetworkError, httpx.ConnectError, httpx.ReadError)) and attempt < self.retries:
                     retry_after = self.backoff_factor * (2 ** attempt)
                     await asyncio.sleep(retry_after)
                else:
                    raise KiteApiException(f"Request failed: {e}", error_type="RequestError") from e

            except KiteApiException as e:
                # Re-raise KiteApiException if caught (e.g., from 429 handling)
                raise e

            except Exception as e:
                logger.exception(f"An unexpected error occurred during request: {method} {endpoint}")
                raise KiteApiException(f"An unexpected error occurred: {str(e)}", error_type="UnexpectedError") from e

        # Should not be reached if retries > 0, but as a fallback
        if last_exception:
             raise KiteApiException(f"Request failed after {self.retries} retries: {last_exception}", error_type="MaxRetriesExceeded") from last_exception
         # Should definitely not be reached
        raise KiteApiException("Request failed due to unknown error after retries", error_type="UnknownRetryFailure")


    async def place_order(self, params: PlaceOrderParams) -> Dict[str, Any]:
        """Place an order."""
        endpoint = f"/orders/{params.variety}"
        # Kite API expects form-encoded data for orders
        data = params.dict(exclude={'variety'}, exclude_none=True)
        # Convert boolean/numeric types to strings if required by API, though httpx usually handles this
        # Example: data = {k: str(v) for k, v in data.items()}
        return await self._request("POST", endpoint, data=data)

    async def modify_order(self, params: ModifyOrderParams) -> Dict[str, Any]:
        """Modify a pending order."""
        endpoint = f"/orders/{params.variety}/{params.order_id}"
        data = params.dict(exclude={'variety', 'order_id'}, exclude_none=True)
        return await self._request("PUT", endpoint, data=data)

    async def cancel_order(self, params: CancelOrderParams) -> Dict[str, Any]:
        """Cancel a pending order."""
        endpoint = f"/orders/{params.variety}/{params.order_id}"
        query_params = {}
        if params.parent_order_id:
            query_params['parent_order_id'] = params.parent_order_id

        # DELETE requests typically don't have a body, use query params if needed
        return await self._request("DELETE", endpoint, params=query_params if query_params else None)

    async def get_orders(self) -> Dict[str, Any]:
        """Retrieve the list of orders for the day."""
        endpoint = "/orders"
        return await self._request("GET", endpoint)

    async def get_order_history(self, params: GetOrderHistoryParams) -> Dict[str, Any]:
        """Retrieve the history of a specific order."""
        endpoint = f"/orders/{params.order_id}"
        return await self._request("GET", endpoint)

    async def close(self):
        """Close the underlying HTTP client."""
        await self.client.aclose()
        logger.info("Kite API client closed.")
