# Scope guardrail — after Prof. Rytis meeting, 2026-09-10

Use this file as a quick check before accepting or starting new Forest Internet tasks.

## Current agreed direction

1. **Do not implement all 6–7 AI applications as equivalent full-stack deliverables.**
2. Select **2–3 feasible priority AI use cases** for the main implementation and validation effort.
3. Acoustic/event-based applications are the strongest current candidates; **bird detection / bioacoustic monitoring** and illegal-logging sound detection were explicitly discussed as feasible.
4. Disease detection is **good-to-have / limited scope** unless later forestry-expert input makes a realistic field-validation plan possible.
5. Disease-related work may use laboratory/simulated/artificial time-series data for proof of concept; full field validation is not assumed.
6. Computer-vision disease detection is not a current priority.
7. Ali's core is **AI/Edge-AI and AI-side data processing**, not low-level RF/network/PCB/driver ownership.
8. On-device AI should perform lightweight preliminary/event detection; a local processing box may perform more detailed processing after an event.
9. The project intends to use a project-owned local backend with **ChirpStack + database + local processing + lightweight UI**, rather than depend primarily on ThingsBoard/TTN.
10. Egidijus leads the universal/custom hardware direction, including the board concept with LoRa and cellular connectivity.

## Immediate implementation baseline

**Next task:** deploy the existing **bird-detection acoustic AI model** on the available XIAO ESP32S3 Sense-class board, validate it in the lab, and use that result to guide the next step.

## Before expanding scope

Any new task should be checked against these questions:

- Is it one of the selected 2–3 priority AI use cases?
- Is it required for the AI-to-system interface, or is it actually low-level IoT/network/hardware work?
- Can it be validated within the remaining project timeline?
- Does it duplicate work expected from Egidijus's embedded/IoT group?
- If it is disease-related, has the use case been validated with forestry-domain experts first?

If the answer is unclear, treat the task as **not yet committed** until responsibility is clarified.

## Correction note

The original automatic transcription incorrectly rendered **bird detection** as **bear detection**. The scope record has been corrected accordingly.
