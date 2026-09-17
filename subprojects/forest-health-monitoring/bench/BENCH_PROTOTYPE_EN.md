# One-Tree Bench Prototype — v0.2.1

**Purpose:** validate the complete sensor-side chain before buying or assembling a 15–18 tree deployment.

This bench is **not** intended to prove bark-beetle detection. It validates electronics, mechanical dendrometry, raw-data integrity, cross-sensor variation, and the calibration workflow.

## 1. Bench hardware

Minimum bench set:

- 2 × BME688 breakout/sensor heads;
- 1 × TT Electronics / BI Model 404, 10 kΩ, 12.7 mm linear potentiometer;
- 1 × ADS1115 16-bit ADC breakout;
- 1 × optional waterproof DS18B20;
- 1 × 3.3 V MCU/dev board with I2C and local/USB logging;
- 1 × aluminum/stainless dendrometer fixture;
- 1 × micrometer or calibrated displacement stage for dendrometer calibration;
- breadboard/cabling/connectors;
- stable 3.3 V supply.

Why **two** BME688 units? One-tree deployment eventually needs a tree-local sensor plus ambient/reference information. Co-locating two devices at the bench also quantifies sensor-to-sensor baseline differences before field normalization is designed.

## 2. Host-board rule

The sensor validation must remain host-agnostic.

Preferred order:

1. use the Forest Internet universal MCU board if an electrically stable prototype is already available;
2. otherwise use Nordic Thingy:91 X if available;
3. otherwise use any existing 3.3 V development board with a reliable I2C stack.

Do **not** buy a new host merely to validate the sensor chain.

Important Thingy:91 X note:
- Nordic documentation identifies the onboard environmental sensor as **BME680**, not BME688;
- the BME680 occupies I2C address `0x76`;
- therefore an external BME688 is still required for this subproject;
- if using Thingy:91 X, use the supported expansion connector and avoid an address collision. A single external BME688 can use `0x77`; a second BME688 may require another bus or an I2C multiplexer.

## 3. Bench wiring concept

```text
                    +------------------+
                    | 3.3 V HOST MCU   |
                    |                  |
I2C SDA/SCL --------+----------------------------+
                    |                            |
                    |                         ADS1115 (0x48)
                    |                            |
                    |                      A0 <- dendro wiper
                    |                      A1 <- excitation sense
                    |
                    +---- BME688 #1 (0x77 or isolated bus)
                    |
                    +---- BME688 #2 (0x76/0x77 or mux/second bus)
                    |
                    +---- optional DS18B20 (1-Wire)
```

Model 404:
- top terminal -> stable/switched excitation;
- bottom terminal -> ground;
- wiper -> ADS1115 A0;
- excitation -> ADS1115 A1 for ratio correction.

Store both raw ADC channels and use:

`ratio = V_wiper / V_excitation`

Never store only converted millimetres.

## 4. Bring-up sequence

### Gate A — electrical communication

1. Verify supply rails before connecting sensors.
2. Enumerate I2C devices.
3. Confirm BME688 chip communication and ADS1115 communication.
4. Log T/RH/P/gas resistance and raw ADC readings for 60 min.
5. Check monotonic timestamps and file integrity.

Pass target:
- no resets;
- no corrupted records;
- >=99.9% structurally valid records during the 60-min test.

### Gate B — 24 h logger stability

Run the complete chain for 24 h at room conditions.

Log:
- raw BME688 fields;
- heater/profile metadata;
- ADS1115 raw values;
- dendrometer ratio;
- host timestamp;
- board/supply diagnostics if available.

Pass target:
- no unexplained timestamp reversal;
- no unhandled sensor-bus lockup;
- >=99.5% expected records present.

### Gate C — dendrometer calibration

Follow `DENDROMETER_CALIBRATION_EN.md`.

### Gate D — BME688 characterization

Follow `BME688_CHARACTERIZATION_EN.md`.

### Gate E — short outdoor dry run

After indoor validation, operate the assembly for 48–72 h outdoors **without using the data for biological conclusions**.

The purpose is to identify:
- condensation/rain problems;
- cable movement;
- mechanical creep;
- temperature sensitivity;
- brownouts;
- gas-sensor enclosure problems;
- clock/logging issues.

## 5. What this bench must NOT claim

Do not train or report an *Ips typographus* classifier from artificial indoor odors.

The bench establishes that the hardware can create trustworthy data. Biological labels must come from the later forestry field protocol.

## 6. Exit criteria for v0.2.x bench readiness

Proceed to a 2–3 tree outdoor pilot only if:

- BME688 logging is stable after initial sensor stabilization;
- dendrometer passes the calibration/repeatability targets or deviations are understood;
- raw and calibrated data are both traceable;
- sensor serial/ID and calibration coefficients are recorded;
- mechanical mounting does not bind the Model 404 over its intended working range;
- the electronics survive a 48–72 h outdoor dry run;
- observed power and data rates are recorded.

Any failure becomes a v0.2.x design revision before scale-up.
