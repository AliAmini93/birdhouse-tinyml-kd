# Candidate Sensor BOM — v0.2.0

**Status:** engineering/research baseline; not yet a procurement order.  
**Price snapshot:** 2026-09-17; indicative ex-VAT unless the cited source states otherwise.

## 1. Selection principles

The BOM prioritizes:

1. direct scientific relevance to Norway spruce / bark-beetle physiology;
2. continuous unattended operation;
3. low-rate data suitable for edge/LoRa operation;
4. field replaceability and traceability;
5. scalable cost for ~15–18 trees;
6. compatibility with the Forest Internet universal MCU node;
7. retention of raw measurements for later ML.

## 2. Per-tree core sensing

### 2.1 BME688 — electronic nose / VOC proxy

**Selected candidate:** Bosch Sensortec BME688.

Why:

- Measures gas resistance plus temperature, relative humidity, and pressure.
- I2C/SPI, 1.71–3.6 V supply.
- Published *Ips typographus* field work used BME688-class e-nose data.
- Bosch provides BME AI-Studio, BSEC, and raw SensorAPI workflows.
- Bare sensor pricing is roughly EUR 6–8 at prototype/low-volume quantities.
- Breakout boards are available around EUR 17–20 for rapid prototyping.

Important: store raw gas resistance/heater-profile measurements. Do not rely only on IAQ/eCO2 outputs.

**Mechanical requirement:** ventilated rain/radiation shield close to bark; do not seal the gas sensor in an IP enclosure.

### 2.2 Continuous dendrometry

Two-tier strategy:

#### Scalable field sensor
**TT Electronics/BI Model 404 precision linear potentiometer** (e.g. 404R10KL1.0) plus custom aluminum/stainless mounting bracket.

- 12.7 mm travel.
- ±1% linearity.
- -40 to +125 °C listed operating range for the cited variant.
- Approx. EUR 21 each at 10-unit pricing.
- Similar Model 404 hardware was used in a 2026 open-source low-cost dendrometer study.
- Requires individual calibration and temperature/mechanical characterization.

#### Acquisition ADC
**TI ADS1115**.

- 16-bit delta-sigma ADC.
- I2C.
- 2.0–5.5 V.
- Typical 150 µA in continuous mode; duty-cycled operation is much lower average.
- Approx. EUR 5 each at 10-unit pricing in the easy-to-assemble VSSOP variant.

The dendrometer excitation must be regulated and switched only during measurement. Ratio-metric processing (`Vout/Vex`) is preferred.

#### Commercial reference
**Ecomatik DR1**, two units recommended.

- Research-grade radial dendrometer.
- 11 mm range.
- Analog 0–Vex output.
- Manufacturer recommends at least 12-bit acquisition.
- Approx. EUR 335 each from a European distributor at the snapshot date.

Purpose: cross-check and characterize the scalable in-house dendrometer on 1–2 reference trees. Do not buy 18 commercial units before the scalable design is evaluated.

## 3. Optional per-tree bark/contact temperature

**Waterproof DS18B20 probe**

- 1-Wire.
- 3.0–5.5 V.
- Typical retail ~EUR 2.5–3.5 in Lithuania at quantity.
- Optional because bark-temperature effects are expected to be secondary, but the marginal cost is small.

Mount with repeatable contact pressure and radiation shielding. It must not be treated as true internal cambium temperature.

## 4. Plot-level soil moisture

**Preferred:** METER Group TEROS 10.

- Research-grade VWC.
- 70 MHz capacitance/frequency-domain method.
- Analog 1.0–2.5 V output.
- 3–15 V excitation.
- Requires ≥12-bit single-ended voltage measurement.
- Typical European price found: ~EUR 218–255 ex VAT.
- Default planning quantity: 3 sensors per plot, not 18.

Rationale: drought/water availability is a major confounder for dendrometer and tree-stress signals; a rugged research-grade sensor is more valuable here than many cheap, poorly stable probes.

If multiple plots are used, use at least 2–3 soil probes per plot or revise the allocation after site heterogeneity is known.

## 5. Ambient reference e-nose

Use 1–2 BME688 reference sensors per plot in standardized shaded/radiation-shielded locations away from direct bark contact.

Purpose:

- estimate plot-wide microclimate and gas baseline;
- create differential features such as tree-minus-ambient RH/T/gas response;
- reduce the risk that the ML model simply learns microclimate/site differences.

For early prototyping, an Adafruit BME688 STEMMA/Qwiic board (~EUR 17) is convenient. For field scale, use the same custom BME688 sensor-head PCB as the tree nodes.

## 6. Pheromone monitoring

Use specialist-approved *Ips typographus* traps/lures as a **plot-level pressure indicator**, not a tree-specific label.

Lithuanian retail examples at the snapshot date:

- IBL3 trap ~EUR 19.36;
- seasonal pheromone lure ~EUR 11–12.4.

Trap type, number, and placement must be approved by a bark-beetle specialist because traps intentionally attract beetles and should not be placed arbitrarily near instrumented healthy trees.

## 7. Sap flow

Recommended only on ~3–4 reference trees if budget permits.

Candidate class:

- ICT International SFM1 / SFMx or equivalent research HRM instrument.

Why not in base BOM:

- specialized invasive installation;
- substantially higher cost than other sensors;
- quotation-dependent;
- strong physiological value but not required on every tree.

Do not purchase until the specialist/site design is frozen and a quotation is available.

## 8. Host electronics

### Preferred final field host
Forest Internet universal MCU/LoRa node developed by the IoT team.

Required sensor-side interfaces:

- I2C for BME688 and ADS1115;
- one switched/regulated excitation rail for dendrometer;
- optional 1-Wire for DS18B20;
- analog input or ADS1115 channel for TEROS 10 on plot nodes;
- local nonvolatile storage;
- timestamp/RTC capability;
- LoRaWAN uplink for summaries/alerts.

### PoC/fallback host
Nordic Thingy:91 X.

Useful because:

- nRF9151 Cortex-M33, 1 MB Flash, 256 KB RAM;
- LTE-M/NB-IoT/GNSS;
- Qwiic/STEMMA/Grove expansion;
- 1350 mAh rechargeable battery;
- ~EUR 88 at current distributor pricing.

Limitation: it is cellular, not LoRaWAN. Therefore it is excellent for bench/early field PoC but should not displace the project’s LoRa architecture.

## 9. Not selected as core at v0.2

- Ambient CO2 per tree.
- Photosynthesis instrument.
- Hyperspectral/camera/UAV.
- Direct continuous electronic resin sensor without a validated measurement method.
- One sap-flow meter per tree.
- Cheap hobby soil probes as scientific ground truth.
