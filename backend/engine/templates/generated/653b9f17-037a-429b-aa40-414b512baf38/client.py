import logging
from typing import Dict, Any, Optional

import httpx
from pydantic import ValidationError as PydanticValidationError

from models import PlaceOrderParams, ModifyOrderParams, CancelOrderParams

logger = logging.getLogger(__name__)

# Custom Exceptions
class KiteConnectError(Exception):
    """Base exception for Kite Connect client errors."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)

    def __str__(self):
        if self.status_code:
            return f"[HTTP {self.status_code}] {self.message}"
        return self.message

class AuthenticationError(KiteConnectError):
    """Authentication failed (401/403)."""
    pass

class ValidationError(KiteConnectError):
    """Input validation failed (400)."""
    pass

class OrderNotFoundError(KiteConnectError):
    """Order not found (often 404, but depends on API)."""
    pass

class InvalidOrderStateError(KiteConnectError):
    """Order cannot be modified/cancelled in its current state."""
    pass

class InsufficientFundsError(KiteConnectError):
    """Insufficient funds for the order."""
    pass

class NetworkError(KiteConnectError):
    """Network communication error."""
    pass

class RateLimitError(KiteConnectError):
    """Rate limit exceeded (429)."""
    pass

class ExchangeError(KiteConnectError):
    """Error reported by the exchange."""
    pass

class GeneralError(KiteConnectError):
    """General API error (5xx or unexpected)."""
    pass


class KiteConnectClient:
    """Asynchronous client for interacting with the Kite Connect Orders API (v3)."""

    def __init__(self, api_key: str, access_token: str, base_url: str = "https://api.kite.trade", timeout: float = 30.0):
        """
        Initializes the Kite Connect client.

        Args:
            api_key: Your Kite Connect API key.
            access_token: The access token obtained after login.
            base_url: The base URL for the Kite Connect API (default: https://api.kite.trade).
            timeout: Request timeout in seconds.
        """
        self.api_key = api_key
        self.access_token = access_token
        self.base_url = base_url
        self.headers = {
            "X-Kite-Version": "3",
            "Authorization": f"token {self.api_key}:{self.access_token}",
            "Content-Type": "application/x-www-form-urlencoded" # Kite uses form encoding
        }
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=timeout
        )
        # Note: Kite API has rate limits (e.g., 10 req/sec). Implement throttling/backoff if needed.
        logger.info(f"KiteConnectClient initialized for base URL: {self.base_url}")

    async def _request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Makes an asynchronous HTTP request to the Kite Connect API."""
        url = f"{self.base_url}{endpoint}"
        logger.debug(f"Sending {method} request to {url}")
        logger.debug(f"Params: {params}")
        logger.debug(f"Data: {data}")

        try:
            response = await self.client.request(method, endpoint, data=data, params=params)
            response.raise_for_status() # Raises HTTPStatusError for 4xx/5xx
            return response.json()
        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            try:
                error_data = e.response.json()
                message = error_data.get("message", "Unknown API error")
                error_type = error_data.get("error_type", "UnknownError")
                logger.error(f"Kite API Error ({status_code} - {error_type}): {message}")

                if status_code == 400:
                    # Could be validation, insufficient funds, bad state etc.
                    if "funds" in message.lower():
                        raise InsufficientFundsError(message, status_code) from e
                    if "validation" in message.lower() or error_type == "InputException":
                         raise ValidationError(message, status_code) from e
                    # Add more specific checks based on Kite error messages if needed
                    raise ValidationError(f"{error_type}: {message}", status_code) from e # Default to validation for 400
                elif status_code in [401, 403]:
                    raise AuthenticationError(message, status_code) from e
                elif status_code == 404:
                    # 404 might mean order not found or invalid endpoint
                    raise OrderNotFoundError(message, status_code) from e
                elif status_code == 429:
                    raise RateLimitError(message, status_code) from e
                elif status_code == 500:
                     raise GeneralError(f"Internal Server Error: {message}", status_code) from e
                elif status_code == 502:
                     raise ExchangeError(f"Exchange Error/Gateway Timeout: {message}", status_code) from e
                elif status_code == 503:
                     raise ExchangeError(f"Service Unavailable (Maintenance?): {message}", status_code) from e
                else:
                    raise GeneralError(f"Unhandled API Error ({error_type}): {message}", status_code) from e
            except (ValueError, KeyError):
                # If response is not JSON or lacks expected keys
                message = e.response.text or f"HTTP error {status_code}"
                logger.error(f"Kite API Error ({status_code}): {message}")
                if status_code in [401, 403]: raise AuthenticationError(message, status_code) from e
                if status_code == 429: raise RateLimitError(message, status_code) from e
                raise GeneralError(message, status_code) from e

        except httpx.TimeoutException as e:
            logger.error(f"Request timed out: {e}")
            raise NetworkError(f"Request timed out after {self.client.timeout} seconds", None) from e
        except httpx.RequestError as e:
            # Covers network connection errors, DNS errors, etc.
            logger.error(f"Network error during request: {e}")
            raise NetworkError(f"Network error: {str(e)} contacting {e.request.url}", None) from e
        except PydanticValidationError as e:
             logger.error(f"Request/Response validation error: {e}")
             raise ValidationError(f"Data validation error: {e}", None) from e
        except Exception as e:
            logger.exception("An unexpected error occurred during API request")
            raise GeneralError(f"An unexpected error occurred: {str(e)}", None) from e

    async def place_order(self, params: PlaceOrderParams) -> Dict[str, Any]:
        """Places an order."""
        endpoint = f"/orders/{params.variety}"
        # Convert model to dict, excluding None values and the 'variety' field itself
        data = params.dict(exclude={'variety'}, exclude_none=True)
        logger.info(f"Placing order: endpoint={endpoint}, data={data}")
        return await self._request("POST", endpoint, data=data)

    async def modify_order(self, params: ModifyOrderParams) -> Dict[str, Any]:
        """Modifies an existing order."""
        endpoint = f"/orders/{params.variety}/{params.order_id}"
        # Convert model to dict, excluding None values and path params ('variety', 'order_id')
        data = params.dict(exclude={'variety', 'order_id'}, exclude_none=True)
        logger.info(f"Modifying order: endpoint={endpoint}, data={data}")
        return await self._request("PUT", endpoint, data=data)

    async def cancel_order(self, params: CancelOrderParams) -> Dict[str, Any]:
        """Cancels an existing order."""
        endpoint = f"/orders/{params.variety}/{params.order_id}"
        # parent_order_id goes into query params if present
        query_params = {}
        if params.parent_order_id:
            query_params['parent_order_id'] = params.parent_order_id

        logger.info(f"Cancelling order: endpoint={endpoint}, params={query_params}")
        return await self._request("DELETE", endpoint, params=query_params)

    async def close(self):
        """Closes the underlying HTTPX client."""
        await self.client.aclose()
        logger.info("KiteConnectClient closed.")
