# Node Architecture — v0.2.0

## 1. Recommended physical partition

### A. Tree sensor head

Mounted close to the monitored spruce:

- BME688 in a ventilated hydrophobic/radiation shield;
- dendrometer mechanical assembly;
- TT Model 404 linear sensor;
- ADS1115 ADC;
- optional DS18B20 bark/contact probe;
- short sensor wiring;
- sensor ID / calibration metadata.

### B. Forest Internet host node

Mounted on/near the tree in a weatherproof enclosure:

- project MCU;
- local storage;
- RTC/time synchronization;
- LoRaWAN radio path managed by IoT team;
- optional cellular fallback managed by IoT team;
- regulated/switchable sensor rails;
- battery/power subsystem.

Keep BME688 outside the sealed main enclosure. The electronics enclosure can be IP-rated; the gas sensor must breathe through a purpose-built protected sensor head.

## 2. Electrical interfaces

```
BME688 ---------------- I2C --------\
                                     \
TT Model 404 -> ADS1115 -- I2C -------> Forest Internet MCU
                                      /
DS18B20 (optional) ----- 1-Wire -----/
                                      \
battery/current monitor ---------------> diagnostics
```

For plot nodes:

```
TEROS 10 -> switched excitation -> analog -> ADC
ambient BME688 -------------------------> I2C
```

## 3. Dendrometer excitation and ADC

Do not leave the resistive dendrometer continuously powered.

Recommended sequence every 5 min:

1. enable precision excitation rail;
2. wait ~100 ms;
3. sample Vex and Vout;
4. calculate ratio `Vout/Vex`;
5. store raw ADC + converted displacement;
6. disable excitation.

ADS1115 has sufficient nominal digital resolution for this purpose, but true field performance will be limited by potentiometer linearity, mechanical bracket drift, thermal expansion, contact geometry, cable noise, and calibration. Calibration is mandatory.

## 4. Cable/interface rule

I2C should remain short.

Preferred:
- host node mounted close to each tree sensor head, approximately sub-metre cable.

If the project later decides to share one electronics box among several trees:
- do not extend raw I2C several metres through the forest;
- add a local sensor microcontroller/ADC and use a robust differential bus such as RS-485 or SDI-12.

The final choice belongs to the IoT integration stage.

## 5. Communications policy

Raw time series are stored locally.

LoRaWAN payload contains only compact summaries, health/anomaly features, diagnostics, and alerts.

Suggested hourly summary fields:

- tree ID;
- timestamp;
- mean/min/max T/RH;
- BME688 gas features;
- stem radius change / daily shrinkage features;
- optional bark temperature;
- battery;
- QC flags;
- anomaly/risk score.

Immediate alert packet is sent only on a persistent anomaly/threshold event.

Bulk raw data can be retrieved during maintenance or through a higher-bandwidth path if the final platform provides it.

## 6. Prototype path

Phase 1 bench prototype:

- Nordic Thingy:91 X or another available dev board;
- external BME688 breakout;
- ADS1115 breakout;
- one TT Model 404 dendrometer mechanism;
- DS18B20 optional;
- local logging and cellular/USB retrieval.

Phase 2 outdoor pilot:

- 2–3 trees;
- one Ecomatik DR1 in parallel on at least one tree;
- verify mechanical stability, thermal drift, condensation/rain protection, and sensor-to-sensor BME688 variation.

Phase 3 scaled pilot:

- ~15–18 trees;
- Forest Internet LoRa-capable host;
- commercial reference sensors retained on a small subset.

## 7. Explicit ownership boundary

Forest-health subproject:
- sensor selection;
- sensor calibration;
- sensor-side acquisition requirements;
- signal preprocessing;
- Edge-AI features/model;
- data schema and QC.

IoT team:
- final MCU/PCB;
- LoRa/cellular driver stack;
- RF/antenna;
- gateway/network;
- final battery/solar hardware integration;
- enclosure manufacturing/productionization.

Shared:
- electrical interface;
- timing;
- payload;
- power measurement;
- end-to-end validation.
