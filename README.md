# eToll for Home Assistant

Custom integration for Home Assistant that reads vehicle vignette data and available bridge toll and invoice data from the eToll portal (`portal.etoll.ro`). The integration domain and component directory are both `etoll`.

[![GitHub Release](https://img.shields.io/github/v/release/vladurash/etollro_ha)](https://github.com/vladurash/etollro_ha/releases)
[![GitHub Stars](https://img.shields.io/github/stars/vladurash/etollro_ha?style=flat&logo=github)](https://github.com/vladurash/etollro_ha/stargazers)

## Sensors

The integration creates one account sensor and one set of vehicle sensors for each registered car.

| Sensor | What it reports |
| --- | --- |
| **Date utilizator** | `Conectat` when the configured account is available; includes the configured username. |
| **Rovinietă activă (plate)** | `Da` while the vehicle’s current vignette expiration date is in the future, `Nu` when expired, and `Necunoscut` when no expiration date is available. Includes vehicle details such as plate, expiration date, category, and validity fields when provided. |
| **Restanțe treceri pod (plate)** | Legacy sensor. It is `Unknown` and disabled because the integration has no confirmed eToll API route for unpaid bridge detections. |
| **Treceri pod (plate)** | Legacy sensor. It reports verified crossings when returned; when the value is `Unknown`, Home Assistant disables it while retaining its registry entry. |
| **Sold peaje neexpirate (plate)** | Legacy sensor. It reports a remaining crossing balance when returned; when the value is `Unknown`, Home Assistant disables it while retaining its registry entry. |
| **Raport tranzacții** | Invoice count and total when invoices are returned; otherwise `Unknown`. |

`Unknown` is expected when the account has no matching toll or invoice data. On integration setup or reload, legacy toll sensors with an `Unknown` value are disabled in the entity registry, but their IDs are retained for compatibility. An empty `/api/tolls` response does not establish whether unpaid crossings exist. Optional toll and invoice requests can fail without stopping vehicle and vignette updates; those failures are written to the Home Assistant log.

## Install

### HACS

Add [vladurash/etollro_ha](https://github.com/vladurash/etollro_ha) as a custom HACS integration repository, install **eToll**, then restart Home Assistant.

### Manual

Copy `etoll/` into `custom_components/etoll/` in your Home Assistant configuration directory, then restart Home Assistant.

After restart, go to **Settings → Devices & services → Add integration**, search for **eToll**, and enter your eToll username and password. The integration authenticates with the eToll identity service and refreshes its data every 24 hours by default.

You can change the refresh interval under **Settings → Devices & services → eToll → Configure**. The allowed interval is 300 to 86,400 seconds.

## Updating from the previous integration domain

This release uses the new Home Assistant domain `etoll` and the directory `custom_components/etoll`. Home Assistant treats it as a different integration from the previous `etoll` domain. Existing config entries and entity registry IDs are not migrated automatically. Remove the old integration entry, install the `etoll` component, and add **eToll** again. Review automations and dashboards for entity IDs that may need updating to the `sensor.etoll_*` prefix.

## Troubleshooting

- Check that the username and password are accepted by the eToll portal. Authentication failures are reported in the integration logs.
- An authentication error for the optional profile route does not necessarily prevent vehicle updates; the account sensor uses the configured username and does not depend on that route.
- If bridge or invoice data is absent, the corresponding sensors may show `Unknown`. Check the Home Assistant log for warnings about optional endpoints.
- To enable detailed logs, add the following to `configuration.yaml` and restart Home Assistant:

  ```yaml
  logger:
    default: info
    logs:
      custom_components.etoll: debug
  ```

## Development and support

Issues and contributions: [github.com/vladurash/etollro_ha](https://github.com/vladurash/etollro_ha).
