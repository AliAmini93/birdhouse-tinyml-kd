# Changelog

## [0.2.0] - 2026-09-17

### Added

- Market/literature-based sensor BOM candidate.
- English/Persian BOM rationale.
- English/Persian node architecture.
- First-order sensor power and data-rate budget.
- Cost scenarios for 15- and 18-tree pilots.
- Machine-readable BOM CSV.
- Commercial-reference + scalable-open-dendrometer strategy.
- Explicit integration boundary with the Forest Internet IoT node.

### Changed

- BME688 is now the named primary e-nose candidate.
- Dendrometer choice is narrowed to a scalable precision-potentiometer design with a 16-bit external ADC, plus commercial references.
- TEROS 10 is the preferred plot-level soil-moisture sensor.
- Nordic Thingy:91 X is classified as PoC/fallback rather than final LoRa node.

### Not frozen

This is a procurement/design baseline, not a purchase order. Exact field site, fresh-attack label protocol, final universal-node electronics, and sap-flow quotation remain open.

## [0.1.0] - 2026-09-17

### Added

- Bilingual (English/Persian) experimental protocol.
- Bilingual data schema.
- Initial decision log and evidence ledger.
- Versioning policy and roadmap.
- Machine-readable CSV schema headers.

### Scientific baseline

- *Picea abies* / *Ips typographus* prospective longitudinal pilot.
- ~18-tree preferred pilot, ~15-tree absolute minimum pending review.
- Core sensing: e-nose/VOC proxy + dendrometer.
- Plot context: soil moisture, ambient reference, weather, pheromone pressure.
- Optional sap-flow subset.
- Weekly forestry ground truth.
- Tree-grouped ML validation and detection-lead-time reporting.
