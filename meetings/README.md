# Forest Internet meeting archive

This directory is the chronological project-meeting record used to preserve technical decisions, scope boundaries, responsibilities, follow-up actions, and source transcripts so that future implementation stays aligned with what was actually discussed.

## Meetings

### 2026-09-09 — Dr. Egidijus Kazanavičius

Directory: [`2026-09-09_kazanavicius/`](2026-09-09_kazanavicius/)

Main topics:
- next-generation forest sensor-node architecture;
- transition from legacy 2G toward LoRaWAN + 4G/NB-IoT;
- low-power/event-driven operation;
- preliminary on-device AI;
- Nordic prototyping platform;
- separation between AI work and Egidijus-group firmware/driver/hardware responsibilities.

### 2026-09-10 — Prof. Rytis

Directory: [`2026-09-10_rytis/`](2026-09-10_rytis/)

Main topics:
- narrowing the AI scope to approximately 2–3 feasible priority use cases;
- treating difficult long-timescale use cases such as disease detection as limited/lab/simulation work where appropriate;
- clarifying on-device AI versus local-box processing;
- project-owned ChirpStack/database/local-processing architecture;
- responsibility boundaries;
- immediate next step: deploy and lab-test the acoustic AI model on the available edge hardware.

The concise working scope after this meeting is recorded in [`2026-09-10_rytis/SCOPE_DECISIONS.md`](2026-09-10_rytis/SCOPE_DECISIONS.md).

## Usage rule

Before accepting a new task or materially expanding implementation scope, check the latest meeting record and scope-decision file. If a proposed task is outside the recorded responsibility boundary or the selected use cases, treat it as **not yet committed** until ownership/scope is explicitly clarified with the project leads.
