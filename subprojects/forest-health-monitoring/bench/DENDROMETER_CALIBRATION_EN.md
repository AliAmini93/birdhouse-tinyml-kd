# Dendrometer Calibration and Acceptance — v0.2.1

## 1. Principle

The TT/BI Model 404 is a precision linear potentiometer with nominal 12.7 mm travel and manufacturer-listed ±1% linearity.

The final tree measurement quality will be determined by:
- sensor linearity;
- ADC noise;
- excitation stability;
- bracket geometry;
- mounting preload;
- thermal expansion;
- cable movement;
- mechanical creep.

Therefore the **assembled dendrometer**, not only the potentiometer, must be calibrated.

## 2. Fixture

Use:
- micrometer head, precision translation stage, or traceable displacement gauge;
- aluminum test fixture matching the intended field geometry;
- stable room temperature for the first calibration;
- ADS1115 and the exact excitation/electronics chain intended for the prototype.

Prefer metal brackets. Recent open-source dendrometer work reported much larger thermal dimensional changes for polymer/3D-printed structures than aluminum.

## 3. Calibration sequence

Use the central ~8–10 mm of travel, leaving end-stop margin.

Suggested sequence:

- positions: 0, 0.5, 1.0, ... 10.0 mm;
- at each position wait 3–5 s;
- collect >=50 ADC samples;
- move upward through all positions;
- move downward through all positions;
- repeat at least 5 complete up/down cycles.

Record:
- timestamp;
- reference displacement;
- ADC wiper;
- ADC excitation;
- ratio;
- direction;
- cycle number;
- temperature.

## 4. Primary calibration

Start with:

`x_mm = a * (Vwiper / Vexc) + b`

Do not introduce nonlinear polynomial correction unless residual analysis clearly shows a repeatable systematic nonlinearity.

Save:
- `a`;
- `b`;
- working range;
- calibration date;
- sensor serial number;
- fixture ID;
- residual statistics.

## 5. Engineering acceptance targets

These are **project targets**, not manufacturer guarantees.

- 100% monotonic response over the selected working range;
- no mechanical binding;
- short-term repeated-position standard deviation target: <=0.010 mm;
- calibrated maximum residual target in the central working range: <=0.050 mm;
- up/down hysteresis target: <=0.050 mm.

If these are not achieved, do not hide the error by smoothing. Identify whether the cause is:
- bracket;
- preload;
- sensor;
- ADC/noise;
- cable;
- thermal behavior.

The scientific literature demonstrates daily stem changes below 0.1 mm in some species, so a dendrometer with errors comparable to the biological signal is not acceptable for this project.

## 6. Thermal characterization

After room calibration, characterize zero/scale drift if an environmental chamber or controlled-temperature setup is available.

Suggested setpoints:
- 10 °C;
- 20 °C;
- 30 °C.

At a fixed mechanical displacement, record at least 30 min after temperature stabilization.

Calculate:
- zero drift in µm/°C;
- scale drift if multiple positions can be tested.

This stage is characterization first; do not invent a compensation model until repeatable data exist.

## 7. Installation setpoint

Install the field sensor close to mid-travel, not near an end stop.

The exact preload and initial position must be recorded in the sensor registry.

## 8. Calibration data file

Use `bench/dendrometer_calibration_template.csv`.

Never overwrite raw calibration runs.
