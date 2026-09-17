# Data Schema — Forest Health Monitoring

**Version:** v0.1.0-draft

The dataset is designed so biological labels, sensor identity, maintenance events, environmental context, and tree metadata remain traceable. Raw time series must never be stored without the metadata required to interpret them.

## 1. `tree_metadata`

One row per tree.

| Field | Type | Required | Description |
|---|---|---:|---|
| tree_id | string | yes | Stable unique ID |
| plot_id | string | yes | Plot/site ID |
| species | string | yes | Expected `Picea_abies` for core study |
| latitude | float | yes | Coordinate |
| longitude | float | yes | Coordinate |
| dbh_cm | float | yes | Initial DBH |
| height_m | float | desirable | Tree height |
| age_class | string/int | desirable | Forestry age class |
| stand_density | float/string | desirable | Density/basal-area descriptor |
| spruce_fraction | float | desirable | Spruce proportion in stand |
| site_type | string | desirable | Forestry site type |
| soil_type | string | desirable | Soil descriptor |
| distance_edge_m | float | desirable | Distance to stand edge |
| distance_windthrow_m | float | desirable | Distance to recent windthrow |
| initial_defoliation_pct | float | yes | Initial crown condition |
| initial_health | string | yes | Baseline forestry status |
| install_date | date | yes | Instrumentation date |

## 2. `sensor_registry`

One row per physical sensor instance.

Required fields:

- sensor_id;
- node_id;
- tree_id or plot_id;
- sensor_type;
- manufacturer;
- model;
- serial_number;
- mount_height_cm;
- orientation;
- install_timestamp;
- calibration_date;
- firmware_version;
- sampling_interval_s;
- notes.

## 3. `sensor_readings`

Long-form time series.

Core fields:

- timestamp_utc;
- tree_id;
- node_id;
- sensor_id;
- gas_resistance_ohm;
- gas_heater_step;
- gas_heater_temp_c;
- air_temp_c;
- relative_humidity_pct;
- pressure_hpa;
- stem_circumference_mm and/or stem_radius_um;
- soil_moisture_pct (if local);
- sap_flow_value + unit (if present);
- battery_v;
- rssi_dbm;
- qc_flag.

Store raw BME688-class gas measurements, not only a proprietary/processed IAQ score.

## 4. `weather`

- timestamp_utc;
- source_id;
- air_temp_c;
- relative_humidity_pct;
- precipitation_mm;
- wind_speed_ms;
- wind_direction_deg;
- solar_radiation_wm2 (when available).

## 5. `tree_inspections`

This is the primary biological-label table.

- inspection_id;
- tree_id;
- timestamp_utc;
- observer;
- health_status_code;
- fresh_attack_confirmed;
- entrance_holes;
- boring_dust;
- resin_score;
- gallery_evidence;
- adult_larval_evidence;
- defoliation_pct;
- crown_status;
- estimated_attack_onset;
- label_confidence;
- photo_reference;
- notes.

## 6. `pheromone_traps`

- trap_id;
- plot_id;
- inspection_date;
- period_start;
- period_end;
- beetle_count;
- lure_type;
- trap_latitude;
- trap_longitude;
- distance_to_nearest_monitored_tree_m;
- notes.

## 7. `maintenance_log`

- timestamp_utc;
- node_id;
- sensor_id;
- action_type;
- battery_changed;
- sensor_replaced;
- sensor_cleaned;
- recalibrated;
- firmware_changed;
- old_firmware_version;
- new_firmware_version;
- problem_description;
- action_description;
- technician;
- notes.

## 8. QC principles

- Never silently overwrite raw data.
- Preserve sensor/node IDs after replacement by assigning the replacement a new sensor ID.
- Keep timestamps in UTC in stored data; convert only for visualization.
- Flag missing/invalid/calibration/maintenance periods explicitly.
- Keep units explicit and stable.
- Version all schema changes.
