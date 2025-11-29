"""
Image utilities for downloading and handling images.
"""
import httpx
from typing import Optional


async def download_image(url: str, timeout: float = 120.0) -> bytes:
    """
    Download image from a URL.
    
    Args:
        url: URL to download the image from
        timeout: Request timeout in seconds (default: 120.0 for mobile uploads)
        
    Returns:
        Image bytes
        
    Raises:
        httpx.HTTPStatusError: If the response status is not successful
        httpx.RequestError: If the request fails
    """
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.content


async def download_image_with_retry(
    url: str,
    max_retries: int = 3,
    timeout: float = 120.0
) -> Optional[bytes]:
    """
    Download image from a URL with retry logic.
    
    Args:
        url: URL to download the image from
        max_retries: Maximum number of retry attempts (default: 3)
        timeout: Request timeout in seconds (default: 120.0 for mobile uploads)
        
    Returns:
        Image bytes if successful, None if all retries fail
    """
    for attempt in range(max_retries):
        try:
            return await download_image(url, timeout)
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            if attempt == max_retries - 1:
                print(f"Failed to download image after {max_retries} attempts: {str(e)}")
                raise
            print(f"Download attempt {attempt + 1} failed, retrying...")
            continue
    
    return None
