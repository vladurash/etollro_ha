"""Sensor platform for the eToll vehicle vignette integration.

Active sensors:
- DateUtilizatorSensor: configured account connection status
- VehiculSensor: current vignette status per vehicle
- Bridge pass, crossing, balance, and invoice sensors

Unpaid bridge detection remains Unknown because no matching eToll endpoint is
confirmed in the portal client.
"""

from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    ATTRIBUTION,
    DOMAIN,
    # LICENSE_DATA_KEY,
    MAX_ATTR_TRECERI,
    VERSION,
)
from .coordinator import EtollCoordinator
from .helpers import sanitize_plate_no

_LOGGER = logging.getLogger(__name__)


# # =====================================================================
# #  Funcții Helper
# # =====================================================================


# # def _is_license_valid(hass: HomeAssistant) -> bool:
# #     """Verifică dacă licența este validă."""
# #     mgr = hass.data.get(DOMAIN, {}).get(LICENSE_DATA_KEY)
# #     return mgr is not None and mgr.is_valid


# =====================================================================
#  Setup
# =====================================================================


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configurează senzorii pe baza unei intrări de configurare."""
    coordinator: EtollCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    if not coordinator.data:
        _LOGGER.error("Nu există date de la coordinator. Senzorii nu pot fi creați.")
        return

    sensors: list[SensorEntity] = []

    # # # Verifică validitatea licenței
    # # license_valid = _is_license_valid(hass)

    # # if not license_valid:
    # #     # Curăță senzorii normali orfani din Entity Registry
    # #     registru = er.async_get(hass)
    # #     licenta_uid = f"{DOMAIN}_licenta_necesara_{config_entry.entry_id}"
    # #     for entry_reg in er.async_entries_for_config_entry(
    # #         registru, config_entry.entry_id
    # #     ):
    # #         if (
    # #             entry_reg.domain == "sensor"
    # #             and entry_reg.unique_id != licenta_uid
    # #         ):
    # #             registru.async_remove(entry_reg.entity_id)
    # #             _LOGGER.debug(
    # #                 "[eToll] Senzor orfan eliminat (licență expirată): %s",
    # #                 entry_reg.entity_id,
    # #             )
    # #     # Dacă nu avem licență validă, adaugă doar LicentaNecesaraSensor
    # #     sensors.append(LicentaNecesaraSensor(coordinator, config_entry))
    # # else:
    # Curăță senzorul de licență orfan (dacă exista anterior)
    registru = er.async_get(hass)
    licenta_uid = f"{DOMAIN}_licenta_necesara_{config_entry.entry_id}"
    entitate_licenta = registru.async_get_entity_id("sensor", DOMAIN, licenta_uid)
    if entitate_licenta is not None:
        registru.async_remove(entitate_licenta)
        _LOGGER.debug(
            "[eToll] Entitate LicentaNecesaraSensor orfană eliminată: %s",
            entitate_licenta,
        )

    # Dacă licența e validă, adaugă toți senzorii normali
    # Senzor utilizator
    sensors.append(DateUtilizatorSensor(coordinator, config_entry))

    # First phase: current vignette status for each vehicle from eToll.
    for vehicle in coordinator.data.get("vehicles", []):
        plate_no = vehicle.get("plateNumber")
        if not plate_no:
            _LOGGER.warning("eToll returned a vehicle without a plate number")
            continue
        sensors.extend(
            [
                VehiculSensor(coordinator, config_entry, plate_no),
                PlataTreceriPodSensor(coordinator, config_entry, plate_no),
                TreceriPodSensor(coordinator, config_entry, plate_no),
                SoldSensor(coordinator, config_entry, plate_no),
            ]
        )

    sensors.append(RaportTranzactiiSensor(coordinator, config_entry))

    if sensors:
        async_add_entities(sensors)
        _LOGGER.info("Au fost adăugați %d senzori eToll.", len(sensors))


# =====================================================================
#  Clasa de bază
# =====================================================================


class EtollBaseSensor(CoordinatorEntity[EtollCoordinator], SensorEntity):
    """Clasa de bază pentru toți senzorii eToll."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION

    def __init__(
        self,
        coordinator: EtollCoordinator,
        config_entry: ConfigEntry,
        name: str,
        unique_id: str,
        icon: str | None = None,
    ) -> None:
        """Inițializează senzorul de bază."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._attr_name = name
        self._attr_unique_id = unique_id
        self._attr_icon = icon

    # @property
    # def _license_valid(self) -> bool:
    #     """Verifică dacă licența este validă."""
    #     mgr = self.hass.data.get(DOMAIN, {}).get(LICENSE_DATA_KEY)
    #     return mgr is not None and mgr.is_valid

    @property
    def device_info(self) -> DeviceInfo:
        """Informații despre dispozitiv.

        IMPORTANT: Device name = "eToll" → entity_id = sensor.etoll_*
        (HA generează entity_id din slug(device_name) + slug(entity_name))
        """
        return DeviceInfo(
            identifiers={(DOMAIN, self._config_entry.entry_id)},
            name="eToll",
            manufacturer="eToll",
            model="eToll",
            sw_version=VERSION,
            entry_type=DeviceEntryType.SERVICE,
        )


# # =====================================================================
# #  LicentaNecesaraSensor
# # =====================================================================


# class LicentaNecesaraSensor(EtollBaseSensor):
#     """Senzor care afișează mesajul de licență necesară."""

#     def __init__(
#         self, coordinator: EtollCoordinator, config_entry: ConfigEntry
#     ) -> None:
#         """Inițializare."""
#         super().__init__(
#             coordinator=coordinator,
#             config_entry=config_entry,
#             name="eToll",
#             unique_id=f"{DOMAIN}_licenta_necesara_{config_entry.entry_id}",
#             icon="mdi:license",
#         )

#     @property
#     def native_value(self) -> str:
#         """Returnează mesajul de licență necesară."""
#         return "Licență necesară"

#     @property
#     def extra_state_attributes(self) -> dict:
#         """Atribute suplimentare cu informații despre licență."""
#         return {
#             "status": "Licență necesară",
#             "info": "Pentru a activa senzorii, este necesară o licență validă. Vizitați https://hubinteligent.org pentru mai multe detalii.",
#             "attribution": ATTRIBUTION,
#         }


# =====================================================================
#  DateUtilizatorSensor
# =====================================================================


class DateUtilizatorSensor(EtollBaseSensor):
    """Senzor cu datele contului utilizatorului."""

    def __init__(
        self, coordinator: EtollCoordinator, config_entry: ConfigEntry
    ) -> None:
        """Inițializare."""
        super().__init__(
            coordinator=coordinator,
            config_entry=config_entry,
            name="Date utilizator",
            unique_id=f"{DOMAIN}_date_utilizator_account_{config_entry.entry_id}",
            icon="mdi:account-details",
        )

    @property
    def native_value(self) -> str:
        """Return connected state without relying on the profile API route."""
        if not self.coordinator.data:
            return "nespecificat"
        return (
            "Conectat"
            if self.coordinator.data.get("account_username")
            else "nespecificat"
        )

    @property
    def extra_state_attributes(self) -> dict:
        """Return the configured account identifier."""
        username = (self.coordinator.data or {}).get("account_username")
        return {"username": username} if username else {}


# =====================================================================
#  VehiculSensor
# =====================================================================


class VehiculSensor(EtollBaseSensor):
    """Senzor pentru starea rovinietei unui vehicul.

    CORECȚIE: Datele vehiculului sunt citite din coordinator la fiecare
    actualizare (nu mai folosim referință stale din __init__).
    """

    def __init__(
        self,
        coordinator: EtollCoordinator,
        config_entry: ConfigEntry,
        plate_no: str,
    ) -> None:
        """Inițializare cu numărul de înmatriculare."""
        sanitized = sanitize_plate_no(plate_no)
        super().__init__(
            coordinator=coordinator,
            config_entry=config_entry,
            name=f"Rovinietă activă ({plate_no})",
            unique_id=f"{DOMAIN}_vehicul_{sanitized}_{config_entry.entry_id}",
            icon="mdi:car",
        )
        self._plate_no = plate_no

    def _get_vehicle_data(self) -> dict:
        """Obține datele actuale ale vehiculului din coordinator."""
        if not self.coordinator.data:
            return {}
        for item in self.coordinator.data.get("vehicles", []):
            if item.get("plateNumber") == self._plate_no:
                return item
        return {}

    @property
    def native_value(self) -> str:
        """Returnează 'Da' dacă vehiculul are rovinietă activă, altfel 'Nu'."""
        # if not self._license_valid:
        #     return "Licență necesară"
        vehicle = self._get_vehicle_data()
        expiration = dt_util.parse_datetime(
            vehicle.get("expirationDateCurrentVignette") or ""
        )
        if expiration is None:
            return "Necunoscut"
        if expiration.tzinfo is None:
            expiration = expiration.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
        return "Da" if expiration > dt_util.now() else "Nu"

    @property
    def extra_state_attributes(self) -> dict:
        """Atribute suplimentare ale vehiculului și rovinietei."""
        # if not self._license_valid:
        #     return {"licență": "necesară"}
        vehicle = self._get_vehicle_data()
        attrs = {
            "plateNumber": vehicle.get("plateNumber"),
            "expirationDate": vehicle.get("expirationDateCurrentVignette"),
            "vehicleType": vehicle.get("vehicleType"),
            "country": vehicle.get("country"),
            "category": vehicle.get("category"),
            "emissionStandard": vehicle.get("emissionStandard"),
            "mtma": vehicle.get("mtma"),
            "isValid": vehicle.get("isValid"),
        }
        return {key: value for key, value in attrs.items() if value is not None}


# =====================================================================
#  PlataTreceriPodSensor — restanțe
# =====================================================================


class PlataTreceriPodSensor(EtollBaseSensor):
    """Senzor pentru restanțe treceri pod (neplătite în ultimele 24h).

    Filtrarea se face per vehicul (vin + plate_no).
    """

    def __init__(
        self,
        coordinator: EtollCoordinator,
        config_entry: ConfigEntry,
        plate_no: str,
    ) -> None:
        """Inițializare."""
        sanitized = sanitize_plate_no(plate_no)
        super().__init__(
            coordinator=coordinator,
            config_entry=config_entry,
            name=f"Restanțe treceri pod ({plate_no})",
            unique_id=f"{DOMAIN}_plata_treceri_pod_{sanitized}_{config_entry.entry_id}",
            icon="mdi:invoice-text-remove",
        )
        self._plate_no = plate_no

    @property
    def native_value(self) -> str:
        """Unpaid bridge detections are not exposed by the confirmed eToll API."""
        return "Unknown"

    @property
    def extra_state_attributes(self) -> dict:
        """Explain why the unpaid state cannot currently be determined."""
        return {
            "Număr de înmatriculare": self._plate_no,
            "reason": "eToll does not expose a confirmed unpaid bridge detection list",
        }


# =====================================================================
#  TreceriPodSensor — istoric
# =====================================================================


class TreceriPodSensor(EtollBaseSensor):
    """Senzor pentru istoricul complet al trecerilor de pod."""

    def __init__(
        self,
        coordinator: EtollCoordinator,
        config_entry: ConfigEntry,
        plate_no: str,
    ) -> None:
        """Inițializare."""
        sanitized = sanitize_plate_no(plate_no)
        super().__init__(
            coordinator=coordinator,
            config_entry=config_entry,
            name=f"Treceri pod ({plate_no})",
            unique_id=f"{DOMAIN}_treceri_pod_{sanitized}_{config_entry.entry_id}",
            icon="mdi:bridge",
        )
        self._plate_no = plate_no

    def _get_bridge_crossings(self) -> list | None:
        """Return crossings from verified bridge pass records, if available."""
        data = self.coordinator.data or {}
        result = data.get("bridge_verification_by_vehicle", {}).get(self._plate_no)
        section = result.get("bridge") if isinstance(result, dict) else None
        if not isinstance(section, dict) or section.get("status") != "OK":
            return None
        items = section.get("items")
        if not isinstance(items, list) or not items:
            return None
        crossings = []
        for item in items:
            if isinstance(item, dict):
                crossings.extend(
                    crossing for crossing in item.get("crossings", [])
                    if isinstance(crossing, dict)
                )
        return crossings

    @property
    def native_value(self) -> int | str:
        """Number of verified bridge crossings, or Unknown if none are reported."""
        crossings = self._get_bridge_crossings()
        return len(crossings) if crossings else "Unknown"

    @property
    def extra_state_attributes(self) -> dict:
        """Expose dates and directions returned by bridge verification."""
        crossings = self._get_bridge_crossings()
        if not crossings:
            return {"Număr de înmatriculare": self._plate_no}
        limited = crossings[:MAX_ATTR_TRECERI]
        attrs = {
            "Număr de înmatriculare": self._plate_no,
            "Număr total treceri": len(crossings),
            "Treceri afișate": len(limited),
        }
        for idx, crossing in enumerate(limited, start=1):
            attrs[f"Trecere {idx} - Dată"] = crossing.get("crossingTime")
            attrs[f"Trecere {idx} - Direcție"] = crossing.get("direction")
        return attrs


# =====================================================================
#  SoldSensor
# =====================================================================


class SoldSensor(EtollBaseSensor):
    """Senzor pentru soldul peajelor neexpirate."""

    def __init__(
        self,
        coordinator: EtollCoordinator,
        config_entry: ConfigEntry,
        plate_no: str,
    ) -> None:
        """Inițializare."""
        sanitized = sanitize_plate_no(plate_no)
        super().__init__(
            coordinator=coordinator,
            config_entry=config_entry,
            name=f"Sold peaje neexpirate ({plate_no})",
            unique_id=f"{DOMAIN}_sold_peaje_neexpirate_{sanitized}_{config_entry.entry_id}",
            icon="mdi:boom-gate",
        )
        self._plate_no = plate_no

    def _get_sold(self) -> int | float | None:
        """Return remaining bridge crossings, or None when no balance exists."""
        data = self.coordinator.data or {}
        services = data.get("bridge_services_by_vehicle", {}).get(self._plate_no, [])
        balances = [
            service.get("peajBalance", {}).get("remainingCrossingsCount")
            for service in services
            if isinstance(service.get("peajBalance"), dict)
            and service["peajBalance"].get("remainingCrossingsCount") is not None
        ]
        if not balances:
            result = data.get("bridge_verification_by_vehicle", {}).get(self._plate_no)
            section = result.get("bridge") if isinstance(result, dict) else None
            items = section.get("items") if isinstance(section, dict) else None
            if isinstance(items, list):
                balances = [
                    item["remainingBalance"]
                    for item in items
                    if isinstance(item, dict) and item.get("remainingBalance") is not None
                ]
        return sum(balances) if balances else None

    @property
    def native_value(self) -> int | float | str:
        """Return the remaining balance or Unknown when no toll data exists."""
        sold = self._get_sold()
        return sold if sold is not None else "Unknown"

    @property
    def extra_state_attributes(self) -> dict:
        """Additional balance details."""
        sold = self._get_sold()
        attrs = {"Număr de înmatriculare": self._plate_no}
        if sold is not None:
            attrs["Treceri rămase"] = sold
        else:
            attrs["reason"] = "No bridge toll balance is available"
        return attrs


# =====================================================================
#  RaportTranzactiiSensor
# =====================================================================


class RaportTranzactiiSensor(EtollBaseSensor):
    """Senzor sumar pentru raportul de tranzacții."""

    def __init__(
        self, coordinator: EtollCoordinator, config_entry: ConfigEntry
    ) -> None:
        """Inițializare."""
        super().__init__(
            coordinator=coordinator,
            config_entry=config_entry,
            name="Raport tranzacții",
            unique_id=f"{DOMAIN}_raport_tranzactii_account_{config_entry.entry_id}",
            icon="mdi:chart-bar-stacked",
        )

    @property
    def native_value(self) -> int | str:
        """Number of invoices, or Unknown when there are none."""
        invoices = (self.coordinator.data or {}).get("invoices", [])
        return len(invoices) if invoices else "Unknown"

    @property
    def extra_state_attributes(self) -> dict:
        """Invoice count and total paid amount."""
        invoices = (self.coordinator.data or {}).get("invoices", [])
        if not invoices:
            return {"reason": "No invoices are available"}
        total_sum = sum(
            float((item.get("total") or {}).get("totalPrice") or 0)
            for item in invoices
            if isinstance(item, dict)
        )
        return {
            "Număr facturi": len(invoices),
            "Suma totală plătită": f"{total_sum:.2f} RON",
        }
