# UBS Healthcare Mapping — IBGE and Territory Enrichment

This document describes the next analytical layer for the UBS mapping project: enriching the current registry dataset with IBGE and territorial indicators.

## Why enrich the dataset?

The current project answers:

> Where are UBS records distributed across Brazil, and what is the quality of their geolocation fields?

The enriched version should answer a stronger question:

> How does the distribution of UBS records relate to population, territory and potential planning priorities?

This distinction matters because a high number of UBS records in a state or municipality does not necessarily mean adequate healthcare coverage. Coverage analysis requires population, territorial area, demand, service production and primary care indicators.

## Proposed concatenation logic

```text
UBS registry data
  key: IBGE municipality code

+ IBGE Localidades API
  official municipality name
  UF
  macroregion
  immediate geographic region
  intermediate geographic region

+ SIDRA / IBGE Table 4714
  resident population
  territorial area
  demographic density

= Enriched territorial dataset
  UBS per 10,000 inhabitants
  UBS per 1,000 km²
  coordinate quality by municipality
  state and regional priority views
```

## Data sources

| Source | Use in project | Key |
|---|---|---|
| UBS base | Original establishment-level data | CNES, IBGE municipality code |
| IBGE Localidades API | Municipality, UF and regional hierarchy | IBGE municipality code |
| SIDRA / IBGE Table 4714 | Population, territorial area and demographic density | IBGE municipality code |

## New indicators

| Indicator | Formula | Interpretation |
|---|---|---|
| UBS per 10,000 inhabitants | `(UBS records / resident population) × 10,000` | Population-adjusted availability proxy |
| UBS per 1,000 km² | `(UBS records / territorial area km²) × 1,000` | Territorial density proxy |
| Coordinate validity rate | `valid coordinate records / UBS records` | Data quality readiness for map-based use |
| Missing coordinate records | `UBS records - valid coordinate records` | Registry correction workload |

## Priority matrix concept

The enriched layer enables a portfolio-ready priority matrix:

| Condition | Possible interpretation |
|---|---|
| Low UBS per 10,000 inhabitants | Possible population pressure |
| Low UBS per 1,000 km² | Possible territorial dispersion |
| Low coordinate validity | Data governance priority |
| High population + missing coordinates | High-value correction priority |

These are analytical flags, not final policy conclusions. They indicate where to investigate further.

## Script

The enrichment pipeline is available at:

```text
projects/ubs-healthcare-mapping/scripts/enrich_with_ibge.py
```

Example usage:

```bash
python projects/ubs-healthcare-mapping/scripts/enrich_with_ibge.py \
  --input projects/ubs-healthcare-mapping/data/raw/ubs.csv \
  --output-dir projects/ubs-healthcare-mapping/data/enriched
```

Expected outputs:

```text
municipality_ubs_territory.csv
uf_ubs_territory_summary.csv
priority_matrix.csv
enrichment_metadata.json
```

## Dashboard upgrade idea

The dashboard can be expanded with a new section called **Leitura Territorial Enriquecida**, containing:

1. **UBS per 10,000 inhabitants** — ranking by municipality or state.
2. **UBS per 1,000 km²** — territorial dispersion proxy.
3. **Priority matrix** — cross-tab of population pressure, territorial dispersion and coordinate quality.
4. **Correction simulator** — estimate how coordinate correction improves mapping readiness.

## Limitations

Even after this enrichment, the project should still avoid claiming real healthcare access or adequacy. For that, the analysis would need service production, teams, workload, catchment areas, socioeconomic indicators and APS coverage metrics.
