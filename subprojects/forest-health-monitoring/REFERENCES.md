# Evidence / Reference Ledger

This file records the evidence that motivated the current v0.1.0 design. It is not a systematic review and should be expanded as the subproject evolves.

## Core scientific evidence

1. **Electronic-nose / bark-beetle field classification**  
   Frontiers in Forests and Global Change (2024), article 1445094.  
   DOI: `10.3389/ffgc.2024.1445094`  
   Relevance: BME688-class e-nose measurements, healthy vs infested spruce sections, Random Forest; supports VOC/e-nose feasibility but also highlights microclimate/site confounding and the need for stronger individual-tree validation.

2. **Physiological response of Norway spruce to natural Ips typographus attack**  
   Frontiers in Forests and Global Change (2023), article 1197229.  
   DOI: `10.3389/ffgc.2023.1197229`  
   Relevance: sap flow, dendrometer/stem increment, bark temperature, soil-water context, monoterpene response; supports the selected physiological measurements and minute-scale sampling.

3. **Lithuanian / Baltic Ips risk context**  
   Use current Lithuanian State Forest Service monitoring reports and peer-reviewed Baltic/Lithuanian studies during site-selection v0.3.  
   Relevance: site/stand risk variables, current outbreak pressure, candidate plots, pheromone-monitoring context.

## Forestry consultation evidence

A forestry-domain consultation identified the following as meaningful candidate tree-response/ground-truth variables:

- diameter increment;
- sap flow;
- resin response;
- climate/weather context;
- pheromone-trap pressure;
- defoliation/crown condition;
- matched healthy controls with similar species/size/age/soil/competition.

The consultant also emphasized the importance of obtaining guidance from a specialist who works directly on bark beetles before freezing the field site and fresh-attack confirmation protocol.

## Evidence-handling rule

When a reference motivates a design decision, record:

- what the paper actually measured;
- whether the study was tree-level or area-level;
- number of independent trees/sites/events;
- environmental context;
- validation split strategy;
- limitations relevant to transfer to Lithuania.

Do not copy headline accuracy values without these qualifiers.
