# Cost Estimate — v0.2.0

**Snapshot:** 2026-09-17.  
**Currency:** EUR.  
**Purpose:** planning only; not a quotation or procurement approval.

## 1. Per-tree scalable sensor-head estimate

| Item | Unit EUR | Basis |
|---|---:|---|
| BME688 bare sensor | 6.75 | DigiKey ~10+ quantity |
| TT/BI Model 404 linear sensor | 20.96 | DigiKey ~10+ quantity |
| ADS1115 ADC | 4.93 | DigiKey VSSOP ~10+ quantity |
| Waterproof DS18B20 (optional but included in estimate) | 2.47 | Lithuanian retail 10+ |
| Custom sensor PCB + passives/connectors | 12.00 | engineering estimate |
| Aluminum/stainless bracket + gas/radiation shield | 18.00 | engineering estimate |
| Cable/glands/misc. | 7.00 | engineering estimate |
| **Estimated sensor head** | **72.11** | excludes host MCU/radio/power |

Mechanical/custom-PCB values are placeholders to be replaced by supplier quotes after CAD/PCB design.

## 2. Plot/reference equipment planning

Default one-plot pilot:

| Item | Qty | Unit EUR | Total EUR |
|---|---:|---:|---:|
| TEROS 10 soil moisture | 3 | 218.50 | 655.50 |
| Ecomatik DR1 commercial reference | 2 | 335.00 | 670.00 |
| Ambient BME688 breakout + estimated shield | 2 | 32.09 | 64.18 |
| IBL3 trap + seasonal lure | 3 | 31.76 | 95.28 |
| **Plot/reference subtotal** |  |  | **1,484.96** |

Sap-flow instruments are excluded because current pricing is quotation-dependent.

## 3. Pilot totals excluding host-node electronics

### 15 trees
- 15 × EUR 72.106 = EUR 1,081.59
- plot/reference subtotal = EUR 1,484.96
- **total ≈ EUR 2,566.55**

### 18 trees
- 18 × EUR 72.106 = EUR 1,297.91
- plot/reference subtotal = EUR 1,484.96
- **total ≈ EUR 2,782.87**

Add at least 15–25% contingency for prototypes, spares, failed sensors, mechanical rework, cables, shipping, and VAT as applicable.

## 4. Temporary Thingy:91 X PoC-host scenario

Current distributor price observed: ~EUR 88.32/unit.

If every tree temporarily used a Thingy:91 X:

- 15 trees: ~EUR 1,324.80 extra;
- 18 trees: ~EUR 1,589.76 extra.

Combined with the sensor estimate:

- 15 trees: ~EUR 3,891.35;
- 18 trees: ~EUR 4,372.63.

This is **not** the preferred final architecture because Thingy:91 X is cellular and the Forest Internet design expects LoRa capability. It is only a useful benchmark for the maximum cost of a ready dev-board host.

## 5. Commercial-dendrometer upper comparison

Buying Ecomatik DR1 at ~EUR 335 for all 18 trees would cost ~EUR 6,030 for dendrometers alone, before e-nose, soil, nodes, power, and communications.

Therefore the open/scalable dendrometer path has high economic value if field validation confirms adequate stability.

## 6. Not yet priced

- final Forest Internet universal node;
- LoRa radio/module if not already part of universal node;
- battery/solar charger;
- final IP enclosure;
- sap-flow instruments;
- professional installation labor;
- field transport;
- replacement lures over the final campaign;
- VAT/shipping/import differences.

These must be incorporated before procurement freeze.
