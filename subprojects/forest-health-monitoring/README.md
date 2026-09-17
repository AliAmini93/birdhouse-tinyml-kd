# Forest Health Monitoring / پایش سلامت جنگل

**Parent project:** Forest Internet / Birdhouse  
**Subproject:** Forest Health Monitoring  
**Current version:** v0.1.0-draft  
**Primary biological target:** Norway spruce (*Picea abies*)  
**Primary threat under study:** European spruce bark beetle (*Ips typographus*)

## Purpose

This subproject records, versions, and evolves the experimental plan for a sensor- and AI-based forest-health monitoring use case within the Birdhouse / Forest Internet project.

The current focus is deliberately narrow: determine whether low-cost, continuously operating, tree-level multimodal sensors can detect early physiological anomalies associated with *Ips typographus* attack in Lithuanian Norway spruce before clear late-stage visual symptoms appear.

Markdown files are the source of truth. Generated PDFs, when available, are snapshots only.

## Canonical documents

- `PROTOCOL_EN.md` — English experimental protocol.
- `PROTOCOL_FA.md` — Persian experimental protocol.
- `DATA_SCHEMA_EN.md` — English data schema.
- `DATA_SCHEMA_FA.md` — Persian data schema.
- `DECISIONS.md` — versioned technical decisions and unresolved questions.
- `REFERENCES.md` — literature/evidence ledger.
- `ROADMAP.md` — next stages toward a field-ready subproject.
- `VERSION` — current semantic version.
- `CHANGELOG.md` — revision history.
- `schemas/*.csv` — machine-readable CSV templates/headers.

## Versioning policy

This subproject uses semantic-style pre-release versioning:

- `v0.1.x`: research framing, protocol, data schema.
- `v0.2.x`: sensor BOM, node architecture, and cost estimate.
- `v0.3.x`: field-site and forestry ground-truth protocol finalized.
- `v0.4.x`: acquisition/firmware/power/communication implementation plan.
- `v1.0.0`: field-ready protocol and frozen implementation baseline.

Minor revisions that materially alter scientific design increment the minor version; corrections/clarifications increment the patch version.

## Current boundary

This subproject covers the AI/sensing experiment and the data required for it. Low-level radio/network engineering, custom PCB manufacturing, and the wider Forest Internet communications infrastructure remain outside this subproject unless explicitly added later.

## Status at v0.1.0

Frozen for now:

- species: *Picea abies*;
- primary threat: *Ips typographus*;
- prospective longitudinal design;
- target cohort: about 18 trees, with ~15 as an absolute pilot minimum;
- core per-tree sensing: electronic-nose/VOC proxy + dendrometer;
- plot context: soil moisture + ambient reference + weather;
- optional reference sensing: sap flow on a small subset;
- weekly forestry inspection as the essential ground-truth process;
- grouped-by-tree validation; no random timestamp split;
- primary outcome includes detection lead time, not accuracy alone.

Not yet frozen:

- exact field site(s);
- forestry definition/protocol for a confirmed fresh *Ips* attack;
- final sensor models/BOM;
- final node electronics and power design;
- final sample size after budget/site review.
