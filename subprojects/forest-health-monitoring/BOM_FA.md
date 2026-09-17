# BOM پیشنهادی سنسورها — v0.2.0

**وضعیت:** baseline مهندسی/تحقیقاتی است و هنوز سفارش خرید نیست.  
**قیمت‌ها:** snapshot تاریخ 2026-09-17 و عموماً بدون VAT.

## ۱. اصل انتخاب

قطعاتی انتخاب شده‌اند که:

- به فیزیولوژی spruce و حمله bark beetle مرتبط باشند؛
- بتوانند دائم در جنگل کار کنند؛
- داده کم‌حجم و مناسب Edge/LoRa تولید کنند؛
- برای 15–18 درخت از نظر هزینه قابل مقیاس باشند؛
- با نود اصلی Forest Internet قابل اتصال باشند؛
- raw data را برای ML نگه دارند.

## ۲. سنسورهای هر درخت

### BME688 — e-nose / VOC proxy

انتخاب اصلی Bosch BME688 است.

- gas resistance + temperature + RH + pressure؛
- I2C/SPI؛
- تغذیه 1.71–3.6 V؛
- در کارهای نزدیک به *Ips typographus* استفاده شده؛
- Bosch ابزار BME AI-Studio/BSEC/SensorAPI دارد؛
- خود IC در تعداد کم حدود 6–8 یورو است؛
- breakout برای prototype حدود 17–20 یورو.

باید raw gas resistance و heater-profile data ذخیره شود؛ IAQ/eCO2 به‌تنهایی کافی نیست.

BME688 نباید داخل enclosure کاملاً sealed قرار گیرد. باید نزدیک bark و داخل یک rain/radiation shield تهویه‌دار نصب شود.

### Dendrometer

برای scale کردن، مسیر پیشنهادی:

**TT Electronics/BI Model 404 precision linear potentiometer** + bracket فلزی اختصاصی.

- travel حدود 12.7 mm؛
- linearity حدود ±1%؛
- قیمت حدود 21 یورو در تعداد 10؛
- در یک سیستم open-source کم‌هزینه 2026 از همین خانواده استفاده شده است.

برای خواندن آن:

**ADS1115 16-bit ADC**

- I2C؛
- 2–5.5 V؛
- low-power؛
- حدود 5 یورو در تعداد 10.

Excitation فقط هنگام measurement روشن شود و پردازش ratio-metric `Vout/Vex` انجام شود.

### مرجع تجاری

دو عدد **Ecomatik DR1** پیشنهاد می‌شود.

- research-grade؛
- range 11 mm؛
- analog 0–Vex؛
- قیمت حدود 335 یورو/عدد.

هدف این است که طراحی ارزان خودمان را روی 1–2 درخت در کنار یک مرجع تجاری cross-check کنیم؛ خرید 18 عدد DR1 در این مرحله توصیه نمی‌شود.

## ۳. دمای bark

**DS18B20 waterproof** به‌صورت optional.

- 1-Wire؛
- 3–5.5 V؛
- حدود 2.5–3.5 یورو در لیتوانی.

به علت هزینه کم ارزش تست دارد، ولی signal اصلی پروژه نیست.

## ۴. Soil moisture در سطح plot

انتخاب پیشنهادی **METER TEROS 10** است.

- VWC research-grade؛
- 70 MHz؛
- analog 1–2.5 V؛
- excitation 3–15 V؛
- قیمت اروپایی پیدا شده حدود 218–255 یورو.

پیشنهاد پایه: **3 عدد در هر plot**، نه یک عدد برای هر درخت.

هدف اصلی soil moisture این است که drought را از stress مرتبط با pest بهتر جدا کنیم.

## ۵. Ambient reference

برای هر plot یک یا دو BME688 مرجع در محل استاندارد و سایه‌دار.

کاربرد:

- baseline محیطی؛
- featureهایی مثل `tree - ambient`؛
- جلوگیری از اینکه ML صرفاً microclimate را یاد بگیرد.

برای prototype می‌توان breakout حدود 17 یورویی استفاده کرد؛ در field بهتر است همان custom sensor-head PCB استفاده شود.

## ۶. Pheromone trap

Trap و lure برای pressure کلی *Ips* در plot استفاده می‌شوند، نه label هر درخت.

قیمت نمونه در لیتوانی:

- trap IBL3 حدود 19.36 یورو؛
- lure فصلی حدود 11–12.4 یورو.

تعداد و محل نصب باید توسط bark-beetle specialist مشخص شود.

## ۷. Sap flow

فقط روی حدود 3–4 reference tree و در صورت بودجه.

کلاس پیشنهادی:

- ICT International SFM1/SFMx یا مشابه.

فعلاً داخل هزینه پایه نیست چون قیمت quotation-based، نصب تخصصی و هزینه آن زیاد است.

## ۸. Host electronics

### نود نهایی

ترجیح اصلی همان Forest Internet universal MCU/LoRa node تیم IoT است.

Interface موردنیاز ما:

- I2C برای BME688 و ADS1115؛
- switched regulated excitation برای dendrometer؛
- optional 1-Wire؛
- analog/ADC برای TEROS 10 روی plot node؛
- local storage؛
- timestamp؛
- LoRaWAN summary/alert.

### PoC

Nordic Thingy:91 X برای bench/PoC مفید است:

- nRF9151 Cortex-M33؛
- 1 MB Flash / 256 KB RAM؛
- LTE-M/NB-IoT/GNSS؛
- Qwiic/STEMMA/Grove؛
- باتری 1350 mAh؛
- حدود 88 یورو.

ولی LoRaWAN ندارد، بنابراین نود نهایی پروژه نیست.

## ۹. چیزهایی که هنوز core نیستند

- CO2 محیطی برای هر درخت؛
- photosynthesis instrument؛
- camera/UAV/hyperspectral؛
- continuous electronic resin sensing؛
- sap-flow برای همه درخت‌ها؛
- soil sensorهای hobby به‌عنوان ground truth علمی.
