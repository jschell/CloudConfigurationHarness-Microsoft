# Tea Shop — Canonical Wardley Map

Source: haberlah/wardley-mapping (CC BY-SA 4.0)

## Strategic Question

What does a tea shop need to serve a customer a cup of tea, and where should it focus?

## OWM Map

```
title Tea Shop
anchor Customer [0.97, 0.50]
component Cup of Tea [0.79, 0.61]
component Tea [0.63, 0.81]
component Hot Water [0.52, 0.52]
component Kettle [0.43, 0.35] inertia
component Water [0.38, 0.82]
component Power [0.10, 0.70]
Customer->Cup of Tea
Cup of Tea->Tea
Cup of Tea->Hot Water
Hot Water->Water
Hot Water->Kettle
Kettle->Power
evolve Kettle 0.62
```

## Evolution Rationale

| Component | Stage | Score | Evidence | Strategic Implication |
|---|---|---|---|---|
| Customer | Anchor | 0.50 | User anchor; positioned centrally | Starting point for all dependencies |
| Cup of Tea | Product | 0.61 | Standardized product; multiple cafes/shops offer it | Differentiate on experience, not existence |
| Tea | Commodity | 0.81 | Global commodity market; price-based competition | Buy, don't source uniquely — unless provenance is the product |
| Hot Water | Product | 0.52 | Understood process; multiple equipment options exist | No differentiation here; use reliable equipment |
| Kettle | Custom Built | 0.35 | Inertia present — shop invested in specific model; but commercial kettles are product-stage | The inertia is organizational, not market. Evolving toward product (0.62) |
| Water | Commodity | 0.82 | Utility-grade; regulated municipal supply in most markets | Pure commodity; treat as invisible infrastructure |
| Power | Commodity | 0.70 | Utility infrastructure; widespread, standardized | Buy from grid; no differentiation possible |

## Strategic Commentary

1. **Inertia on Kettle is the key risk.** The Kettle sits at Custom Built (0.35) with inertia, while market-available commercial kettles are product-stage. The shop is over-investing in a component that should be a commodity purchase. `evolve Kettle 0.62` signals the right direction.

2. **All sub-components below Hot Water are commodity.** Tea, Water, and Power are buy decisions with zero differentiation value. The shop should spend no strategic energy here.

3. **Differentiation lives in Cup of Tea and customer experience.** The only place to build competitive advantage is in how the tea is served — not in the supply chain beneath it.

4. **No genesis-stage components.** This is a mature value chain. The strategic posture is efficiency and operations, not exploration.
