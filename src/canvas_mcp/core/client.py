"""HTTP client and Canvas API utilities."""

import asyncio
import re
from typing import Any
from urllib.parse import urlencode

import httpx

from .anonymization import anonymize_response_data
from .logging import log_debug, log_error, log_info

# Rate limit retry configuration
MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 2

# HTTP client will be initialized with configuration
http_client: httpx.AsyncClient | None = None


def _determine_data_type(endpoint: str) -> str:
    """Determine the type of data based on the API endpoint."""
    endpoint_lower = endpoint.lower()

    if "/users" in endpoint_lower:
        return "users"
    elif "/discussion_topics" in endpoint_lower and "/entries" in endpoint_lower:
        return "discussions"
    elif "/discussion" in endpoint_lower:
        return "discussions"
    elif "/submissions" in endpoint_lower:
        return "submissions"
    elif "/assignments" in endpoint_lower:
        return "assignments"
    elif "/enrollments" in endpoint_lower:
        return "users"  # Enrollments contain user data
    else:
        return "general"


def _should_anonymize_endpoint(endpoint: str) -> bool:
    """Determine if an endpoint should have its data anonymized."""
    # Don't anonymize these endpoints as they don't contain student data
    safe_endpoints = [
        "/courses",  # Course info without student data (unless it includes users)
        "/self",  # User's own profile
        "/accounts",  # Account information
        "/terms",  # Academic terms
    ]

    endpoint_lower = endpoint.lower()

    # Always anonymize discussion entries as they contain student posts
    if "/discussion_topics" in endpoint_lower and "/entries" in endpoint_lower:
        return True

    # Check if it's a safe endpoint
    for safe in safe_endpoints:
        if safe in endpoint_lower and "/users" not in endpoint_lower:
            return False

    # Anonymize endpoints that contain student data
    student_data_endpoints = [
        "/users",
        "/discussion",
        "/submissions",
        "/enrollments",
        "/groups",
        "/analytics",
    ]

    return any(
        student_endpoint in endpoint_lower
        for student_endpoint in student_data_endpoints
    )


def _get_http_client() -> httpx.AsyncClient:
    """Get or create the HTTP client with current configuration."""
    global http_client
    if http_client is None:
        from .. import __version__
        from .config import get_config

        config = get_config()
        http_client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {config.api_token}",
                "User-Agent": f"canvas-mcp/{__version__} (https://github.com/vishalsachdev/canvas-mcp)",
            },
            timeout=config.api_timeout,
        )
    return http_client


async def cleanup_http_client() -> None:
    """Close the HTTP client and release resources."""
    global http_client
    if http_client is not None:
        await http_client.aclose()
        http_client = None


async def make_canvas_request(
    method: str,
    endpoint: str,
    params: dict[str, Any] | None = None,
    data: dict[str, Any] | list[tuple[str, str]] | None = None,
    use_form_data: bool = False,
    skip_anonymization: bool = False,
) -> Any:
    """Make a request to the Canvas API with proper error handling.

    Automatically retries on rate limit errors (429) with exponential backoff.

    Args:
        method: HTTP method (get, post, put, delete)
        endpoint: Canvas API endpoint
        params: Query parameters
        data: Request body data
        use_form_data: Use form data instead of JSON
        skip_anonymization: Skip anonymization (used by paginated fetchers)
    """

    from .config import get_config

    config = get_config()
    client = _get_http_client()

    # Ensure the endpoint starts with a slash
    if not endpoint.startswith("/"):
        endpoint = f"/{endpoint}"

    # Construct the full URL
    url = f"{config.api_base_url.rstrip('/')}{endpoint}"

    # Retry loop for rate limiting
    for attempt in range(MAX_RETRIES + 1):
        try:
            # Log the request for debugging (if enabled)
            if config.log_api_requests:
                retry_info = f" (retry {attempt}/{MAX_RETRIES})" if attempt > 0 else ""
                log_debug(f"Making {method.upper()} request to {url}{retry_info}")

            if method.lower() == "get":
                response = await client.get(url, params=params)
            elif method.lower() == "post":
                if use_form_data:
                    # Handle list of tuples separately to work around httpx async bug
                    # with duplicate keys (e.g., module[prerequisite_module_ids][])
                    if isinstance(data, list):
                        encoded = urlencode(data)
                        response = await client.post(
                            url,
                            content=encoded,
                            headers={
                                "Content-Type": "application/x-www-form-urlencoded"
                            },
                        )
                    else:
                        response = await client.post(url, data=data)
                else:
                    response = await client.post(url, json=data)
            elif method.lower() == "put":
                if use_form_data:
                    # Handle list of tuples separately to work around httpx async bug
                    if isinstance(data, list):
                        encoded = urlencode(data)
                        response = await client.put(
                            url,
                            content=encoded,
                            headers={
                                "Content-Type": "application/x-www-form-urlencoded"
                            },
                        )
                    else:
                        response = await client.put(url, data=data)
                else:
                    response = await client.put(url, json=data)
            elif method.lower() == "delete":
                response = await client.delete(url, params=params)
            else:
                return {"error": f"Unsupported method: {method}"}

            response.raise_for_status()
            result = response.json()

            # Apply anonymization if enabled and this endpoint contains student data
            # Skip if explicitly requested (e.g., from paginated fetcher that will anonymize the full result)
            if (
                not skip_anonymization
                and config.enable_data_anonymization
                and _should_anonymize_endpoint(endpoint)
            ):
                data_type = _determine_data_type(endpoint)
                result = anonymize_response_data(result, data_type)

                # Log anonymization for debugging (if enabled)
                if config.anonymization_debug:
                    log_info(f"Applied {data_type} anonymization to {endpoint}")

            return result

        except httpx.HTTPStatusError as e:
            # Handle rate limiting with exponential backoff
            if e.response.status_code == 429 and attempt < MAX_RETRIES:
                # Check for Retry-After header
                retry_after = e.response.headers.get("Retry-After")
                if retry_after:
                    try:
                        wait_time = int(retry_after)
                    except ValueError:
                        wait_time = INITIAL_BACKOFF_SECONDS * (2**attempt)
                else:
                    wait_time = INITIAL_BACKOFF_SECONDS * (2**attempt)

                log_debug(
                    f"Rate limited (429). Retrying in {wait_time}s... (attempt {attempt + 1}/{MAX_RETRIES})"
                )
                await asyncio.sleep(wait_time)
                continue

            # Not a rate limit error or out of retries - format and return error
            error_message = f"HTTP error: {e.response.status_code}"
            try:
                error_details = e.response.json()
                error_message += f", Details: {error_details}"
            except ValueError:
                error_details = e.response.text
                error_message += f", Text: {error_details}"

            log_error(f"API error: {error_message}")
            return {"error": error_message}

        except Exception as e:
            log_error(f"Request failed: {str(e)}")
            return {"error": f"Request failed: {str(e)}"}

    # Should never reach here, but just in case
    return {"error": "Max retries exceeded"}


async def upload_file_multipart(
    upload_url: str,
    upload_params: dict[str, Any],
    file_path: str,
) -> Any:
    """Upload a file to Canvas via multipart POST (Step 2 of 3-step file upload).

    Canvas file uploads go to an external URL (e.g., S3) that does NOT
    accept Canvas auth headers. This function uses a fresh httpx client.

    Args:
        upload_url: The URL returned by the file upload slot request.
        upload_params: Form fields returned by the file upload slot request.
        file_path: Local path to the file to upload.
    """
    import mimetypes
    from pathlib import Path

    path = Path(file_path)
    if not path.exists():
        return {"error": f"File not found: {file_path}"}

    content_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"

    # Build multipart fields from upload_params + the file itself
    files = {"file": (path.name, path.read_bytes(), content_type)}

    try:
        async with httpx.AsyncClient(timeout=120.0, follow_redirects=False) as client:
            response = await client.post(
                upload_url,
                data=upload_params,
                files=files,
            )

            # Canvas returns 200/201 with JSON on direct uploads
            if response.status_code in (200, 201):
                return response.json()

            # S3 returns 301/302/303 redirect to Canvas confirmation URL
            if response.status_code in (301, 302, 303):
                redirect_url = response.headers.get("Location")
                if redirect_url:
                    # Follow the redirect WITH Canvas auth headers
                    canvas_client = _get_http_client()
                    confirm = await canvas_client.get(redirect_url)
                    confirm.raise_for_status()
                    return confirm.json()
                return {"error": "Redirect with no Location header"}

            return {
                "error": f"Upload failed with status {response.status_code}: {response.text}"
            }

    except Exception as e:
        return {"error": f"File upload failed: {str(e)}"}


def _parse_link_header(header: str) -> dict[str, str]:
    """Parse a Link header into a dict of rel → URL mappings.

    Example input: '<https://...?page=2>; rel="next", <https://...?page=1>; rel="prev"'
    Returns: {"next": "https://...?page=2", "prev": "https://...?page=1"}
    """
    links: dict[str, str] = {}
    for part in header.split(","):
        match = re.match(r'\s*<([^>]+)>\s*;\s*rel="([^"]+)"', part.strip())
        if match:
            links[match.group(2)] = match.group(1)
    return links


async def fetch_all_paginated_results(
    endpoint: str,
    params: dict[str, Any] | None = None,
    *,
    skip_anonymization: bool = False,
) -> Any:
    """Fetch all results from a paginated Canvas API endpoint.

    Follows Link header pagination (rel="next") instead of page numbers,
    which is required by Canvas for many endpoints. Applies anonymization
    once to the complete dataset.

    Args:
        endpoint: The Canvas API endpoint to fetch from
        params: Query parameters for the request
        skip_anonymization: If True, skip anonymization entirely (for internal tools like anonymization map)
    """
    from .config import get_config

    config = get_config()
    client = _get_http_client()

    if params is None:
        params = {}

    if "per_page" not in params:
        params["per_page"] = 100

    # Build the initial URL
    if not endpoint.startswith("/"):
        endpoint = f"/{endpoint}"
    url: str | None = f"{config.api_base_url.rstrip('/')}{endpoint}"

    all_results: list[Any] = []

    while url:
        try:
            response = await client.get(url, params=params if not all_results else None)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            error_detail = str(e)
            try:
                error_detail = e.response.json()
            except Exception:
                pass
            log_error(f"HTTP error fetching {url}: {error_detail}")
            return {"error": f"HTTP error: {e.response.status_code}, Details: {error_detail}"}
        except httpx.RequestError as e:
            log_error(f"Request error fetching {url}: {e}")
            return {"error": f"Request error: {e}"}

        data = response.json()

        if isinstance(data, dict) and "error" in data:
            log_error(f"API error fetching {url}: {data['error']}")
            return data

        if not data or not isinstance(data, list) or len(data) == 0:
            break

        all_results.extend(data)

        # Follow Link header for next page
        link_header = response.headers.get("link", "")
        links = _parse_link_header(link_header) if link_header else {}
        url = links.get("next")

    # Apply anonymization to the complete result set if needed
    if not skip_anonymization:
        if config.enable_data_anonymization and _should_anonymize_endpoint(endpoint):
            data_type = _determine_data_type(endpoint)
            all_results = anonymize_response_data(all_results, data_type)

            if config.anonymization_debug:
                log_info(
                    f"Applied {data_type} anonymization to paginated results from {endpoint}"
                )

    return all_results


async def poll_canvas_progress(
    progress_url: str | int,
    *,
    max_wait_seconds: float = 120.0,
    initial_interval: float = 1.0,
    max_interval: float = 5.0,
) -> dict[str, Any]:
    """Poll a Canvas Progress object until completion or timeout.

    Canvas async operations (bulk grade updates, content migrations, etc.)
    return a Progress object. This function polls until workflow_state
    reaches 'completed' or 'failed', or until the timeout is exceeded.

    Args:
        progress_url: The Progress object URL (e.g., /api/v1/progress/123)
                     or just the progress ID
        max_wait_seconds: Maximum total time to wait (default: 120s)
        initial_interval: Initial polling interval in seconds (default: 1s)
        max_interval: Maximum polling interval in seconds (default: 5s)

    Returns:
        dict with keys: completed, workflow_state, completion, message,
        progress_id, error
    """
    import time

    # Handle both full URL and bare ID
    if isinstance(progress_url, (int, float)):
        endpoint = f"/progress/{int(progress_url)}"
    elif str(progress_url).isdigit():
        endpoint = f"/progress/{progress_url}"
    elif "/api/v1/" in str(progress_url):
        endpoint = str(progress_url).split("/api/v1", 1)[1]
    elif str(progress_url).startswith("/"):
        endpoint = str(progress_url)
    else:
        endpoint = f"/progress/{progress_url}"

    progress_id = endpoint.rstrip("/").split("/")[-1]
    start_time = time.monotonic()
    interval = initial_interval

    while True:
        elapsed = time.monotonic() - start_time
        if elapsed >= max_wait_seconds:
            return {
                "completed": False,
                "workflow_state": "timeout",
                "completion": 0,
                "message": f"Polling timed out after {max_wait_seconds}s",
                "progress_id": progress_id,
                "error": f"Operation still in progress after {max_wait_seconds}s. "
                f"Check manually with GET /api/v1{endpoint}",
            }

        response = await make_canvas_request("get", endpoint, skip_anonymization=True)

        if isinstance(response, dict) and "error" in response:
            return {
                "completed": False,
                "workflow_state": "error",
                "completion": 0,
                "message": None,
                "progress_id": progress_id,
                "error": f"Failed to check progress: {response['error']}",
            }

        workflow_state = response.get("workflow_state", "unknown")
        completion = response.get("completion", 0) or 0
        message = response.get("message")

        if workflow_state == "completed":
            return {
                "completed": True,
                "workflow_state": "completed",
                "completion": 100,
                "message": message,
                "progress_id": response.get("id"),
                "error": None,
            }

        if workflow_state == "failed":
            return {
                "completed": True,
                "workflow_state": "failed",
                "completion": completion,
                "message": message,
                "progress_id": response.get("id"),
                "error": f"Bulk operation failed: {message or 'unknown error'}",
            }

        # Still running -- wait and retry
        await asyncio.sleep(interval)
        interval = min(interval * 1.5, max_interval)
