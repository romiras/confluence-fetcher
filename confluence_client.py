import requests
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin, urlsplit

class ConfluenceAPIError(Exception):
    """Custom exception for Confluence API errors"""

    def __init__(self, message: str, status_code: int, response_data: Optional[Dict] = None):
        self.status_code = status_code
        self.response_data = response_data
        super().__init__(f"{message} (Status: {status_code})")

class ConfluenceClient:
    """Client for interacting with the Confluence Cloud REST API"""

    def __init__(self, account_name: str, user_email: str, api_token: str):
        """Initialize the Confluence API client.

        Args:
            account_name: Confluence account name (e.g., 'mycompany' for mycompany.atlassian.net)
            user_email: User email for authentication
            api_token: API token for authentication
        """

        self.base_url = f"https://{account_name}.atlassian.net/wiki/api/v2"
        self.download_base_url = f"https://{account_name}.atlassian.net/wiki"  # Base URL for downloads without api/v2
        self.account_name = account_name
        self.auth = (user_email, api_token)
        self.headers = {
            "Accept": "application/json"
        }


    def _build_url(self, endpoint: str) -> str:
        """Construct the full API URL for a given endpoint."""

        res = urlsplit(self.base_url) # to handle existing path in base_url
        return urljoin(self.base_url, f"{res.path}{endpoint}")


    def _build_download_url(self, endpoint: str) -> str:
        """Construct the full download URL for a given endpoint."""

        res = urlsplit(self.download_base_url) # to handle existing path in base_url
        return urljoin(self.download_base_url, f"{res.path}{endpoint}")


    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make an HTTP request to the Confluence API with error handling.

        Args:
            method: HTTP method (get, post, etc.)
            endpoint: API endpoint (e.g., '/spaces')
            **kwargs: Additional arguments to pass to requests

        Returns:
            Dictionary containing the response data

        Raises:
            ConfluenceAPIError: If the API request fails
        """

        try:
            response = requests.request(
                method,
                self._build_url(endpoint),
                auth=self.auth,
                headers=self.headers,
                **kwargs
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            error_data = None
            try:
                error_data = e.response.json() if hasattr(e, 'response') else None
            except Exception:
                error_data = None
            raise ConfluenceAPIError(
                f"API request failed: {e}",
                response.status_code, # pyright: ignore[reportPossiblyUnboundVariable]
                error_data
            )
        except requests.exceptions.RequestException as e:
            raise ConfluenceAPIError(f"Request failed: {e}", 0)

    def _paginated_get(self, endpoint: str, **kwargs) -> List[Dict[str, Any]]:
        """Handle paginated GET requests to the Confluence API.

        Args:
            endpoint: API endpoint
            **kwargs: Additional arguments to pass to requests

        Returns:
            List of results from all pages
        """

        results = []
        next_url = endpoint

        while next_url:
            data = self._make_request('get', next_url, **kwargs)
            results.extend(data.get('results', []))
            
            # Handle pagination
            next_path = data.get('_links', {}).get('next')
            next_url = next_path.removeprefix('/wiki/api/v2') if next_path else None

        return results

    def get_spaces(self) -> List[Dict[str, Any]]:
        """Fetch all spaces from Confluence."""

        return self._paginated_get('/spaces')

    def get_pages_for_space(self, space_id: str) -> List[Dict[str, Any]]:
        """Fetch all pages for a given space.

        Args:
            space_id: The ID of the space

        Returns:
            List of pages in the space
        """
        return self._paginated_get(f'/spaces/{space_id}/pages')

    def get_page_content(self, page_id: str) -> Dict[str, Any]:
        """Get the content of a specific page.

        Args:
            page_id: The ID of the page

        Returns:
            Page content data
        """

        params = {
            "body-format": "storage",
            "status": "current"
        }
        return self._make_request('get', f'/pages/{page_id}', params=params)

    def get_page_attachments(self, page_id: str) -> List[Dict[str, Any]]:
        """Get all attachments for a specific page.

        Args:
            page_id: The ID of the page

        Returns:
            List of attachments
        """

        return self._paginated_get(f'/pages/{page_id}/attachments')

    def download_attachment(self, download_url: str) -> bytes:
        """Download an attachment from Confluence.

        Args:
            download_url: The URL to download the attachment from

        Returns:
            The attachment content as bytes
        """

        url = self._build_download_url(download_url)

        try:
            response = requests.get(
                url,
                auth=self.auth,
                stream=True
            )
            response.raise_for_status()
    
        except requests.exceptions.HTTPError as e:
            raise ConfluenceAPIError(f"Attachment download failed: {e}", response.status_code) # pyright: ignore[reportPossiblyUnboundVariable]
    
        return response.content
