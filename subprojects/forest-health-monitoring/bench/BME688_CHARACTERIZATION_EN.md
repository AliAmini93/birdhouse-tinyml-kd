# BME688 Bench Characterization — v0.2.1

## 1. Objective

This stage validates:
- communication;
- initial stabilization;
- raw data logging;
- heater-profile traceability;
- sensor-to-sensor differences;
- enclosure/shield behavior.

It does **not** validate bark-beetle classification.

## 2. Initial stabilization

Bosch documentation states that factory-new BME boards should run for **at least 24 h** before meaningful recordings.

Therefore:

1. power both BME688 devices;
2. use the same documented measurement configuration;
3. run continuously for >=24 h;
4. flag this period as `stabilization`;
5. do not mix it into later biological training data.

## 3. Heater-profile policy

The BME688 gas response depends strongly on heater profile and duty cycle.

For the first characterization:
- use one fixed, fully documented profile;
- store heater step, target temperature/duration where available;
- do not change heater configuration mid-dataset without a configuration/version event.

If using Bosch BME688 Development Kit / AI-Studio:
- start with Bosch's documented default configuration (`HP-354`, `RDC-5-10`);
- only then explore alternative heater profiles.

If using a generic breakout:
- use Bosch BME68x SensorAPI or an equivalent verified driver;
- preserve the exact gas-heater settings in metadata.

## 4. Two-sensor co-location test

After stabilization, mount two sensors side-by-side in the same ventilated environment for >=12 h.

Store:
- gas resistance;
- temperature;
- RH;
- pressure;
- heater/profile metadata;
- sensor ID;
- timestamp.

Analyze:
- absolute offset;
- log(gas resistance) offset;
- correlation over time;
- temperature/RH difference;
- drift.

Do **not** expect identical absolute gas resistance between sensors. The purpose is to design normalization, not force equality.

## 5. Simple response challenge

Optional engineering-only check:

Expose both sensors to the same repeatable nonhazardous headspace, preferably a forestry-relevant material such as a sealed container with fresh spruce needles/resin material, followed by clean ambient recovery.

Purpose:
- verify that both sensors respond;
- compare response/recovery shapes;
- verify logging.

Do not use this experiment as an *Ips* training dataset or biological claim.

## 6. Outdoor sensor-head test

The BME688 must be exposed to air but protected from:
- direct rain;
- liquid water/condensation;
- insects/debris;
- direct solar heating.

Test the proposed ventilated shield for 48–72 h outdoors before field deployment.

A fully sealed IP box is unsuitable for the gas sensor itself.

## 7. Acceptance

Engineering targets after stabilization:

- >=99.5% expected valid records over 24 h;
- no unexplained heater-profile/configuration change;
- no bus-lockup requiring manual recovery;
- sensor ID and configuration traceable for every record;
- outdoor shield does not cause persistent condensation or obvious thermal trapping.

Cross-sensor baseline difference is characterized, not used as a pass/fail criterion.
