"""Coordinator for eToll profile and vehicle vignette data."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import EtollAPI
from .const import CONF_USERNAME, DEFAULT_UPDATE_INTERVAL, DOMAIN
from .exceptions import EtollApiError, EtollAuthError, EtollConnectionError

_LOGGER = logging.getLogger(__name__)


class EtollCoordinator(DataUpdateCoordinator[dict]):
    """Fetch vehicles, bridge pass data, and invoices from eToll."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        api: EtollAPI,
        config_entry: ConfigEntry,
        update_interval: int = DEFAULT_UPDATE_INTERVAL,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_coordinator",
            update_interval=timedelta(seconds=update_interval),
            config_entry=config_entry,
        )
        self.api = api

    async def _async_update_data(self) -> dict:
        """Refresh data while preserving the previous coordinator data on errors."""
        try:
            vehicles = await self.api.get_vehicles()
            bridge_services: dict[str, list[dict]] = {}
            bridge_verification: dict[str, dict] = {}
            for vehicle in vehicles:
                plate = vehicle.get("plateNumber")
                vehicle_id = vehicle.get("id")
                if not plate:
                    continue
                bridge_services[plate] = await self._optional_fetch(
                    self.api.get_bridge_services(vehicle), [],
                    f"bridge services for {plate}",
                )
                if vehicle_id:
                    bridge_verification[plate] = await self._optional_fetch(
                        self.api.get_bridge_verification(vehicle_id), {},
                        f"bridge verification for {plate}",
                    )
            invoices = await self._optional_fetch(
                self.api.get_invoices(), [], "invoices"
            )
            return {
                "account_username": self.config_entry.data.get(CONF_USERNAME),
                "vehicles": vehicles,
                "bridge_services_by_vehicle": bridge_services,
                "bridge_verification_by_vehicle": bridge_verification,
                "invoices": invoices,
            }
        except EtollAuthError as err:
            raise ConfigEntryAuthFailed(f"eToll authentication failed: {err}") from err
        except (EtollApiError, EtollConnectionError) as err:
            raise UpdateFailed(f"Could not update eToll data: {err}") from err
        except Exception as err:
            _LOGGER.exception("Unexpected error while updating eToll data")
            raise UpdateFailed(f"Unexpected error while updating eToll data: {err}") from err

    @staticmethod
    async def _optional_fetch(coro, default, description: str):
        """Keep optional feature endpoint failures from disabling vehicle sensors."""
        try:
            return await coro
        except (EtollApiError, EtollAuthError, EtollConnectionError) as err:
            _LOGGER.warning("Could not fetch %s: %s", description, err)
            return default
