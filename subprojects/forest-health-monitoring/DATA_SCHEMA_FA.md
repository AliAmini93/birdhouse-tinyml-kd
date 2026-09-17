# ساختار داده — پایش سلامت جنگل

**نسخه:** v0.1.0-draft

این schema طوری طراحی شده که label زیستی، هویت سنسور، تعمیرات، context محیطی و metadata هر درخت قابل رهگیری بماند. raw time series نباید بدون اطلاعات لازم برای تفسیر ذخیره شود.

## ۱. `tree_metadata`

برای هر درخت یک ردیف:

- `tree_id` شناسه پایدار و یکتا؛
- `plot_id` شناسه محل؛
- `species` (در مطالعه اصلی `Picea_abies`)؛
- latitude / longitude؛
- `dbh_cm`؛
- `height_m`؛
- `age_class`؛
- `stand_density` یا basal-area descriptor؛
- `spruce_fraction`؛
- `site_type`؛
- `soil_type`؛
- `distance_edge_m`؛
- `distance_windthrow_m`؛
- `initial_defoliation_pct`؛
- `initial_health`؛
- `install_date`.

## ۲. `sensor_registry`

برای هر سنسور فیزیکی یک ردیف:

- `sensor_id`؛
- `node_id`؛
- `tree_id` یا `plot_id`؛
- `sensor_type`؛
- manufacturer/model/serial؛
- ارتفاع نصب؛
- orientation؛
- زمان نصب؛
- calibration date؛
- firmware version؛
- sampling interval؛
- notes.

## ۳. `sensor_readings`

Time series اصلی:

- `timestamp_utc`؛
- `tree_id`؛
- `node_id`؛
- `sensor_id`؛
- `gas_resistance_ohm`؛
- heater step/temperature در صورت استفاده؛
- `air_temp_c`؛
- `relative_humidity_pct`؛
- `pressure_hpa`؛
- `stem_circumference_mm` و/یا `stem_radius_um`؛
- `soil_moisture_pct`؛
- sap-flow value + unit در صورت وجود؛
- `battery_v`؛
- `rssi_dbm`؛
- `qc_flag`.

برای BME688-class فقط IAQ score پردازش‌شده ذخیره نشود؛ **raw gas measurement** باید نگهداری شود.

## ۴. `weather`

- timestamp؛
- source؛
- temperature؛
- RH؛
- precipitation؛
- wind speed/direction؛
- solar radiation در صورت دسترسی.

## ۵. `tree_inspections`

این جدول منبع اصلی biological label است:

- `inspection_id`؛
- `tree_id`؛
- timestamp؛
- observer؛
- `health_status_code`؛
- `fresh_attack_confirmed`؛
- entrance holes؛
- boring dust؛
- resin score؛
- gallery evidence؛
- adult/larval evidence؛
- defoliation؛
- crown status؛
- estimated attack onset؛
- label confidence؛
- photo reference؛
- notes.

## ۶. `pheromone_traps`

- trap ID؛
- plot ID؛
- inspection date؛
- period start/end؛
- beetle count؛
- lure type؛
- مختصات؛
- فاصله تا نزدیک‌ترین درخت instrumented؛
- notes.

## ۷. `maintenance_log`

- timestamp؛
- node/sensor ID؛
- نوع اقدام؛
- battery changed؛
- sensor replaced/cleaned/recalibrated؛
- firmware changed؛
- old/new firmware version؛
- problem؛
- action؛
- technician؛
- notes.

## ۸. اصول QC

- raw data هیچ‌وقت silently overwrite نشود.
- سنسور جایگزین ID جدید بگیرد.
- داده ذخیره‌شده UTC باشد؛ تبدیل timezone فقط برای نمایش.
- missing/invalid/calibration/maintenance periods flag شوند.
- واحدها explicit و ثابت بمانند.
- هر تغییر schema نسخه‌بندی شود.
