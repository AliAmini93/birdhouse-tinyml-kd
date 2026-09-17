# پروتوتایپ بنچ یک درخت — v0.2.1

هدف این مرحله **اثبات تشخیص Ips نیست**. هدف این است که قبل از خرید برای 15–18 درخت مطمئن شویم زنجیره سنسور، مکانیک، logging و calibration واقعاً قابل اعتماد است.

## سخت‌افزار حداقلی

- 2 × BME688؛
- 1 × TT/BI Model 404، 10 kΩ، travel حدود 12.7 mm؛
- 1 × ADS1115 16-bit؛
- 1 × DS18B20 waterproof به‌صورت optional؛
- یک MCU/dev board موجود با 3.3 V و I2C؛
- bracket آلومینیومی/استیل برای dendrometer؛
- micrometer یا displacement stage برای calibration؛
- کابل، breadboard و supply پایدار.

دو BME688 عمداً استفاده می‌شوند تا علاوه بر tree/ambient concept، اختلاف baseline بین دو سنسور را هم از همین مرحله اندازه بگیریم.

## انتخاب host

اولویت:

1. اگر prototype پایدار universal board پروژه آماده است، همان؛
2. اگر نیست و Thingy:91 X در دسترس است، همان؛
3. در غیر این صورت هر dev board موجود 3.3 V با I2C.

برای bench فقط به خاطر host برد جدید نخریم.

نکته Thingy:91 X:
- سنسور onboard آن طبق مستندات Nordic، **BME680** است نه BME688؛
- BME680 آدرس `0x76` دارد؛
- بنابراین BME688 خارجی همچنان لازم است؛
- برای جلوگیری از conflict، BME688 خارجی روی `0x77` یا bus/mux جدا استفاده شود.

## wiring

```text
Host MCU / 3.3 V
   |
   +--- I2C ---> BME688 #1
   |
   +--- I2C ---> BME688 #2 / mux or second bus
   |
   +--- I2C ---> ADS1115
                   |
                   +--- A0 = dendrometer wiper
                   +--- A1 = excitation measurement
   |
   +--- optional 1-Wire ---> DS18B20
```

در Model 404 باید raw ADC و excitation هر دو ذخیره شوند و نسبت:

`V_wiper / V_excitation`

نیز محاسبه شود.

## گیت‌های تست

### Gate A
60 دقیقه logging پیوسته:
- communication؛
- timestamp؛
- raw BME688؛
- raw ADC.

هدف: حداقل 99.9% record ساختاری درست و بدون reset.

### Gate B
24 ساعت تست پایدار indoor.

هدف:
- timestamp برنگردد؛
- I2C hang حل‌نشده نداشته باشیم؛
- حداقل 99.5% recordهای مورد انتظار حاضر باشند.

### Gate C
Calibration dendrometer طبق فایل مربوطه.

### Gate D
Characterization BME688 طبق فایل مربوطه.

### Gate E
48–72 ساعت outdoor dry run بدون نتیجه‌گیری زیستی.

بررسی:
- باران/condensation؛
- thermal drift؛
- cable movement؛
- mechanical creep؛
- brownout؛
- clock/logging؛
- نحوه محافظت BME688.

## شرط خروج

فقط اگر logging پایدار، dendrometer قابل calibration، raw data قابل trace، و outdoor dry run موفق بود به pilot دو تا سه درخت می‌رویم.

هر failure باید قبل از scale-up به‌عنوان revision در v0.2.x ثبت شود.
