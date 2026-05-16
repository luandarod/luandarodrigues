# Mapping Primary Healthcare Units in Brazil

**Health Analytics | Geomapping | Data Quality | Public Health BI**

This project analyzes a public dataset of Brazilian Primary Healthcare Units (UBS) to map geographic distribution, evaluate coordinate quality and identify data governance opportunities for public health planning.

## Interactive dashboard

A static interactive dashboard is available through GitHub Pages:

**[Open the UBS Healthcare Mapping Dashboard →](https://luandarodrigues.github.io/luandarodrigues/dashboards/ubs-healthcare-mapping/)**

The dashboard works as a portfolio presentation layer for the analysis, with KPI cards, regional filters, state-level rankings, data quality indicators and interpretation notes.

## Business and public health question

How can geographic and cadastral data from primary healthcare units be transformed into useful intelligence for territorial planning, BI dashboards and data quality monitoring?

## Dataset

The dataset contains identification and location fields for UBS records:

- CNES establishment code
- State code
- Municipality IBGE code
- Establishment name
- Address and neighborhood
- Latitude and longitude

The raw UBS file is currently stored at:

```text
projects/ubs-healthcare-mapping/data/Unidades_Basicas_Saude-UBS.csv
```

The APS coverage file is currently stored at:

```text
projects/ubs-healthcare-mapping/data/cobertura-aps-geral.xlsx
```

## Key numbers

| Metric | Value |
|---|---:|
| Total UBS records | 47,714 |
| Unique CNES records | 47,714 |
| States represented | 27 |
| Unique municipalities | 5,483 |
| Records with valid coordinates | 45,785 |
| Records without complete coordinates | 1,929 |
| Records with repeated coordinates | 3,182 |

## Distribution by region

| Region | UBS records | Share |
|---|---:|---:|
| Northeast | 18,125 | 38.0% |
| Southeast | 15,274 | 32.0% |
| South | 6,764 | 14.2% |
| North | 3,971 | 8.3% |
| Center-West | 3,580 | 7.5% |

## Top states by number of UBS records

| State | Region | UBS records |
|---|---|---:|
| MG | Southeast | 6,137 |
| SP | Southeast | 5,824 |
| BA | Northeast | 4,449 |
| PE | Northeast | 3,012 |
| CE | Northeast | 2,492 |

## Main insights

- The dataset has strong national coverage, with all 27 Brazilian federative units represented.
- Around 96% of records have usable geographic coordinates, which makes the base suitable for mapping.
- Missing latitude/longitude values and repeated coordinates are relevant data quality flags.
- The Northeast and Southeast concentrate the largest number of UBS records in the dataset.
- The IBGE enrichment makes it possible to compare UBS volume against population and territorial area.
- The APS coverage layer can support a stronger interpretation of installed capacity and potential primary care coverage.
- The analysis describes distribution and analytical signals, not definitive healthcare access or adequacy.

## Methodology

1. Data dictionary validation
2. CSV ingestion and field standardization
3. Missing coordinate analysis
4. Classification of states by Brazilian region
5. Aggregation by region, state and municipality
6. Geolocation quality assessment
7. IBGE/SIDRA enrichment for population and territorial analysis
8. APS potential coverage enrichment
9. Preparation of outputs for dashboard and portfolio presentation

## Enrichment pipeline

The raw UBS file can be enriched with IBGE territory data using:

```bash
python projects/ubs-healthcare-mapping/scripts/enrich_with_ibge.py \
  --input projects/ubs-healthcare-mapping/data/Unidades_Basicas_Saude-UBS.csv \
  --output-dir projects/ubs-healthcare-mapping/data/enriched
```

After generating `municipality_ubs_territory.csv`, the APS coverage file can be joined using:

```bash
python projects/ubs-healthcare-mapping/scripts/enrich_with_aps_coverage.py \
  --ubs-territory projects/ubs-healthcare-mapping/data/enriched/municipality_ubs_territory.csv \
  --aps-file projects/ubs-healthcare-mapping/data/cobertura-aps-geral.xlsx \
  --output-dir projects/ubs-healthcare-mapping/data/enriched
```

Expected enriched outputs:

```text
projects/ubs-healthcare-mapping/data/enriched/
├── municipality_ubs_territory.csv
├── uf_ubs_territory_summary.csv
├── priority_matrix.csv
├── aps_coverage_normalized.csv
├── municipality_ubs_aps_coverage.csv
├── uf_ubs_aps_coverage_summary.csv
├── enrichment_metadata.json
└── aps_enrichment_metadata.json
```

## Files in this project

```text
projects/ubs-healthcare-mapping/
├── README.md
├── DATA_ENRICHMENT.md
├── data/
│   ├── Unidades_Basicas_Saude-UBS.csv
│   ├── cobertura-aps-geral.xlsx
│   ├── data_quality_summary.csv
│   ├── region_distribution.csv
│   ├── state_distribution.csv
│   └── enriched/
│       ├── municipality_ubs_territory.csv
│       ├── uf_ubs_territory_summary.csv
│       ├── priority_matrix.csv
│       ├── aps_coverage_normalized.csv
│       ├── municipality_ubs_aps_coverage.csv
│       ├── uf_ubs_aps_coverage_summary.csv
│       ├── enrichment_metadata.json
│       └── aps_enrichment_metadata.json
└── scripts/
    ├── analyze_ubs.py
    ├── enrich_with_ibge.py
    └── enrich_with_aps_coverage.py
```

## Tools

Python, Pandas, Folium, Matplotlib, CSV, Geolocation, Data Quality, Health Analytics, IBGE APIs, SIDRA, APS Coverage, Territorial Intelligence.

## Limitations

This project does not infer definitive access to care, demand, productivity or adequacy of healthcare coverage. To answer those questions, the dataset should also be enriched with service production, teams, workload, catchment areas, socioeconomic indicators and official APS coverage metrics by period.
