# Calibration و پذیرش Dendrometer — v0.2.1

Model 404 حدود 12.7 mm travel و linearity اسمی ±1% دارد، ولی دقت نهایی سیستم را فقط خود سنسور تعیین نمی‌کند. bracket، preload، thermal expansion، ADC، کابل و creep نیز مهم‌اند.

بنابراین **کل assembly** باید calibration شود.

## Fixture

- micrometer head یا translation stage دقیق؛
- bracket فلزی شبیه طراحی field؛
- ADS1115 و excitation واقعی؛
- ابتدا دمای اتاق ثابت.

برای bracket فلز ترجیح دارد؛ کارهای open-source جدید نشان داده‌اند ساختارهای پلیمری/3D-printed نسبت به آلومینیوم thermal dimensional change بیشتری دارند.

## sequence

پیشنهاد:

- 0 تا 10 mm با step برابر 0.5 mm؛
- در هر نقطه 3–5 ثانیه صبر؛
- حداقل 50 ADC sample؛
- مسیر بالا؛
- مسیر پایین؛
- حداقل 5 cycle کامل.

ثبت شود:

- reference displacement؛
- raw ADC wiper؛
- raw excitation؛
- ratio؛
- direction؛
- cycle؛
- temperature.

## مدل اولیه

`x_mm = a * (Vwiper / Vexc) + b`

مدل nonlinear فقط وقتی استفاده شود که residualها یک nonlinearity واقعی و تکرارشونده نشان دهند.

## targetهای مهندسی

این اعداد **target پروژه** هستند، نه specification سازنده:

- پاسخ کاملاً monotonic؛
- بدون mechanical binding؛
- repeated-position SD هدف <= 0.010 mm؛
- maximum calibrated residual هدف <= 0.050 mm؛
- hysteresis هدف <= 0.050 mm.

اگر fail شد، با smoothing پنهانش نمی‌کنیم؛ علت باید پیدا شود.

## thermal characterization

اگر chamber یا setup کنترل دما داریم:

- 10 °C؛
- 20 °C؛
- 30 °C.

در displacement ثابت drift را اندازه بگیریم و `µm/°C` گزارش کنیم.

فعلاً compensation model نمی‌سازیم تا data واقعی تکرارشونده داشته باشیم.

## نصب field

sensor نزدیک middle of travel نصب شود و preload/initial position ثبت شود.

raw calibration هیچ‌وقت overwrite نشود.
