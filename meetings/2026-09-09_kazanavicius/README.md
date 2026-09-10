# Meeting with Dr. Egidijus Kazanavičius — 2026-09-09

## Context

Technical discussion for the **Forest Internet / Miško internetas** project.  
The meeting focused on the next-generation forest sensor-node architecture, communication strategy, low-power operation, and the role of embedded AI.

## Key technical points

- Previous work by Ahmad used a custom PCB with a microcontroller, sensor interfaces, LoRa connectivity, and 2G/GSM.
- The previous 2G-based design needs redesign because 2G is being phased out in Lithuania and Europe.
- The new architecture should support a wide range of sensors: video, audio, ultrasound, temperature, humidity, CO2, LiDAR/distance, moisture, pH, flame, motion, and potentially others.
- Dr. Kazanavičius stated that **his group will develop the low-level firmware, sensor drivers, and data-transmission drivers**.
- Two communication paths are being considered:
  - LoRa/LoRaWAN through an RS485-connected device such as S2100.
  - 4G / NB-IoT for locations where LoRa connectivity is insufficient or where larger payloads are required.
- A heterogeneous network is being considered: low-power LoRa nodes with selected gateway/router nodes using cellular connectivity.
- The team decided **not to use ThingsBoard**. They plan to use their own computing/backend architecture, with ChirpStack for LoRaWAN/network management.
- Low-power operation is a primary design objective. Data may be stored locally (e.g. 256 MB or more) while the device sleeps and transmitted periodically or when an event occurs.
- Embedded AI is proposed as an event-triggering mechanism:
  - lightweight anomaly detection runs locally;
  - normal data can remain stored locally / device can remain in low-power mode;
  - on anomaly, relevant data are collected and transmitted immediately.
- Raw or high-volume data such as video are problematic over LoRa because fragmentation into many payloads increases radio-on time and battery drain.
- LoRa vs 4G/NB-IoT should be selected according to payload size, connectivity, energy, and operating cost.
- NB-IoT/cellular connectivity introduces a per-node recurring cost, making hybrid LoRa + cellular routing attractive at scale.
- **Nordic Thingy:91 X** and a Nordic development/design kit were discussed as the initial prototyping platform.
- The intended development path is proof-of-concept on a commercial open platform, followed by a custom/minimised product and custom PCB in later project stages.

## Implication for Ali's likely scope

### Primary AI/Edge-AI responsibility
- TinyML / lightweight anomaly detection on the sensor node.
- Embedded signal preprocessing and inference.
- Compression/quantisation and low-power inference.
- Event-driven sensing/transmission logic.
- Accuracy-latency-memory-energy trade-off analysis.
- Lab and field validation of AI performance.
- Adaptation/retraining from real forest data.

### Shared with the IoT/embedded team
- AI-to-firmware integration.
- Definition of data/event payloads.
- End-to-end energy measurement.
- Evaluation of LoRa vs NB-IoT communication strategies.
- Field deployment and system-level validation.

### Explicitly indicated as Kazanavičius-group work
- Low-level sensor firmware.
- Sensor drivers.
- Communication/data-transmission drivers.

## Architectural sketch

```text
Sensors
  -> MCU + firmware
  -> local storage / sleep management
  -> lightweight Edge AI / anomaly detection
  -> event-triggered transmission
  -> LoRaWAN and/or 4G-NB-IoT
  -> ChirpStack / project-owned backend
  -> higher-level analytics / management
```

## Related meeting materials

- Full transcript: `transcript.txt`
- Architecture slide: `Misko-internetas.pdf`
- Nordic Thingy:91 X reference photo: `Nordic_Thingy91X_photo.jpg`
- Meeting audio recording: `meeting_audio_8kbps.ogg` (speech-oriented archival copy)

The transcript was supplied by Ali after transcription in Gemini. The binary meeting assets are preserved with SHA-256 checksums in `manifest.json`.
