# Meeting with Prof. Rytis — Forest Internet scope and local processing architecture

**Date:** 2026-09-10  
**Project context:** Forest Internet / Miško internetas  
**Main purpose:** Narrow the AI scope, clarify which use cases require field validation, and clarify the role of the local mini-computer / ChirpStack processing box.

## Meeting outcome at a glance

The main agreement was to **narrow the AI scope to approximately 2–3 feasible priority use cases** rather than attempt full implementation and field validation of every threat/application listed in the work plan within the 15-month project.

The remaining, less feasible use cases can be treated as **good-to-have**, demonstrated with laboratory/simulated/artificial data where appropriate, and not necessarily field-validated when the required biological timescale is incompatible with the project schedule.

A second important clarification was that the system should use a **project-owned local processing box** running an open-source LoRaWAN/backend stack such as ChirpStack plus a database and local processing. Preliminary AI can run on-device, while more detailed processing can run on the local box after an event triggers richer data collection/transmission.

## Scope decisions / agreements

### 1. AI use cases should be narrowed

Agreed direction:

- Select roughly **2–3 priority, feasible AI use cases** for full implementation.
- Prioritise use cases that can realistically be trained, deployed and validated within the project timeline.
- Treat the remaining use cases as secondary / good-to-have rather than equivalent mandatory field-validation targets.

Examples discussed as feasible:

- acoustic / sound analysis;
- bear / animal detection;
- illegal logging detection using acoustic signatures such as saw, engine, breaking or related sounds.

### 2. Disease detection should not drive the core scope

Disease monitoring was identified as a difficult case because meaningful changes may require long-term monitoring, potentially longer than the available field-validation window.

Agreed direction:

- disease detection may be implemented in a limited laboratory/simulation form;
- synthetic/artificial or representative time-series data may be used for a proof-of-concept classifier;
- full field validation should **not be assumed as a core deliverable** if the biological timescale makes it unrealistic;
- computer-vision-based disease detection was explicitly not preferred as a main direction for this project.

Potential disease-related signals discussed included sap flow, CO2, humidity, temperature and other tree/environmental parameters. A discussion with VDU forestry specialists was proposed before defining this use case more precisely.

### 3. Two levels of AI/processing are envisaged

**On-device / MCU side:**

- lightweight preliminary processing;
- anomaly/event detection;
- low-power wake/sleep logic;
- trigger richer sensing or transmission when something suspicious is detected.

**Local processing box:**

- receive data from the network/gateway side;
- run ChirpStack / database-related services;
- perform more detailed data processing and potentially heavier AI/classification;
- support a lightweight local web interface for foresters.

### 4. Communication remains a distinct layer

The discussion explicitly separated the transmission layer from the processing/AI layer. The universal hardware concept is expected to support both LoRa and a cellular modem (4G / NB-IoT), with Egidijus leading the custom-board direction.

The main architectural idea is to use small/low-power LoRa traffic where suitable and use cellular connectivity when richer data such as audio/video must be transferred after an event.

### 5. Project-owned backend instead of dependence on commercial platforms

The intended direction is to avoid relying on ThingsBoard / The Things Network as the primary project backend and instead operate a local/project-controlled system based on open-source components such as ChirpStack, a database, local processing and a custom lightweight UI.

This was motivated by customisation, cost, control and project-evaluation considerations.

> Note: Statements in the spoken discussion about exact LoRa/ChirpStack packet sizes were exploratory and are **not recorded here as verified technical limits/capabilities**. Those details must be checked against the actual LoRaWAN/ChirpStack configuration before implementation.

## Responsibility boundary captured from the discussion

### Ali — core / expected focus

- 2–3 selected AI use cases rather than all listed applications;
- Edge-AI / TinyML model deployment and preliminary on-device processing;
- model training, optimisation and lab validation;
- selected field validation where feasible;
- event/anomaly-driven AI logic;
- AI/data processing on the local processing box where required;
- AI integration with the data/database/backend interface;
- adaptation/retraining based on collected data.

### Shared / interface work

- definition of data/event payloads between AI and communication layers;
- integration of node-side AI with gateway/local-box processing;
- evaluation of end-to-end latency, reliability and energy where it affects AI operation;
- lightweight result visualisation / UI integration as needed.

### Not the core AI responsibility

- low-level sensor drivers;
- custom PCB design and manufacturing;
- RF/antenna design;
- LoRa/cellular modem firmware and low-level transmission implementation;
- full network engineering as a primary responsibility;
- full field validation of every application named in the proposal.

Egidijus is expected to lead the universal hardware/board design and associated embedded/communication-side development, consistent with the previous meeting.

## Immediate next step

The immediate technical step agreed at the end of the meeting is to **deploy the existing acoustic AI model on the available XIAO ESP32S3 Sense-class hardware and validate it in the lab**, then proceed based on the result.

## Follow-up actions

- Message Prof. Rytis on Telegram to obtain contact with VDU forestry specialists.
- Discuss realistic disease indicators and validation timescales with forestry experts before committing to a disease-detection use case.
- Finalise the 2–3 priority AI use cases.
- Continue the acoustic Edge-AI deployment/lab test as the immediate implementation task.
- Later, clarify the exact ownership boundary for ChirpStack/database/local-box administration versus AI/data-processing integration.

## Files in this archive

- `transcript.md` — full supplied transcription of the meeting.
- `audio/part_00.opus` … `audio/part_05.opus` — sequential speech-oriented archival audio parts (3-minute segments; final part shorter), created from the original MP3 for reliable GitHub archival.
- `SCOPE_DECISIONS.md` — concise scope guardrail for future work.
- `manifest.json` — provenance and checksums.
