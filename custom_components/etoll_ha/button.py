"""Button platform for the eToll integration."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, VERSION
from .coordinator import EtollCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the manual refresh button."""
    coordinator: EtollCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([EtollRefreshButton(coordinator, config_entry)])


class EtollRefreshButton(CoordinatorEntity[EtollCoordinator], ButtonEntity):
    """Refresh eToll data immediately when pressed."""

    _attr_has_entity_name = True
    _attr_translation_key = "refresh"
    _attr_icon = "mdi:refresh"

    def __init__(
        self, coordinator: EtollCoordinator, config_entry: ConfigEntry
    ) -> None:
        """Initialize the refresh button."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._attr_unique_id = f"{DOMAIN}_refresh_{config_entry.entry_id}"

    @property
    def device_info(self) -> DeviceInfo:
        """Associate the button with the eToll service device."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._config_entry.entry_id)},
            name="eToll",
            manufacturer="eToll",
            model="eToll",
            sw_version=VERSION,
            entry_type=DeviceEntryType.SERVICE,
        )

    async def async_press(self) -> None:
        """Request an immediate update through the normal coordinator flow."""
        await self.coordinator.async_request_refresh()