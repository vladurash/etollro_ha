# eToll for Home Assistant

Custom integration for Home Assistant that reads vehicle vignette data and available bridge toll and invoice data from the eToll portal (`portal.etoll.ro`). The integration domain and component directory are both `etoll`. Current release: **1.0.0**.

[![GitHub Release](https://img.shields.io/github/v/release/vladurash/etoll)](https://github.com/vladurash/etoll/releases)
[![GitHub Stars](https://img.shields.io/github/stars/vladurash/etoll?style=flat&logo=github)](https://github.com/vladurash/etoll/stargazers)

## Sensors

The integration creates one account sensor and one set of vehicle sensors for each registered car.

| Sensor | What it reports |
| --- | --- |
| **Date utilizator** | `Conectat` when the configured account is available; includes the configured username. |
| **Rovinietă activă (plate)** | `Da` while the vehicle’s current vignette expiration date is in the future, `Nu` when expired, and `Necunoscut` when no expiration date is available. Includes vehicle details such as plate, expiration date, category, and validity fields when provided. |
| **Restanțe treceri pod (plate)** | `Unknown` because the integration has not confirmed an eToll API route that identifies unpaid bridge detections. |
| **Treceri pod (plate)** | Count and limited date/direction attributes when bridge verification returns crossings; otherwise `Unknown`. |
| **Sold peaje neexpirate (plate)** | Remaining crossing balance when the portal returns one; otherwise `Unknown`. |
| **Raport tranzacții** | Invoice count and total when invoices are returned; otherwise `Unknown`. |

`Unknown` is expected when the account has no matching toll or invoice data. For example, an empty `/api/tolls` response does not mean that there are zero unpaid crossings: unpaid bridge detection is not currently available from a confirmed endpoint. Optional toll and invoice requests can fail without stopping vehicle and vignette updates; those failures are written to the Home Assistant log.

## Install

### HACS

Add [vladurash/etoll](https://github.com/vladurash/etoll) as a custom HACS integration repository, install **eToll**, then restart Home Assistant.

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

Issues and contributions: [github.com/vladurash/etoll](https://github.com/vladurash/etoll).
