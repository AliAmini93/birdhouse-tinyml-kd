# Bench Acceptance Checklist — v0.2.1

## Electrical
- [ ] Correct supply rails verified before sensor connection.
- [ ] BME688 #1 identified.
- [ ] BME688 #2 identified or isolated through mux/second bus.
- [ ] ADS1115 identified.
- [ ] Optional DS18B20 identified.
- [ ] No I2C address conflict.
- [ ] 60-minute bring-up log >=99.9% structurally valid records.
- [ ] 24-hour logger test >=99.5% expected records.
- [ ] No unexplained resets/bus lockups.

## BME688
- [ ] >=24 h first-use stabilization completed.
- [ ] Stabilization data flagged.
- [ ] Heater profile/config version recorded.
- [ ] 12 h co-location run completed.
- [ ] Sensor-to-sensor baseline difference quantified.
- [ ] Outdoor shield 48–72 h test completed.

## Dendrometer
- [ ] Model 404 serial/ID recorded.
- [ ] Metal fixture/bracket used for primary test.
- [ ] 0–10 mm up/down calibration completed.
- [ ] >=5 cycles completed.
- [ ] Raw ADC and excitation saved.
- [ ] Calibration coefficients saved.
- [ ] Monotonic response confirmed.
- [ ] Repeatability/hysteresis/residuals reported.
- [ ] Thermal drift characterized if controlled-temperature setup is available.

## Data/QC
- [ ] UTC timestamps.
- [ ] Raw and converted fields stored together.
- [ ] Sensor IDs on every record.
- [ ] Configuration changes logged.
- [ ] No raw file overwritten.
- [ ] Bench data stored separately from future biological field data.

## Decision
- [ ] PASS: ready for 2–3 tree outdoor pilot.
- [ ] REVISE: design issue identified and versioned before scale-up.
