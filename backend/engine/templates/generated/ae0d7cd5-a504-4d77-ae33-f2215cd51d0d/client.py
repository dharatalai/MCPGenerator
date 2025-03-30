import httpx
import logging
import os
from typing import Dict, Any, Optional, Union
from models import PlaceOrderParams, ModifyOrderParams, OrderResponse
import asyncio

logger = logging.getLogger(__name__)

# Simple in-memory rate limiter
class RateLimiter:
    def __init__(self, rate: int, period: float):
        self.rate = rate
        self.period = period
        self.tokens = rate
        self.last_refill_time = asyncio.get_event_loop().time()
        self.lock = asyncio.Lock()

    async def acquire(self):
        async with self.lock:
            now = asyncio.get_event_loop().time()
            time_passed = now - self.last_refill_time
            refill_amount = time_passed * (self.rate / self.period)

            self.tokens = min(self.rate, self.tokens + refill_amount)
            self.last_refill_time = now

            if self.tokens >= 1:
                self.tokens -= 1
                return True
            else:
                # Calculate wait time
                wait_time = (1 - self.tokens) * (self.period / self.rate)
                logger.warning(f"Rate limit exceeded. Waiting for {wait_time:.2f} seconds.")
                await asyncio.sleep(wait_time)
                # Re-check after waiting (another task might have consumed the token)
                # For simplicity in this example, we assume the wait was sufficient
                # and consume the token conceptually generated during the wait.
                self.tokens = 0 # Reset tokens after waiting to avoid bursting
                self.last_refill_time = asyncio.get_event_loop().time() # Update time after wait
                return True

class KiteConnectError(Exception):
    """Custom exception for Kite Connect API errors."""
    def __init__(self, status_code: int, message: str, details: Optional[Dict] = None):
        self.status_code = status_code
        self.message = message
        self.details = details
        super().__init__(f"Kite API Error {status_code}: {message}")

class KiteConnectClient:
    """Asynchronous client for interacting with the Kite Connect v3 API."""

    def __init__(self, api_key: str, access_token: str, base_url: str = "https://api.kite.trade"):
        if not api_key or not access_token:
            raise ValueError("API key and access token are required.")

        self.api_key = api_key
        self.access_token = access_token
        self.base_url = base_url
        self.headers = {
            "X-Kite-Version": "3",
            "Authorization": f"token {self.api_key}:{self.access_token}"
            # Content-Type is set by httpx based on data/json parameter
        }
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=30.0 # Set a reasonable timeout
        )
        # Kite Connect rate limit: 10 requests per second
        self.rate_limiter = RateLimiter(rate=10, period=1.0)

    async def _request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Makes an asynchronous request to the Kite Connect API."""
        await self.rate_limiter.acquire()
        url = f"{self.base_url}{endpoint}"
        logger.info(f"Sending {method} request to {url} with data: {data}")
        try:
            response = await self.client.request(method, endpoint, data=data)
            response.raise_for_status() # Raises HTTPStatusError for 4xx/5xx responses
            
            json_response = response.json()
            logger.info(f"Received successful response ({response.status_code}) from {url}")
            # Kite API specific success check (often contains a 'data' field)
            if json_response.get("status") == "error":
                 logger.error(f"Kite API returned error status: {json_response.get('message')}")
                 raise KiteConnectError(status_code=response.status_code, message=json_response.get('message', 'Unknown API error'), details=json_response)
            
            return json_response.get("data", {}) # Orders API usually returns data directly inside 'data'

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            try:
                error_details = e.response.json()
                message = error_details.get("message", "No error message provided.")
                logger.error(f"HTTP error {status_code} from {url}: {message}", exc_info=True)
                raise KiteConnectError(status_code=status_code, message=message, details=error_details) from e
            except Exception:
                # If parsing response fails, use default text
                message = str(e)
                logger.error(f"HTTP error {status_code} from {url}: {message}", exc_info=True)
                raise KiteConnectError(status_code=status_code, message=message) from e
        except httpx.TimeoutException as e:
            logger.error(f"Request timed out for {url}: {str(e)}", exc_info=True)
            raise KiteConnectError(status_code=408, message=f"Request timed out: {str(e)}") from e
        except httpx.RequestError as e:
            logger.error(f"Network or request error for {url}: {str(e)}", exc_info=True)
            raise KiteConnectError(status_code=503, message=f"Network error: {str(e)}") from e
        except KiteConnectError: # Re-raise specific Kite errors
            raise
        except Exception as e:
            logger.error(f"An unexpected error occurred during request to {url}: {str(e)}", exc_info=True)
            raise KiteConnectError(status_code=500, message=f"An unexpected error occurred: {str(e)}") from e

    async def place_order(self, params: PlaceOrderParams) -> OrderResponse:
        """Place an order."""
        endpoint = f"/orders/{params.variety}"
        # Prepare form data, excluding 'variety' and None values
        data = {k: v for k, v in params.dict(exclude={'variety'}).items() if v is not None}
        
        # Ensure numerical values are sent correctly for form data
        for key in ['quantity', 'price', 'trigger_price', 'disclosed_quantity', 'validity_ttl', 'iceberg_legs', 'iceberg_quantity']:
            if key in data:
                data[key] = str(data[key])

        response_data = await self._request("POST", endpoint, data=data)
        if 'order_id' not in response_data:
             logger.error(f"'order_id' not found in response data: {response_data}")
             raise KiteConnectError(status_code=500, message="'order_id' not found in response", details=response_data)
        return OrderResponse(order_id=response_data['order_id'])

    async def modify_order(self, params: ModifyOrderParams) -> OrderResponse:
        """Modify an existing order."""
        endpoint = f"/orders/{params.variety}/{params.order_id}"
        # Prepare form data, excluding 'variety', 'order_id', and None values
        data = {k: v for k, v in params.dict(exclude={'variety', 'order_id'}).items() if v is not None}
        
        # Ensure numerical values are sent correctly for form data
        for key in ['quantity', 'price', 'trigger_price', 'disclosed_quantity']:
             if key in data:
                data[key] = str(data[key])

        response_data = await self._request("PUT", endpoint, data=data)
        if 'order_id' not in response_data:
             logger.error(f"'order_id' not found in response data: {response_data}")
             raise KiteConnectError(status_code=500, message="'order_id' not found in response", details=response_data)
        return OrderResponse(order_id=response_data['order_id'])

    async def close(self):
        """Closes the underlying HTTPX client."""
        await self.client.aclose()
        logger.info("KiteConnectClient closed.")
