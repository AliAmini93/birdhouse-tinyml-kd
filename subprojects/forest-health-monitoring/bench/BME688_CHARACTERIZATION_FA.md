# Characterization سنسور BME688 — v0.2.1

هدف این مرحله validation سخت‌افزار و data integrity است، نه تشخیص bark beetle.

## Stabilization اولیه

طبق مستندات Bosch، BME board نو باید حداقل **24 ساعت** روشن بماند تا قبل از measurement معنی‌دار stabilize شود.

پس:
- هر دو BME688 حداقل 24 ساعت با config یکسان کار کنند؛
- این بازه با flag `stabilization` ذخیره شود؛
- وارد biological training data نشود.

## Heater profile

BME688 به heater profile و duty cycle حساس است.

در ابتدا:
- فقط یک config ثابت؛
- heater step/config در metadata؛
- تغییر profile وسط dataset بدون version event ممنوع.

اگر Bosch Development Kit/AI-Studio داریم:
- از default `HP-354 / RDC-5-10` شروع شود.

اگر breakout معمولی داریم:
- Bosch BME68x SensorAPI یا driver معتبر؛
- تمام heater settings ثبت شوند.

## تست دو سنسور کنار هم

بعد از stabilization، دو سنسور حداقل 12 ساعت side-by-side کار کنند.

ذخیره:

- gas resistance؛
- T؛
- RH؛
- pressure؛
- heater metadata؛
- sensor ID؛
- timestamp.

بررسی:

- baseline offset؛
- log-gas offset؛
- correlation؛
- T/RH difference؛
- drift.

انتظار نداریم absolute gas resistance دو سنسور دقیقاً برابر باشد.

## challenge ساده

اختیاری و فقط برای engineering:

هر دو سنسور در معرض یک headspace یکسان و بی‌خطر، ترجیحاً مرتبط با جنگل مثل spruce needle/resin material قرار بگیرند و recovery در هوای عادی ثبت شود.

هدف فقط دیدن response و صحت logging است؛ این data نباید به‌عنوان Ips dataset استفاده شود.

## تست outdoor

BME688 باید هوا بگیرد ولی از rain، liquid water، debris و direct solar heating محافظت شود.

sensor head پیشنهادی 48–72 ساعت outdoor dry run شود.

## acceptance

بعد از stabilization:

- حداقل 99.5% record معتبر در 24 ساعت؛
- هیچ تغییر unexplained در heater config؛
- I2C hang حل‌نشده نداشته باشیم؛
- sensor ID/config برای هر record قابل trace باشد؛
- shield باعث condensation پایدار یا thermal trapping واضح نشود.
