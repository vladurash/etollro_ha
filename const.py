"""Constants for the eToll integration."""

from typing import Final

DOMAIN = "etoll"
VERSION = "1.0.0"
ATTRIBUTION = "Date furnizate de portal.etoll.ro"

# eToll portal and Keycloak
ETOLL_BASE_URL: Final = "https://portal.etoll.ro"
KEYCLOAK_TOKEN_URL: Final = (
    "https://sso.etoll.ro/auth/realms/external/"
    "protocol/openid-connect/token"
)
KEYCLOAK_CLIENT_ID: Final = "ddcm-authz-client"
VEHICLES_PAGE_SIZE: Final = 50

# Chei de configurare
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_UPDATE_INTERVAL = "update_interval"
CONF_ISTORIC_TRANZACTII = "istoric_tranzactii"

# Valori implicite
DEFAULT_UPDATE_INTERVAL = 86400  # 24 ore (secunde)
MIN_UPDATE_INTERVAL = 300  # 5 minute (secunde)
MAX_UPDATE_INTERVAL = 86400  # 1 zi (secunde)
ISTORIC_TRANZACTII_DEFAULT = 2  # ani

# Limită atribute de stare (previne > 16384 bytes recorder)
MAX_ATTR_TRECERI = 20

# Platforme suportate
PLATFORMS: list[str] = ["sensor"]
