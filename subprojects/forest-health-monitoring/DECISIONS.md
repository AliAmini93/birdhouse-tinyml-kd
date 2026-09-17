# Decision Log

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
