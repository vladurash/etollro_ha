"""Async client for the eToll portal API."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import logging
import time
from urllib.parse import urlencode, urlsplit

import aiohttp

from .const import (
    ETOLL_BASE_URL,
    KEYCLOAK_CLIENT_ID,
    KEYCLOAK_TOKEN_URL,
    VEHICLES_PAGE_SIZE,
)
from .exceptions import (
    EtollApiError,
    EtollAuthError,
    EtollConnectionError,
)

_LOGGER = logging.getLogger(__name__)


class EtollAPI:
    """Authenticated, read-only client for eToll vehicle data."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        username: str,
        password: str,
    ) -> None:
        self._session = session
        self._username = username
        self._password = password
        self._access_token: str | None = None
        self._token_expires_at = 0.0

    @property
    def authenticated(self) -> bool:
        """Return whether the in-memory access token is still usable."""
        return bool(self._access_token) and time.monotonic() < self._token_expires_at

    async def authenticate(self) -> None:
        """Get an access token using the Keycloak password grant."""
        self._access_token = None
        self._token_expires_at = 0
        try:
            async with self._session.post(
                KEYCLOAK_TOKEN_URL,
                data={
                    "grant_type": "password",
                    "client_id": KEYCLOAK_CLIENT_ID,
                    "username": self._username,
                    "password": self._password,
                },
                headers={"Accept": "application/json"},
            ) as response:
                payload = await self._read_json(response)
                if not isinstance(payload, dict):
                    raise EtollApiError("Keycloak returned an unexpected JSON response")
                if response.status in (400, 401):
                    detail = payload.get("error_description") or payload.get("error")
                    raise EtollAuthError(
                        f"Keycloak rejected the credentials: {detail or response.status}"
                    )
                if response.status != 200:
                    raise EtollApiError(
                        f"Keycloak token request failed (HTTP {response.status})"
                    )
        except EtollAuthError:
            raise
        except EtollApiError:
            raise
        except (aiohttp.ClientError, TimeoutError) as err:
            raise EtollConnectionError(
                f"Connection to Keycloak failed: {err}"
            ) from err

        access_token = payload.get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise EtollApiError("Keycloak response did not contain an access token")
        try:
            expires_in = max(1, int(payload["expires_in"]))
        except (KeyError, TypeError, ValueError) as err:
            raise EtollApiError(
                "Keycloak response did not contain a valid expires_in value"
            ) from err

        self._access_token = access_token
        # Refresh a little early to avoid sending a token at its expiry boundary.
        self._token_expires_at = time.monotonic() + max(1, expires_in - 30)
        _LOGGER.debug("Authenticated to eToll; token lifetime is %d seconds", expires_in)

    async def _read_json(self, response: aiohttp.ClientResponse) -> dict | list:
        """Read a JSON response and convert malformed payloads to API errors."""
        try:
            payload = await response.json(content_type=None)
        except (aiohttp.ContentTypeError, ValueError) as err:
            body = (await response.text())[:200]
            raise EtollApiError(
                f"Expected JSON from eToll (HTTP {response.status}): {body}"
            ) from err
        if not isinstance(payload, (dict, list)):
            raise EtollApiError("eToll returned an unexpected JSON response")
        return payload

    async def _request_json(
        self,
        url: str,
        *,
        method: str = "GET",
        json_data: dict | None = None,
        retry_auth: bool = True,
    ) -> dict | list:
        """Make an authenticated request and retry once after HTTP 401."""
        if not self.authenticated:
            await self.authenticate()

        try:
            async with self._session.request(
                method,
                url,
                json=json_data,
                headers={
                    "Authorization": f"Bearer {self._access_token}",
                    "Accept": "application/json",
                },
            ) as response:
                if response.status == 401 and retry_auth:
                    await response.read()
                    self._access_token = None
                    self._token_expires_at = 0
                    await self.authenticate()
                    return await self._request_json(
                        url,
                        method=method,
                        json_data=json_data,
                        retry_auth=False,
                    )
                if response.status == 401:
                    raise EtollAuthError(
                        "eToll rejected the refreshed access token for "
                        f"{urlsplit(url).path}"
                    )
                if response.status == 429:
                    await self._wait_for_retry(response.headers.get("Retry-After"))
                    raise EtollApiError("eToll rate limit reached; retry after the indicated delay")
                if response.status < 200 or response.status >= 300:
                    body = (await response.text())[:200]
                    raise EtollApiError(
                        f"eToll API request failed (HTTP {response.status}): {body}"
                    )
                return await self._read_json(response)
        except (EtollAuthError, EtollApiError):
            raise
        except (aiohttp.ClientError, TimeoutError) as err:
            raise EtollConnectionError(
                f"Request to eToll failed: {err}"
            ) from err

    @staticmethod
    async def _wait_for_retry(retry_after: str | None) -> None:
        """Honor a valid Retry-After value before returning a rate-limit error."""
        if not retry_after:
            return
        try:
            delay = max(0.0, float(retry_after))
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(retry_after)
                if retry_at.tzinfo is None:
                    retry_at = retry_at.replace(tzinfo=timezone.utc)
                delay = max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
            except (TypeError, ValueError, OverflowError):
                return
        # Avoid sleeping through a Home Assistant shutdown for a malformed server value.
        await asyncio.sleep(delay)

    @staticmethod
    def _page_items_and_cursor(payload: dict) -> tuple[list[dict], str | None]:
        """Extract vehicles and a continuation cursor from common page envelopes."""
        items: list[dict] | None = None
        for key in ("items", "content", "vehicles", "results", "view"):
            candidate = payload.get(key)
            if isinstance(candidate, list):
                items = candidate
                break
        if items is None and isinstance(payload.get("data"), list):
            items = payload["data"]
        if items is None:
            raise EtollApiError(
                "Vehicle response did not contain a recognized list; runtime response shape needs confirmation"
            )

        cursor: str | None = None
        for key in ("nextCursor", "next_cursor", "next", "cursor"):
            value = payload.get(key)
            if isinstance(value, str) and value:
                cursor = value
                break
        page_info = payload.get("pageInfo") or payload.get("pagination")
        if cursor is None and isinstance(page_info, dict):
            for key in ("nextCursor", "next_cursor", "next"):
                value = page_info.get(key)
                if isinstance(value, str) and value:
                    cursor = value
                    break
        return [item for item in items if isinstance(item, dict)], cursor

    async def get_vehicles(self) -> list[dict]:
        """Fetch all CAR vehicles, following cursor pagination when present."""
        vehicles: list[dict] = []
        cursor: str | None = None
        seen_cursors: set[str] = set()

        for _ in range(100):
            params = {
                "vehicleType": "CAR",
                "computeVignetteEligibility": "true",
                "size": VEHICLES_PAGE_SIZE,
            }
            if cursor:
                params["cursor"] = cursor
            payload = await self._request_json(
                f"{ETOLL_BASE_URL}/api/vehicles?{urlencode(params)}"
            )
            if not isinstance(payload, dict):
                raise EtollApiError("Vehicle response was not a page object")
            page, next_cursor = self._page_items_and_cursor(payload)
            vehicles.extend(self._normalize_vehicle(vehicle) for vehicle in page)
            if not next_cursor or next_cursor in seen_cursors:
                return vehicles
            seen_cursors.add(next_cursor)
            cursor = next_cursor

        raise EtollApiError("Vehicle pagination exceeded 100 pages")

    async def get_bridge_services(self, vehicle: dict) -> list[dict]:
        """Fetch BRIDGE service records filtered to one registered vehicle."""
        services: list[dict] = []
        cursor: str | None = None
        seen_cursors: set[str] = set()
        for _ in range(100):
            params = {
                "type": "BRIDGE",
                "orderBy": "DSC",
                "size": VEHICLES_PAGE_SIZE,
            }
            for field in ("category", "countryCode", "plateNumber", "vin"):
                value = vehicle.get(field)
                if value:
                    params[field] = value
            if cursor:
                params["cursor"] = cursor
            payload = await self._request_json(
                f"{ETOLL_BASE_URL}/api/tolls?{urlencode(params)}"
            )
            if not isinstance(payload, dict):
                raise EtollApiError("Bridge service response was not an object")
            page = payload.get("tolls")
            if not isinstance(page, list):
                raise EtollApiError("Bridge service response did not contain tolls")
            services.extend(item for item in page if isinstance(item, dict))
            next_cursor = payload.get("nextCursor")
            if not isinstance(next_cursor, str) or not next_cursor or next_cursor in seen_cursors:
                return services
            seen_cursors.add(next_cursor)
            cursor = next_cursor
        raise EtollApiError("Bridge service pagination exceeded 100 pages")

    async def get_bridge_verification(self, vehicle_id: str) -> dict:
        """Fetch read-only bridge pass verification for a saved vehicle."""
        payload = await self._request_json(
            f"{ETOLL_BASE_URL}/api/tolls/verification",
            method="POST",
            json_data={"vehicleId": vehicle_id, "types": ["BRIDGE"]},
        )
        if not isinstance(payload, dict):
            raise EtollApiError("Bridge verification response was not an object")
        return payload

    async def get_invoices(self) -> list[dict]:
        """Fetch invoices for the current profile."""
        payload = await self._request_json(f"{ETOLL_BASE_URL}/api/invoices")
        if not isinstance(payload, list):
            raise EtollApiError("Invoice response was not a list")
        return [invoice for invoice in payload if isinstance(invoice, dict)]

    @staticmethod
    def _normalize_vehicle(vehicle: dict) -> dict:
        """Keep the eToll fields used by sensors in one small internal record."""
        eligibility = vehicle.get("vignetteEligibility")
        if not isinstance(eligibility, dict):
            eligibility = {}
        return {
            "id": vehicle.get("id"),
            "plateNumber": vehicle.get("plateNumber"),
            "vehicleType": vehicle.get("vehicleType"),
            "country": vehicle.get("country"),
            "countryCode": vehicle.get("countryCode"),
            "countryType": vehicle.get("countryType"),
            "vin": vehicle.get("vin"),
            "category": vehicle.get("category"),
            "emissionStandard": vehicle.get("emissionStandard"),
            "mtma": vehicle.get("mtma"),
            "isValid": vehicle.get("isValid"),
            "favorite": vehicle.get("favorite"),
            "lastEvent": vehicle.get("lastEvent"),
            "registrationSerial": vehicle.get("registrationSerial"),
            "strrPeajCategoryCode": vehicle.get("strrPeajCategoryCode"),
            "temporaryPlate": vehicle.get("temporaryPlate"),
            "trailerCategory": vehicle.get("trailerCategory"),
            "eligibleIntervals": eligibility.get("eligibleIntervals"),
            "expirationDateCurrentVignette": eligibility.get(
                "expirationDateCurrentVignette"
            ),
        }
