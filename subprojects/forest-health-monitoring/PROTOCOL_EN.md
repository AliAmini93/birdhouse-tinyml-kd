# Experimental Protocol — Forest Health Monitoring

**Version:** v0.1.0-draft  
**Parent project:** Forest Internet / Birdhouse  
**Target ecosystem:** Lithuanian Norway-spruce stands  
**Target species:** *Picea abies*  
**Primary threat:** *Ips typographus*

## 1. Research question

Can low-cost, continuously operating multimodal tree-level sensors identify an early physiological anomaly associated with *Ips typographus* attack in Lithuanian Norway spruce before clear late-stage visual symptoms appear?

At this stage the system should not claim species-specific diagnosis from a single sensor reading. The first target is a defensible **tree-level anomaly / attack-risk score** that can later be tested against forestry-confirmed attack events.

## 2. Biological/technical hypothesis

An *Ips* attack can induce a combination of physiological and chemical changes in Norway spruce. Candidate observables include:

- changes in VOC/e-nose response near the bark;
- altered stem-radius dynamics and reduced increment;
- altered sap-flow dynamics;
- local bark/microclimate changes;
- interactions with soil-water and weather conditions.

The working hypothesis is that multimodal temporal changes are more informative than any single absolute threshold.

## 3. Study design

Use a **prospective longitudinal** design.

### Initial target cohort

- Preferred pilot: about **18 Norway spruce trees**.
- Absolute pilot minimum: about **15 trees**, subject to forestry/statistical review.
- Trees should be apparently healthy at installation where feasible, then monitored continuously through the active season.
- The experiment should aim to capture trees that remain healthy and trees that receive naturally occurring fresh attack during monitoring.

### Control matching

Healthy/reference and attacked trees should be as comparable as practical with respect to:

- species;
- DBH / size;
- age or age class;
- stand density / basal area;
- competition/neighbourhood;
- soil/site type;
- slope/aspect when relevant;
- local microclimate.

This is critical to reduce confounding by drought, site, age, and competition.

## 4. Site-selection requirements

Prefer a mature Norway-spruce stand with:

- documented or recent *Ips* activity nearby;
- realistic probability of fresh attack during one field season;
- safe and repeated access for weekly forestry inspection;
- enough comparable trees for controls;
- access to local weather data;
- feasibility of pheromone monitoring under an entomologist/forester-approved placement protocol.

The site must not be finalized without input from a specialist who works directly with bark beetles / forest health.

## 5. Sensing plan

### 5.1 Core per-tree sensing

Each instrumented tree should preferably carry:

1. **Electronic-nose / VOC proxy sensor** (initial candidate: BME688-class MOX sensor)
   - raw gas resistance / heater-profile response;
   - temperature;
   - relative humidity;
   - pressure.

2. **Dendrometer**
   - high-resolution stem-radius or circumference change;
   - sufficient stability for multi-month outdoor deployment.

3. **Node diagnostics**
   - battery voltage/state;
   - uptime/reset reason;
   - local device temperature if available;
   - communication diagnostics.

### 5.2 Plot-level context sensing

Use a smaller number of shared sensors/data sources for:

- soil moisture or soil-water proxy;
- ambient/reference e-nose + T/RH/P away from a target tree;
- meteorological data: temperature, humidity, precipitation, wind, solar radiation if available;
- pheromone-trap counts under forestry/entomology guidance.

### 5.3 Optional reference measurements

If budget allows, install sap-flow sensing on a small subset (for example 3–4 reference trees), not necessarily on all trees.

Manual/periodic reference observations may include:

- resin response;
- boring dust;
- entrance holes;
- gallery/adult/larval evidence;
- crown condition and defoliation.

## 6. Why an ambient reference sensor is required

MOX/e-nose responses are affected by temperature, humidity, device baseline, and site microclimate. Therefore, a local ambient reference is needed to help distinguish tree-local changes from plot-wide environmental changes.

Derived comparisons may include:

- tree temperature minus ambient temperature;
- tree RH minus ambient RH;
- gas response normalized to the sensor's own baseline;
- tree response relative to plot reference.

## 7. Installation consistency

To reduce artificial variability:

- dendrometers should use the same nominal mounting height and mounting method;
- tree e-nose sensors should use the same height, orientation, and ventilated weather shield;
- direct sun exposure should be minimized/standardized where practical;
- all mounting details must be stored in `sensor_registry`;
- replacements/recalibrations must be logged.

## 8. Sampling plan

Initial targets:

- e-nose gas/T/RH/P: every 10 min;
- dendrometer: every 5 min;
- soil moisture: every 15 min;
- sap flow (subset): every 10 min;
- weather: hourly or better;
- node health: every 30–60 min.

These rates are working defaults and may be changed during v0.x after power/storage/BOM analysis.

## 9. Baseline period

Collect at least **14 days** of baseline before the main expected attack window; 3–4 weeks is preferable when feasible.

The purpose is to learn each tree/sensor's normal temporal behavior rather than relying only on population-wide absolute thresholds.

## 10. Forestry ground truth

A forestry inspection should occur approximately weekly during the active period, with event-driven inspection if the system raises a persistent alert.

Suggested status coding:

- `0`: healthy / no evidence;
- `1`: suspicious;
- `2`: fresh attack confirmed;
- `3`: advanced infestation;
- `4`: dead/removed.

Record independent observations such as:

- entrance holes;
- boring dust;
- fresh resin response;
- gallery evidence;
- adult/larval evidence;
- crown discoloration;
- defoliation;
- other stress symptoms.

**The final definition of `fresh attack confirmed` must be approved by a bark-beetle/forest-health specialist before field deployment.**

## 11. Role of pheromone traps

Pheromone-trap data represent **local beetle pressure**, not a tree-specific infection label.

Use trap counts as plot-level context and for seasonal pressure trends. Trap placement must be approved by a specialist so monitoring does not unintentionally alter local attack risk around instrumented trees.

## 12. Feature engineering

Do not train models only on instantaneous raw values.

Candidate dendrometer features:

- daily maximum/minimum;
- daily radial amplitude;
- night recovery;
- 24 h growth/increment;
- 72 h trend;
- deviation from 7-day personal baseline.

Candidate e-nose features:

- log gas resistance;
- normalized response relative to individual baseline;
- short-term slope;
- 24 h / 72 h change;
- rolling mean/standard deviation;
- tree-to-ambient differences;
- heater-profile features if used.

Environmental context:

- T/RH;
- precipitation;
- wind;
- soil moisture;
- VPD derived from T/RH where appropriate;
- seasonal/time-of-day features.

## 13. ML strategy

### Phase A — anomaly detection

Model each tree's expected normal behavior conditional on environment/time, then compute deviation/anomaly scores.

This phase remains useful even if the number of confirmed attacks is small.

### Phase B — supervised attack-risk classification

If enough confirmed attacks are captured, compare simple, defensible baselines first:

- logistic/mixed-effects baseline where appropriate;
- Random Forest;
- gradient-boosted trees such as XGBoost.

Sequence DL models should only be introduced if the number of independent trees/events justifies them.

## 14. Validation rule

**Never randomly split timestamps from the same tree between training and test sets.**

Primary validation should group by `tree_id`:

- GroupKFold;
- leave-one-tree-out;
- held-out trees.

If multiple sites become available, a stronger test is train-on-site-A / test-on-site-B.

## 15. Metrics

Report at minimum:

- sensitivity/recall;
- specificity;
- precision;
- F1;
- balanced accuracy;
- ROC-AUC;
- PR-AUC;
- false alerts per tree per week;
- **detection lead time** relative to forestry-confirmed fresh attack.

Accuracy alone is insufficient.

## 16. Alert logic

A single abnormal sample must not generate an operational alert.

The final rule should require a persistent elevated risk/anomaly across multiple windows. Threshold and persistence duration must be selected from validation data, not invented in advance.

## 17. Contingency if few attacks occur

If too few fresh attacks are captured, do not overclaim a supervised classifier.

The outcome should then be framed as:

- a prospective sensing feasibility study;
- within-tree anomaly characterization;
- case studies of confirmed attacks;
- engineering validation of the monitoring platform.

## 18. Current open dependencies

Before field deployment, resolve:

1. exact field site(s);
2. specialist-approved definition of confirmed fresh *Ips* attack;
3. expected positive-event probability / access to high-risk plots;
4. sensor BOM and per-tree cost;
5. final node/power/enclosure design;
6. final sample size after budget review.
