# پروتکل آزمایش — پایش سلامت جنگل

**نسخه:** v0.1.0-draft  
**پروژه مادر:** Forest Internet / Birdhouse  
**اکوسیستم هدف:** توده‌های صنوبر نروژی در لیتوانی  
**گونه هدف:** *Picea abies*  
**تهدید اصلی:** *Ips typographus*

## ۱. سؤال تحقیق

آیا مجموعه‌ای از سنسورهای چندوجهی ارزان‌قیمت که به‌طور پیوسته در سطح درخت کار می‌کنند می‌توانند یک ناهنجاری فیزیولوژیکی اولیه مرتبط با حمله *Ips typographus* را در صنوبر نروژی جنگل‌های لیتوانی، پیش از ظاهر شدن علائم واضح و دیرهنگام، تشخیص دهند؟

در این مرحله سیستم نباید از یک اندازه‌گیری منفرد ادعای تشخیص قطعی گونه آفت داشته باشد. خروجی اولیه باید یک **امتیاز ناهنجاری/ریسک حمله در سطح درخت** باشد که بعداً با حمله تأییدشده توسط متخصص جنگل مقایسه شود.

## ۲. فرضیه زیستی/فنی

حمله *Ips* می‌تواند ترکیبی از تغییرات فیزیولوژیکی و شیمیایی در صنوبر ایجاد کند، از جمله:

- تغییر پاسخ VOC/e-nose در نزدیکی پوست درخت؛
- تغییر دینامیک قطر/شعاع تنه و کاهش رشد؛
- تغییر sap flow؛
- تغییرات محلی دمای پوست و میکروکلیما؛
- تعامل با وضعیت آب خاک و هوا.

فرض کاری این است که **تغییرات زمانی چندوجهی** از یک threshold مطلق برای یک سنسور قابل‌اعتمادتر هستند.

## ۳. طراحی مطالعه

طراحی مطالعه باید **آینده‌نگر و طولی (prospective longitudinal)** باشد.

### تعداد اولیه درختان

- پایلوت ترجیحی: حدود **۱۸ درخت صنوبر نروژی**.
- حداقل مطلق پایلوت: حدود **۱۵ درخت**، مشروط به بازبینی متخصص جنگل/آمار.
- در صورت امکان درخت‌ها هنگام نصب ظاهراً سالم باشند و در طول فصل به‌طور پیوسته مانیتور شوند.
- هدف این است که بخشی سالم بمانند و بخشی در طول پایش دچار حمله طبیعی تازه شوند.

### همسان‌سازی کنترل‌ها

درخت‌های سالم/مرجع و attacked باید تا حد امکان از نظر موارد زیر مشابه باشند:

- گونه؛
- DBH / اندازه؛
- سن یا age class؛
- تراکم توده / basal area؛
- رقابت و همسایگی؛
- نوع خاک/سایت؛
- شیب و جهت در صورت ارتباط؛
- میکروکلیمای محلی.

این موضوع برای کاهش اثر عوامل مخدوش‌کننده مانند خشکی، سایت، سن و رقابت ضروری است.

## ۴. الزامات انتخاب محل

یک توده نسبتاً بالغ صنوبر ترجیح داده می‌شود که:

- سابقه یا شواهد اخیر فعالیت *Ips* در نزدیکی آن وجود داشته باشد؛
- احتمال معقول وقوع حمله تازه طی یک فصل وجود داشته باشد؛
- امکان بازدید هفتگی ایمن و تکرارشونده وجود داشته باشد؛
- درختان مشابه کافی برای کنترل وجود داشته باشند؛
- داده هواشناسی محلی قابل دسترس باشد؛
- نصب pheromone trap با تأیید متخصص ممکن باشد.

محل نهایی بدون نظر فردی که مستقیماً در bark beetle/forest health کار می‌کند freeze نمی‌شود.

## ۵. برنامه سنجش

### ۵.۱ سنسورهای اصلی روی هر درخت

1. **Electronic nose / proxy برای VOC** (کاندید اولیه: سنسور MOX کلاس BME688)
   - raw gas resistance / heater-profile response؛
   - دما؛
   - رطوبت نسبی؛
   - فشار.

2. **Dendrometer**
   - تغییر شعاع یا محیط تنه با رزولوشن بالا؛
   - پایداری مناسب برای استقرار چندماهه در فضای باز.

3. **داده‌های سلامت node**
   - ولتاژ/وضعیت باتری؛
   - uptime و reset reason؛
   - دمای داخلی در صورت وجود؛
   - شاخص‌های ارتباطی.

### ۵.۲ داده‌های مشترک در سطح plot

برای هر plot تعداد محدودتری از موارد زیر کافی است:

- soil moisture یا شاخص آب خاک؛
- ambient/reference e-nose + T/RH/P دور از یک درخت خاص؛
- هواشناسی: دما، رطوبت، بارش، باد و در صورت دسترسی تابش خورشیدی؛
- شمارش pheromone trap تحت نظر متخصص.

### ۵.۳ اندازه‌گیری‌های مرجع اختیاری

اگر بودجه اجازه دهد، sap flow فقط روی تعداد کمی درخت مرجع (مثلاً ۳ تا ۴ درخت) نصب شود، نه روی همه درخت‌ها.

مشاهدات مرجع دستی/دوره‌ای می‌تواند شامل موارد زیر باشد:

- resin response؛
- boring dust؛
- entrance holes؛
- شواهد gallery/adult/larva؛
- وضعیت تاج و defoliation.

## ۶. دلیل نیاز به Ambient Reference Sensor

پاسخ MOX/e-nose تحت تأثیر دما، رطوبت، baseline هر device و میکروکلیمای محل است. بنابراین یک سنسور مرجع محیطی برای جدا کردن تغییرات محلی درخت از تغییرات عمومی plot لازم است.

نمونه featureهای مقایسه‌ای:

- دمای سنسور درخت منهای دمای مرجع؛
- RH درخت منهای RH مرجع؛
- gas response نرمال‌شده نسبت به baseline همان سنسور؛
- پاسخ درخت نسبت به مرجع plot.

## ۷. یکسان‌سازی نصب

برای کاهش variability مصنوعی:

- dendrometerها در ارتفاع اسمی یکسان و با روش نصب یکسان نصب شوند؛
- e-noseهای درختی ارتفاع، جهت و weather shield یکسان داشته باشند؛
- تابش مستقیم خورشید تا حد ممکن یکسان/کاهش داده شود؛
- همه جزئیات نصب در `sensor_registry` ذخیره شود؛
- تعویض یا recalibration در log ثبت شود.

## ۸. نرخ نمونه‌برداری اولیه

- e-nose gas/T/RH/P: هر ۱۰ دقیقه؛
- dendrometer: هر ۵ دقیقه؛
- soil moisture: هر ۱۵ دقیقه؛
- sap flow روی subset: هر ۱۰ دقیقه؛
- weather: ساعتی یا بهتر؛
- node health: هر ۳۰ تا ۶۰ دقیقه.

این اعداد فعلاً defaults هستند و در نسخه‌های v0.x بعد از بررسی توان/حافظه/BOM قابل تغییرند.

## ۹. دوره baseline

قبل از window اصلی حمله حداقل **۱۴ روز baseline** جمع شود؛ در صورت امکان ۳ تا ۴ هفته بهتر است.

هدف این است که رفتار عادی هر درخت و هر سنسور یاد گرفته شود و وابستگی به thresholdهای مطلق کاهش یابد.

## ۱۰. Ground truth جنگلداری

در دوره فعال، تقریباً هر هفته بازدید تخصصی انجام شود و اگر سیستم هشدار پایدار داد بازدید event-driven نیز انجام شود.

کد پیشنهادی وضعیت:

- `0`: سالم / بدون شواهد؛
- `1`: مشکوک؛
- `2`: حمله تازه تأییدشده؛
- `3`: آلودگی پیشرفته؛
- `4`: مرده/حذف‌شده.

مشاهدات مستقل:

- entrance holes؛
- boring dust؛
- resin تازه؛
- gallery evidence؛
- adult/larval evidence؛
- تغییر رنگ تاج؛
- defoliation؛
- سایر علائم استرس.

**تعریف نهایی `fresh attack confirmed` باید قبل از field deployment توسط متخصص bark beetle/forest health تأیید شود.**

## ۱۱. نقش Pheromone Trap

شمارش pheromone trap نشان‌دهنده **فشار محلی جمعیت آفت** است، نه label اختصاصی برای یک درخت.

از آن برای context و trend فصل استفاده می‌شود. محل نصب trap باید توسط متخصص تأیید شود تا monitoring خودش ریسک حمله اطراف درختان instrumented را تغییر ندهد.

## ۱۲. Feature Engineering

مدل نباید فقط با raw instantaneous value آموزش ببیند.

برای dendrometer:

- daily max/min؛
- daily radial amplitude؛
- night recovery؛
- 24 h growth؛
- 72 h trend؛
- deviation from 7-day personal baseline.

برای e-nose:

- log(gas resistance)؛
- normalized response نسبت به baseline فردی؛
- short-term slope؛
- تغییر ۲۴/۷۲ ساعته؛
- rolling mean/std؛
- tree-to-ambient differences؛
- heater-profile features در صورت استفاده.

context محیطی:

- T/RH؛
- بارش؛
- باد؛
- soil moisture؛
- VPD در صورت نیاز؛
- زمان روز/فصل.

## ۱۳. استراتژی ML

### فاز A — Anomaly Detection

برای هر درخت رفتار عادی مورد انتظار با در نظر گرفتن environment/time مدل می‌شود و deviation/anomaly score محاسبه می‌شود.

حتی اگر positive attack کم باشد این فاز ارزشمند است.

### فاز B — Supervised Attack-Risk Classification

اگر تعداد کافی attack تأییدشده ثبت شود، اول baselineهای ساده و قابل‌دفاع بررسی شوند:

- logistic/mixed-effects baseline در صورت تناسب؛
- Random Forest؛
- gradient-boosted trees مانند XGBoost.

مدل‌های sequence/DL فقط در صورت کافی بودن تعداد درخت‌ها و eventهای مستقل وارد شوند.

## ۱۴. قانون Validation

**timestampهای یک درخت هرگز به‌صورت random بین train و test تقسیم نمی‌شوند.**

Validation اصلی بر اساس `tree_id` انجام شود:

- GroupKFold؛
- leave-one-tree-out؛
- held-out trees.

اگر دو سایت داشتیم، train روی Site A و test روی Site B آزمون قوی‌تری است.

## ۱۵. معیارها

حداقل گزارش شوند:

- sensitivity/recall؛
- specificity؛
- precision؛
- F1؛
- balanced accuracy؛
- ROC-AUC؛
- PR-AUC؛
- false alerts per tree per week؛
- **detection lead time** نسبت به حمله تازه تأییدشده.

Accuracy به‌تنهایی کافی نیست.

## ۱۶. منطق هشدار

یک sample غیرعادی نباید هشدار عملی ایجاد کند.

قاعده نهایی باید persistence ریسک بالا را در چند window بخواهد. threshold و زمان persistence از validation data تعیین می‌شود و از قبل اختراع نمی‌شود.

## ۱۷. اگر attack کافی رخ نداد

اگر positive attack کم بود، classifier بزرگ train و overclaim نمی‌شود.

خروجی به شکل زیر frame می‌شود:

- prospective sensing feasibility study؛
- within-tree anomaly characterization؛
- case studies of confirmed attacks؛
- engineering validation of monitoring platform.

## ۱۸. وابستگی‌های باز

پیش از field deployment باید تعیین شوند:

1. field site دقیق؛
2. تعریف مورد تأیید متخصص برای fresh *Ips* attack؛
3. احتمال positive event و دسترسی به plot پرریسک؛
4. BOM و هزینه هر درخت؛
5. طراحی نهایی node/power/enclosure؛
6. تعداد نهایی درخت‌ها پس از budget review.
