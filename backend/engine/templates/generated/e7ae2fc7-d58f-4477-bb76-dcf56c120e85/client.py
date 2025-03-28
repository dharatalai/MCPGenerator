import httpx
import logging
import os
import asyncio
from typing import Dict, Any, Optional
from models import PlaceOrderParams, PlaceOrderResponse, ErrorResponse, VarietyType

logger = logging.getLogger(__name__)

class KiteConnectError(Exception):
    """Base exception for Kite Connect client errors."""
    def __init__(self, message="An error occurred with the Kite Connect API", status_code=None, error_type=None, data=None):
        self.message = message
        self.status_code = status_code
        self.error_type = error_type
        self.data = data
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": "error",
            "message": self.message,
            "error_type": self.error_type or self.__class__.__name__,
            "data": self.data
        }

class AuthenticationError(KiteConnectError):
    """Exception for authentication issues (403 Forbidden)."""
    pass

class NetworkError(KiteConnectError):
    """Exception for network-related issues (timeouts, connection errors)."""
    pass

class BadRequestError(KiteConnectError):
    """Exception for client-side errors (400 Bad Request)."""
    pass

class ServerError(KiteConnectError):
    """Exception for server-side errors (5xx)."""
    pass

class RateLimitError(KiteConnectError):
    """Exception for rate limit errors (429 Too Many Requests)."""
    pass

class KiteConnectClient:
    """Asynchronous client for interacting with the Zerodha Kite Connect API v3."""

    def __init__(self, max_retries: int = 3, backoff_factor: float = 0.5):
        self.api_key = os.getenv("KITE_API_KEY")
        self.access_token = os.getenv("KITE_ACCESS_TOKEN")
        self.base_url = os.getenv("KITE_ROOT_URL", "https://api.kite.trade")
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

        if not self.api_key or not self.access_token:
            raise ValueError("KITE_API_KEY and KITE_ACCESS_TOKEN must be set in environment variables.")

        self.headers = {
            "X-Kite-Version": "3",
            "Authorization": f"token {self.api_key}:{self.access_token}",
            "Content-Type": "application/x-www-form-urlencoded" # Kite uses form encoding
        }
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=30.0  # Set a default timeout
        )

    async def _request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Makes an asynchronous request to the Kite Connect API with retry logic."""
        url = f"{self.base_url}{endpoint}"
        logger.debug(f"Requesting {method} {url} with data: {data}")
        
        for attempt in range(self.max_retries + 1):
            try:
                response = await self.client.request(method, endpoint, data=data)
                response.raise_for_status() # Raises HTTPStatusError for 4xx/5xx
                
                json_response = response.json()
                logger.debug(f"Response {response.status_code} from {url}: {json_response}")

                # Check for Kite specific error structure within a 200 OK response
                if json_response.get("status") == "error":
                    error_type = json_response.get("error_type", "UnknownKiteError")
                    message = json_response.get("message", "Unknown Kite API error")
                    logger.error(f"Kite API error ({error_type}): {message}")
                    # Map Kite error types to our custom exceptions if needed
                    if error_type == "InputException":
                         raise BadRequestError(message=message, status_code=response.status_code, error_type=error_type, data=json_response.get("data"))
                    elif error_type == "TokenException":
                         raise AuthenticationError(message=message, status_code=response.status_code, error_type=error_type, data=json_response.get("data"))
                    # Add more mappings as needed
                    else:
                        raise KiteConnectError(message=message, status_code=response.status_code, error_type=error_type, data=json_response.get("data"))
                
                return json_response.get("data", {}) # Successful response data is usually nested

            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code
                try:
                    error_data = e.response.json()
                    message = error_data.get("message", f"HTTP error {status_code}")
                    error_type = error_data.get("error_type", f"HTTP{status_code}")
                except Exception:
                    message = f"HTTP error {status_code}: {e.response.text[:100]}" # Truncate long non-JSON errors
                    error_type = f"HTTP{status_code}"
                
                logger.error(f"HTTP error {status_code} from {url}: {message} (Attempt {attempt + 1}/{self.max_retries + 1})")

                if status_code == 400:
                    raise BadRequestError(message=message, status_code=status_code, error_type=error_type, data=error_data if 'error_data' in locals() else None) from e
                elif status_code == 403:
                    raise AuthenticationError(message=message, status_code=status_code, error_type=error_type, data=error_data if 'error_data' in locals() else None) from e
                elif status_code == 429:
                    # Rate limited, retry if possible
                    if attempt < self.max_retries:
                        wait_time = self.backoff_factor * (2 ** attempt)
                        logger.warning(f"Rate limit hit. Retrying in {wait_time:.2f} seconds...")
                        await asyncio.sleep(wait_time)
                        continue # Retry the loop
                    else:
                        raise RateLimitError(message="Rate limit exceeded after multiple retries.", status_code=status_code, error_type="RateLimitError") from e
                elif status_code >= 500:
                    # Server error, retry if possible
                    if attempt < self.max_retries:
                        wait_time = self.backoff_factor * (2 ** attempt)
                        logger.warning(f"Server error ({status_code}). Retrying in {wait_time:.2f} seconds...")
                        await asyncio.sleep(wait_time)
                        continue # Retry the loop
                    else:
                         raise ServerError(message=f"Server error {status_code} after multiple retries.", status_code=status_code, error_type="ServerError") from e
                else:
                    # Other unexpected 4xx errors
                    raise KiteConnectError(message=message, status_code=status_code, error_type=error_type, data=error_data if 'error_data' in locals() else None) from e

            except httpx.TimeoutException as e:
                logger.error(f"Request timed out to {url}: {str(e)} (Attempt {attempt + 1}/{self.max_retries + 1})")
                if attempt < self.max_retries:
                    wait_time = self.backoff_factor * (2 ** attempt)
                    logger.warning(f"Timeout occurred. Retrying in {wait_time:.2f} seconds...")
                    await asyncio.sleep(wait_time)
                    continue # Retry the loop
                else:
                    raise NetworkError(message="Request timed out after multiple retries.", error_type="TimeoutException") from e
            
            except httpx.NetworkError as e:
                logger.error(f"Network error connecting to {url}: {str(e)} (Attempt {attempt + 1}/{self.max_retries + 1})")
                if attempt < self.max_retries:
                    wait_time = self.backoff_factor * (2 ** attempt)
                    logger.warning(f"Network error occurred. Retrying in {wait_time:.2f} seconds...")
                    await asyncio.sleep(wait_time)
                    continue # Retry the loop
                else:
                    raise NetworkError(message=f"Network error after multiple retries: {str(e)}", error_type="NetworkError") from e

            except Exception as e:
                logger.exception(f"An unexpected error occurred during request to {url}: {str(e)}")
                raise KiteConnectError(message=f"An unexpected error occurred: {str(e)}", error_type="UnexpectedException") from e
        
        # Should not be reached if retries are exhausted, as exceptions are raised
        raise KiteConnectError("Request failed after maximum retries.")

    async def place_order(self, variety: VarietyType, params: PlaceOrderParams) -> PlaceOrderResponse:
        """
        Places an order of a specific variety.

        Args:
            variety: The order variety (e.g., 'regular', 'amo').
            params: An instance of PlaceOrderParams containing order details.

        Returns:
            PlaceOrderResponse containing the order_id.

        Raises:
            KiteConnectError: For API specific errors.
            AuthenticationError: For auth issues.
            NetworkError: For connection or timeout problems.
            BadRequestError: For invalid input parameters.
            ServerError: For Kite server issues.
            RateLimitError: If rate limits are exceeded.
        """
        endpoint = f"/orders/{variety}"
        
        # Convert Pydantic model to dict, excluding None values and the 'variety' field itself
        payload = params.dict(exclude_none=True, exclude={'variety'})
        
        # Ensure required fields based on logic are present (Pydantic model handles most)
        # Convert float values to strings where necessary if API expects strings
        for key, value in payload.items():
            if isinstance(value, float):
                payload[key] = str(value)
            if isinstance(value, int):
                 payload[key] = str(value) # Kite API expects numbers as strings in form data

        logger.info(f"Placing {variety} order with payload: {payload}")
        
        try:
            response_data = await self._request("POST", endpoint, data=payload)
            
            if "order_id" not in response_data:
                 logger.error(f"'order_id' not found in response: {response_data}")
                 raise KiteConnectError(message="'order_id' not found in the response data.", data=response_data, error_type="MalformedResponse")

            return PlaceOrderResponse(order_id=response_data["order_id"])
        except KiteConnectError as e:
            logger.error(f"Failed to place order: {e.message} (Type: {e.error_type}, Data: {e.data})")
            raise # Re-raise the specific error
        except Exception as e:
            logger.exception(f"Unexpected error during place_order: {str(e)}")
            raise KiteConnectError(message=f"An unexpected error occurred while placing the order: {str(e)}") from e

    async def close(self):
        """Closes the underlying HTTP client."""
        await self.client.aclose()
        logger.info("KiteConnectClient closed.")
