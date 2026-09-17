# Forest Health Monitoring / پایش سلامت جنگل

**Parent project:** Forest Internet / Birdhouse  
**Subproject:** Forest Health Monitoring  
**Current version:** v0.2.1-draft  
**Primary biological target:** Norway spruce (*Picea abies*)  
**Primary threat under study:** European spruce bark beetle (*Ips typographus*)

## Purpose

This subproject records, versions, and evolves the experimental, sensing, electronics, data, and AI plan for a forest-health monitoring use case within the Birdhouse / Forest Internet project.

The current research question is deliberately narrow: can low-cost, continuously operating, tree-level multimodal sensors detect early physiological anomalies associated with *Ips typographus* attack in Lithuanian Norway spruce before clear late-stage visual symptoms appear?

Markdown/CSV files are the source of truth. Generated PDFs, when available, are snapshots only.

## Canonical documents

- `PROTOCOL_EN.md`, `PROTOCOL_FA.md` — experimental protocol.
- `DATA_SCHEMA_EN.md`, `DATA_SCHEMA_FA.md` — data schema.
- `BOM_EN.md`, `BOM_FA.md` — v0.2 candidate sensing BOM and procurement logic.
- `NODE_ARCHITECTURE_EN.md`, `NODE_ARCHITECTURE_FA.md` — sensing-node architecture and integration boundary.
- `POWER_DATA_BUDGET.md` — first-order sensor power and data-rate calculations.
- `COST_ESTIMATE.md` — pilot cost scenarios and assumptions.
- `bom/bom_v0_2_0.csv` — machine-readable candidate BOM.
- `DECISIONS.md` — versioned technical decisions and unresolved questions.
- `REFERENCES.md` — literature, manufacturer, and market evidence ledger.
- `ROADMAP.md` — next stages toward field-ready deployment.
- `VERSION`, `CHANGELOG.md` — version and revision history.
- `schemas/*.csv` — machine-readable data templates.

## Versioning policy

- `v0.1.x`: research framing, protocol, data schema.
- `v0.2.x`: sensor BOM, node architecture, power/data/cost estimate.
- `v0.3.x`: field-site and forestry ground-truth protocol finalized.
- `v0.4.x`: acquisition/firmware/power/communication implementation plan.
- `v1.0.0`: field-ready protocol and frozen implementation baseline.

## Current system boundary

This subproject owns the AI/sensing experiment and sensor-side interface requirements. The preferred final host is the Forest Internet universal MCU/communications node owned by the IoT team. Low-level LoRaWAN/LTE-M/NB-IoT modem firmware, RF/antenna engineering, gateway/network administration, and final PCB production remain outside this subproject unless explicitly reassigned.

## Status at v0.2.0

### Retained from v0.1

- *Picea abies* / *Ips typographus* prospective longitudinal pilot.
- About 18 trees preferred; ~15 absolute pilot minimum pending field/budget review.
- Core modalities: e-nose/VOC proxy + continuous dendrometry.
- Plot context: soil moisture + ambient reference + weather + pheromone pressure.
- Weekly forestry inspection as primary biological ground truth.
- Grouped-by-tree validation; no random timestamp split.
- Detection lead time and false alerts/tree/week are primary operational metrics.

### v0.2 candidate hardware baseline

- BME688 retained as the primary low-cost e-nose/VOC proxy because it has direct bark-beetle literature continuity and a mature embedded/software ecosystem.
- Scalable dendrometry path: TT Electronics/BI Model 404 precision linear potentiometer + ADS1115 16-bit ADC + temperature-stable metal bracket, with per-device calibration.
- Two commercial Ecomatik DR1 units are recommended as reference/cross-check instruments rather than buying commercial dendrometers for every tree.
- TEROS 10 is the preferred research-grade plot soil-moisture sensor; default planning quantity is three, not one per tree.
- Waterproof DS18B20 bark/contact temperature is optional and low-cost.
- Sap flow remains a small-subset reference measurement and is not included in the base cost until quotations are obtained.
- Existing Forest Internet LoRa-capable universal node is preferred for field deployment. Nordic Thingy:91 X is a useful bench/cellular PoC fallback, not the final per-tree LoRa architecture.
- Raw high-rate data remain local; LoRa carries compact summaries and alerts.

### Still not frozen

- exact field site;
- specialist-approved fresh-attack definition;
- exact Forest Internet universal-node I/O/power rails and final PCB;
- final dendrometer mechanical design and calibration fixture;
- final BME688 heater profile and sampling policy;
- sap-flow vendor/quantity;
- final battery/solar subsystem after the IoT node is electrically characterized.

## v0.2.1 bench-readiness package

- `bench/BENCH_PROTOTYPE_EN.md`, `bench/BENCH_PROTOTYPE_FA.md`
- `bench/DENDROMETER_CALIBRATION_EN.md`, `bench/DENDROMETER_CALIBRATION_FA.md`
- `bench/BME688_CHARACTERIZATION_EN.md`, `bench/BME688_CHARACTERIZATION_FA.md`
- `bench/ACCEPTANCE_CHECKLIST.md`
- `bench/bench_bom_v0_2_1.csv`
- calibration/data templates in `bench/*.csv`

The next physical gate is a one-tree-equivalent bench build followed by a 2–3 tree outdoor pilot.
