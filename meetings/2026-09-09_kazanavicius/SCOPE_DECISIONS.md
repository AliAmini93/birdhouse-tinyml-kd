# Scope guardrail — after Dr. Egidijus Kazanavičius meeting, 2026-09-09

Use this file as a quick responsibility check before accepting or starting new Forest Internet tasks that touch the embedded node, communications, or Edge-AI integration.

## Current responsibility direction from this meeting

1. **Egidijus's group owns the low-level embedded/IoT implementation side.** This includes sensor-measurement firmware, sensor drivers, and data-transmission drivers.
2. The next-generation forest node is expected to support multiple sensing modalities, potentially including audio, video, ultrasound, temperature, humidity, CO2, LiDAR/distance, moisture, pH, flame, motion, and other sensors.
3. The communication architecture is expected to combine **LoRa/LoRaWAN** and **4G / NB-IoT** rather than relying on the previous 2G design.
4. A heterogeneous communication strategy is preferred: LoRa where range/connectivity and payload size make it suitable, and cellular connectivity where richer data or weak LoRa connectivity requires it.
5. The project intends to avoid dependence on third-party IoT platforms where possible and use a project-controlled backend, with **ChirpStack** discussed for LoRaWAN/network management.
6. Low-power operation is a key design requirement. Nodes should spend substantial time in sleep/low-power mode, with local storage used to buffer data where appropriate.
7. **Ali's core contribution is the AI/Edge-AI side**, especially lightweight on-device anomaly/event detection, preprocessing/inference, model optimisation, and validation.
8. The intended Edge-AI behavior is event-driven: perform lightweight local checking, remain in low-power operation during normal conditions, and trigger richer sensing/data transmission when an anomaly is detected.
9. AI-to-communication integration is a **shared interface task**, but ownership of the LoRaWAN/NB-IoT stack, low-level modem/radio implementation, and associated drivers should remain with the embedded/IoT side unless explicitly reassigned later.
10. Hardware prototyping may initially use Nordic Thingy:91 / Nordic development hardware before later transition to a more customised/minimised project-specific board.

## Ali — core / expected focus

- lightweight on-device AI / TinyML;
- anomaly and event detection;
- embedded preprocessing and inference;
- model compression / quantisation / optimisation where needed;
- accuracy-latency-memory-energy trade-off analysis;
- event-triggered sensing/transmission logic from the AI side;
- lab and field validation of AI behavior;
- adaptation/retraining based on collected forest data;
- definition of compact AI outputs/events to pass to the communication layer.

## Shared / interface work

- AI-to-firmware integration;
- definition of data/event payloads;
- coordination of wake/sleep behavior with AI events;
- end-to-end latency and energy evaluation where AI behavior affects the node;
- system-level field validation involving both AI and communication behavior;
- integration of richer audio/video transfer after an AI event, where required.

## Not Ali's core responsibility from this meeting

- sensor-driver development;
- low-level sensor-measurement firmware;
- RS485 driver implementation;
- LoRaWAN modem/radio firmware;
- NB-IoT / cellular modem low-level implementation;
- RF and antenna design;
- gateway/network administration as a primary responsibility;
- custom PCB design and manufacturing;
- enclosure and power-electronics design.

## Architectural boundary to preserve

```text
Sensors
  -> MCU + low-level firmware/drivers        [Egidijus / embedded-IoT side]
  -> local sensing/data stream
  -> Edge AI / anomaly detection             [Ali core]
  -> event / compact AI result
  -> LoRaWAN and/or 4G-NB-IoT transport      [embedded-IoT / shared interface]
  -> ChirpStack / project-owned backend      [system/backend side]
  -> higher-level analysis / services
```

## Before accepting additional embedded/network tasks

Check the following:

- Is this task required to integrate AI with the sensor node, or is it actually a low-level firmware/network task?
- Has Egidijus's group already taken responsibility for the required driver/communication implementation?
- Does the task directly support Edge-AI validation, event-triggering, latency, energy, or model behavior?
- Would accepting it shift Ali from AI/Edge-AI responsibility into general IoT/network engineering?

If ownership is unclear, treat the task as **shared / not yet committed** until responsibility is explicitly clarified with the project leads.
