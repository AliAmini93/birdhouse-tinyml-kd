# Evidence / Reference Ledger

**Updated:** 2026-09-17  
This is a design evidence ledger, not a systematic review.

## A. Core biological/ML evidence

1. **BME688/e-nose and bark-beetle field classification**  
   Frontiers in Forests and Global Change (2024), article 1445094.  
   DOI: `10.3389/ffgc.2024.1445094`  
   Relevance: supports BME688-class electronic-nose feasibility; also motivates strict microclimate controls and tree-grouped validation.

2. **Norway spruce physiological response to natural Ips typographus attack**  
   Frontiers in Forests and Global Change (2023), article 1197229.  
   DOI: `10.3389/ffgc.2023.1197229`  
   Relevance: sap flow, dendrometer/stem increment, bark temperature, soil-water context, monoterpene response.

3. **Low-cost wireless dendrometer and digital twin**  
   Measurement (2026), article 121442.  
   DOI: `10.1016/j.measurement.2026.121442`  
   Relevance: open-hardware LoRaWAN dendrometry, calibration/thermal-error treatment, scalable field sensing.

4. **Low-cost open-source dendrometer with precision linear potentiometer**  
   Smart Agricultural Technology (2026), 102073.  
   DOI: `10.1016/j.atech.2026.102073`  
   Relevance: ~USD 70 open-source design based on TT/BI Model 404-class precision linear potentiometer; long-term/field validation.

5. **Inexpensive open-source dendrometer**  
   AoB PLANTS (2024), `plae009`.  
   Relevance: demonstrates low-cost potentiometric dendrometry, calibration, high-resolution time series, and importance of mechanics/environment.

## B. Manufacturer / integration evidence

6. **Bosch BME688 product/datasheet**  
   https://www.bosch-sensortec.com/en/products/environmental-sensors/gas-sensors/bme688  
   Relevance: interfaces, current, scan time, environmental ranges.

7. **Bosch BME AI-Studio / BSEC ecosystem**  
   https://www.bosch-sensortec.com/en/software-tools/software/bme688-and-bme690-software  
   Relevance: raw gas profiles, labeling/training workflow, embedded deployment.

8. **Texas Instruments ADS1115**  
   https://www.ti.com/product/ADS1115  
   Relevance: 16-bit I2C ADC, PGA, low power.

9. **TT Electronics/BI Model 404**  
   https://www.ttelectronics.com/products/passive-components/potentiometers/404/  
   Relevance: precision spring-return linear potentiometer family.

10. **Ecomatik DR series**  
    https://ecomatik.de/en/products/growth-and-plant-water-status-dendrometer/  
    Relevance: commercial research dendrometer and logger integration; analog 0–Vex; ≥12-bit acquisition.

11. **METER TEROS 10**  
    https://metergroup.com/products/teros-10/  
    Relevance: rugged research-grade VWC, 70 MHz, analog output, third-party logger compatibility.

12. **Nordic Thingy:91 X**  
    https://www.nordicsemi.com/Products/Development-hardware/Nordic-Thingy-91-X  
    Relevance: cellular PoC platform, nRF9151, Qwiic/STEMMA/Grove, 1350 mAh battery.

13. **ICT International sap-flow products**  
    https://ictinternational.com/product-category/b-plant/sap-flow/  
    Relevance: research HRM/HFD sap-flow candidates; quotation before procurement.

## C. Price snapshots (not guarantees)

- BME688 bare IC, DigiKey Lithuania: ~EUR 6.75 at 10+ quantity.
- BME688 Adafruit breakout, DigiKey Europe: ~EUR 17.
- ADS1115, DigiKey Lithuania: ~EUR 4.93 at 10+ for VSSOP.
- TT/BI Model 404, DigiKey Europe: ~EUR 21 at 10+.
- Ecomatik DR1, European distributor: ~EUR 335.
- TEROS 10, European distributor: ~EUR 218.50–255.
- Nordic Thingy:91 X, Mouser Lithuania: ~EUR 88.32.
- Waterproof DS18B20, Lithuanian retail: ~EUR 2.47 at 10+.
- IBL3 Ips trap, Lithuanian retail: ~EUR 19.36.
- Ips seasonal lure, Lithuanian retail: ~EUR 11–12.40.

All prices must be refreshed before purchase.

## D. Forestry consultation evidence

Forestry consultation supported:

- diameter increment;
- sap flow;
- resin response;
- climate/weather context;
- pheromone pressure;
- defoliation/crown condition;
- matched controls.

It also emphasized that the field protocol must be reviewed by a specialist directly working on bark beetles.

## Evidence-handling rule

For every future source, record:

- what was actually measured;
- tree-level vs area-level;
- independent trees/sites/events;
- environmental context;
- validation split;
- transferability to Lithuania;
- hardware and calibration limitations.
