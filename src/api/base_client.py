"""
Base API client with common functionality
"""

import time
import asyncio
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import httpx
from src.utils.logger import logger
from src.config.constants import MAX_RETRIES, RETRY_DELAY


class BaseAPIClient(ABC):
    """Base class for API clients with common functionality"""
    
    def __init__(self, base_url: str, timeout: int = 30):
        """
        Initialize base API client
        
        Args:
            base_url: Base URL for API
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)
        self.logger = logger
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[str] = None,
        retries: int = MAX_RETRIES,
    ) -> Dict[str, Any]:
        """
        Make HTTP request with retry logic
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint
            headers: Request headers
            params: Query parameters
            json_data: JSON body
            retries: Number of retry attempts
            
        Returns:
            Response data as dictionary
            
        Raises:
            httpx.HTTPError: If request fails after all retries
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        for attempt in range(retries):
            try:
                self.logger.debug(f"Request: {method} {url} (attempt {attempt + 1}/{retries})")
                
                request_kwargs = {
                    "method": method,
                    "url": url,
                    "headers": headers,
                    "params": params,
                }
                
                if json_data is not None:
                    request_kwargs["json"] = json_data
                    self.logger.debug(f"Request JSON data: {json_data}")
                elif data is not None:
                    request_kwargs["content"] = data
                    self.logger.debug(f"Request data (first 200 chars): {data[:200]}")
                
                response = await self.client.request(**request_kwargs)
                
                # Log response for debugging
                self.logger.debug(f"Response status: {response.status_code}")
                if response.status_code >= 400:
                    try:
                        error_body = response.text[:1000]  # First 1000 chars
                        self.logger.warning(f"Error response body: {error_body}")
                    except:
                        pass
                
                response.raise_for_status()
                
                # Handle empty response (204 No Content or empty body)
                if response.status_code == 204:
                    return {}
                
                # Check if response body is empty
                try:
                    content = response.text.strip()
                    if not content:
                        return {}
                    return response.json()
                except ValueError:
                    # If JSON parsing fails but we got 2xx, return empty dict
                    if 200 <= response.status_code < 300:
                        return {}
                    raise
                
            except httpx.HTTPStatusError as e:
                if attempt < retries - 1:
                    self.logger.warning(
                        f"Request failed with status {e.response.status_code}, "
                        f"retrying in {RETRY_DELAY} seconds..."
                    )
                    await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                else:
                    self.logger.error(f"Request failed after {retries} attempts: {e}")
                    raise
            
            except httpx.RequestError as e:
                if attempt < retries - 1:
                    self.logger.warning(
                        f"Request error: {e}, retrying in {RETRY_DELAY} seconds..."
                    )
                    await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                else:
                    self.logger.error(f"Request error after {retries} attempts: {e}")
                    raise
    
    async def get(
        self,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make GET request"""
        return await self._request("GET", endpoint, headers=headers, params=params)
    
    async def post(
        self,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        data: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Make POST request"""
        return await self._request("POST", endpoint, headers=headers, params=params, json_data=json_data, data=data)
    
    async def put(
        self,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make PUT request"""
        return await self._request("PUT", endpoint, headers=headers, params=params, json_data=json_data)
    
    async def delete(
        self,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make DELETE request"""
        return await self._request("DELETE", endpoint, headers=headers, params=params)
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()
