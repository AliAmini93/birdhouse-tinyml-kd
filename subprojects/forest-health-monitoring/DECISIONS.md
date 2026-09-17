# Decision Log

## v0.2.1 — Bench validation gate

**Status:** Draft; must be executed physically before scale-up.

### New decisions

29. Validate a one-tree-equivalent sensor chain before purchasing/assembling the full 15–18 tree system.
30. Use two BME688 devices in the bench phase to quantify sensor-to-sensor baseline differences.
31. Factory-new BME688 devices require >=24 h initial stabilization before meaningful recording, following Bosch guidance.
32. Bench BME688 configuration must be fixed/versioned; heater-profile changes must be recorded as configuration events.
33. Artificial indoor odor/headspace tests may verify sensor response but must not be used to claim or train *Ips typographus* detection.
34. Calibrate the **assembled** dendrometer mechanism, not the Model 404 alone.
35. Prefer aluminum/stainless mechanical structures for primary calibration and field prototypes; polymer brackets require separate thermal characterization.
36. Preserve raw dendrometer ADC, excitation measurement, ratio, and calibrated displacement.
37. Project bench targets are monotonic response, <=0.010 mm repeated-position SD, <=0.050 mm maximum central-range calibration residual, and <=0.050 mm hysteresis; these are engineering targets, not manufacturer specifications.
38. Thingy:91 X onboard environmental sensing is BME680, not BME688; external BME688 remains required. Avoid I2C address conflict with onboard BME680 at 0x76.
39. A 48–72 h outdoor dry run is required before a 2–3 tree pilot.
40. Biological/forestry field data remain separate from bench/calibration datasets.


## v0.2.0 — Sensor BOM and node architecture baseline

**Status:** Draft engineering baseline; not procurement-frozen.

### New decisions

16. Retain Bosch **BME688** as the primary e-nose/VOC proxy because it has direct literature continuity with spruce-bark-beetle sensing, exposes raw gas data, supports custom heater profiles, and is inexpensive/available.
17. Use a **two-tier dendrometer strategy**: scalable in-house TT Electronics/BI Model 404 + ADS1115 + metal bracket on the main cohort, plus two commercial Ecomatik DR1 units as reference/cross-check instruments.
18. Individual calibration and thermal/mechanical characterization are mandatory for every in-house dendrometer.
19. Use **TEROS 10** as the preferred research-grade plot soil-moisture sensor; default planning allocation is three sensors per plot, not one sensor per tree.
20. Waterproof DS18B20 bark/contact temperature is optional because it is cheap and easy to integrate, but it is not a primary disease/pest signal.
21. Sap flow remains limited to a small reference subset and is excluded from the base cost until quotations and the field site are available.
22. The preferred final host is the **Forest Internet universal LoRa-capable node** developed by the IoT team.
23. Nordic Thingy:91 X is a bench/cellular-PoC fallback only; it is not the final per-tree radio architecture because it does not provide LoRaWAN.
24. Keep I2C short. If one electronics box eventually serves several trees over multi-metre cabling, insert local acquisition and use a robust differential bus (e.g. RS-485/SDI-12) rather than long raw I2C.
25. Store raw measurements locally and use LoRaWAN for compact summaries, diagnostics, risk scores, and event alerts.
26. Power-gate the dendrometer excitation and other sensors wherever practical.
27. Sensor-side planning current is provisionally budgeted at 0.2 mA average per tree excluding MCU/radio/storage/regulator losses, pending bench measurement.
28. The v0.2 cost baseline is **sensor-subsystem only**; final universal-node, radio, battery/solar, and enclosure costs remain separate until the IoT design is frozen.

### Explicitly not frozen

- final PCB/layout;
- final BME688 heater profile;
- final dendrometer bracket geometry/material/thickness;
- final battery/solar sizing;
- final LoRa payload and spreading-factor policy;
- exact number/placement of soil sensors and pheromone traps if multiple plots are selected;
- sap-flow procurement.

## v0.1.0 — Initial experimental baseline

**Status:** Draft / research baseline, not yet field-frozen.

### Decisions

1. Use the broad subproject name **Forest Health Monitoring** rather than a disease-only name, because the current primary target (*Ips typographus*) is a pest and the platform may later cover disease/stress use cases.
2. Primary biological target is Norway spruce (*Picea abies*) in Lithuania.
3. Primary threat for the first prospective study is *Ips typographus*.
4. Prefer a prospective longitudinal design over a trivial healthy-vs-dead cross-sectional classifier.
5. Initial target cohort is ~18 trees; ~15 is treated only as an absolute pilot minimum pending statistical/forestry review.
6. Core per-tree sensors: electronic-nose/VOC proxy + dendrometer.
7. Use a plot-level ambient reference e-nose and soil-moisture/weather context to reduce microclimate confounding.
8. Sap flow is useful but expensive/complex, so it is optional on a small reference subset rather than mandatory on every tree.
9. Resin, entrance holes, boring dust, galleries, defoliation, etc. are primarily ground-truth/manual forestry observations at this stage.
10. Pheromone traps represent local beetle pressure, not a tree-specific label.
11. Primary AI output in v0.x is an anomaly/attack-risk score; do not overclaim species-specific diagnosis until evidence supports it.
12. Start with anomaly detection + simple supervised ML baselines; DL is conditional on the number of independent trees/events.
13. Validation must be grouped by tree; random timestamp splitting is prohibited.
14. Detection lead time and false alerts/tree/week are primary practical metrics alongside standard classification metrics.
15. Exact site and definition of confirmed fresh attack remain open and require a bark-beetle/forest-health specialist.

### Explicitly rejected/deferred for core v0.1

- camera/hyperspectral/UAV as the core sensing route;
- ambient CO2 as a primary tree-specific disease/pest signal;
- photosynthesis instrumentation for unattended continuous deployment;
- continuous electronic resin-flow sensing without a validated practical method;
- buying sap-flow systems for every tree before budget/BOM review.
