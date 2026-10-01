"""Excepții personalizate pentru integrarea eToll."""

from homeassistant.exceptions import HomeAssistantError


class EtollError(HomeAssistantError):
    """Excepție de bază pentru integrarea eToll."""


class EtollAuthError(EtollError):
    """Eroare de autentificare (credentiale invalide sau token expirat)."""


class EtollConnectionError(EtollError):
    """Eroare de conexiune la API-ul eToll."""


class EtollApiError(EtollError):
    """Eroare generală la apelul API-ului eToll."""
