# Sensor Power and Data Budget — v0.2.0

**Scope:** first-order engineering estimate for the forest-health sensor subsystem.  
**Excluded:** final MCU, LoRa/cellular radio, SD-card/storage, regulator losses, cold-weather battery derating, solar charger, and enclosure thermal effects. Those require the final IoT-node electrical design.

## 1. Sensor-side average-current estimate

### BME688

Bosch lists ~3.9 mA average current in standard gas-scan mode and ~10.8 s per scan. If one full gas scan is executed every 10 minutes:

`3.9 mA × 10.8 s / 600 s ≈ 0.070 mA average`

The exact heater profile must be measured because application-specific BME AI-Studio profiles can change energy substantially.

### Dendrometer

For a 10 kΩ linear potentiometer excited at 3.3 V:

`I ≈ 0.33 mA while powered`

If excitation is on for 0.1 s every 300 s:

`0.33 × 0.1 / 300 ≈ 0.00011 mA average`

The ADC contribution is similarly negligible when duty-cycled.

### DS18B20

Assume roughly 1.5 mA during a worst-case 0.75 s conversion every 600 s:

`1.5 × 0.75 / 600 ≈ 0.0019 mA average`

### Planning number

Raw calculated sensor-only duty-cycled current is approximately 0.07–0.08 mA before board/regulator overhead.

For design reserve, use:

**0.2 mA average per tree sensor subsystem**

until measured on real hardware.

At 0.2 mA:
- 24 h: 4.8 mAh/day;
- 180 d: 864 mAh.

This demonstrates why radio/MCU/power architecture is likely to dominate the final energy budget.

## 2. TEROS 10

TEROS 10 is plot-level and should be power-switched. Measurement duration is short and sampling can be 15–30 min. Its contribution to whole-system average power is small compared with a continuously active radio.

## 3. Raw data volume

Conservative binary planning assumptions:

### BME688
One record every 10 min, including gas-scan features + T/RH/P + IDs/QC:
~64 bytes/record.

`144 records/day × 64 B ≈ 9.2 kB/day/tree`

### Dendrometer
One record every 5 min:
~12 bytes/record.

`288 × 12 B ≈ 3.5 kB/day/tree`

### Optional bark temperature + diagnostics
Budget ~1–2 kB/day/tree.

### Total planning value
Use **15 kB/day/tree binary raw**.

For 18 trees:
- ~270 kB/day;
- ~49 MB over 180 days.

CSV/text representations may be several times larger; even a 5× factor remains modest (<250 MB for the tree sensors over a 6-month field season).

Therefore local storage is not a limiting factor.

## 4. LoRa budget

Do not transmit raw data continuously.

Example policy:
- 1 hourly summary, target payload ~30–50 bytes;
- 24 packets/day/tree;
- 18 trees -> 432 routine packets/day across the pilot;
- immediate alert packets only on events.

Exact LoRaWAN duty-cycle, spreading factor, confirmed/unconfirmed uplink policy, and gateway capacity are owned by the IoT/network design and must be validated after the deployment region and gateway topology are known.

## 5. Measurement campaign requirements

Before scaling to 18 trees, physically measure:

- BME688 current for the chosen heater profile;
- host sleep current;
- host active current;
- LoRa TX/RX energy at representative SF;
- SD/local-storage write energy;
- regulator quiescent current;
- cold-weather battery performance;
- dendrometer excitation stability.

A bench power profiler measurement supersedes all estimates in this file.
