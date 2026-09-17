# معماری نود — v0.2.0

## ۱. تقسیم فیزیکی پیشنهادی

### Sensor head روی درخت

- BME688 داخل shield تهویه‌دار و محافظ باران/تابش؛
- مکانیزم dendrometer؛
- TT Model 404؛
- ADS1115؛
- DS18B20 optional؛
- کابل کوتاه؛
- شناسه و calibration metadata.

### Forest Internet host node

داخل enclosure ضدآب نزدیک درخت:

- MCU اصلی پروژه؛
- local storage؛
- time synchronization؛
- LoRaWAN تحت مسئولیت تیم IoT؛
- cellular fallback در صورت وجود؛
- sensor power rails؛
- battery/power subsystem.

BME688 نباید داخل enclosure sealed اصلی قرار گیرد.

## ۲. Interface

```text
BME688 ---------------- I2C --------\
                                     \
TT Model 404 -> ADS1115 -- I2C -------> Forest Internet MCU
                                      /
DS18B20 optional -------- 1-Wire ----/
```

در plot node:

```text
TEROS 10 -> switched excitation -> analog -> ADC
ambient BME688 -------------------------> I2C
```

## ۳. Dendrometer

مقاومت خطی دائماً powered نباشد.

هر 5 دقیقه:

1. excitation روشن؛
2. حدود 100 ms صبر؛
3. Vex و Vout خوانده شود؛
4. `Vout/Vex` محاسبه شود؛
5. raw ADC و displacement ذخیره شود؛
6. excitation خاموش شود.

ADS1115 از نظر resolution کافی است، اما accuracy واقعی را mechanics، thermal drift، mounting، cable noise و calibration تعیین می‌کنند.

## ۴. کابل

I2C باید کوتاه بماند.

ترجیح: host node نزدیک sensor head همان درخت نصب شود.

اگر بعداً یک box بخواهد چند درخت را بخواند، I2C چندمتری توصیه نمی‌شود؛ در آن صورت local acquisition + RS-485/SDI-12 بهتر است.

## ۵. Communication

Raw data روی local storage بماند.

LoRa فقط:

- summary؛
- feature؛
- diagnostics؛
- anomaly/risk score؛
- alert.

ارسال hourly summary کافی است و alert در صورت anomaly پایدار فوراً ارسال می‌شود.

## ۶. مراحل prototype

**Phase 1:** یک نود bench با Thingy:91 X یا dev board موجود + BME688 + ADS1115 + Model 404.

**Phase 2:** تست outdoor روی 2–3 درخت و قرار دادن حداقل یک Ecomatik DR1 در کنار طراحی خودمان.

**Phase 3:** scale به 15–18 درخت با نود LoRa اصلی Forest Internet.

## ۷. مرز مسئولیت

Forest-health:
- انتخاب و calibration سنسور؛
- acquisition requirement؛
- preprocessing/AI؛
- schema/QC.

IoT team:
- MCU/PCB نهایی؛
- LoRa/cellular؛
- RF/antenna؛
- gateway/network؛
- power hardware نهایی؛
- production enclosure.

Shared:
- interface؛
- timing؛
- payload؛
- power measurement؛
- system validation.
