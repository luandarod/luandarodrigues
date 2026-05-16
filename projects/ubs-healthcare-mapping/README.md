# Mapping Primary Healthcare Units in Brazil

**Health Analytics | Geomapping | Data Quality | Public Health BI**

This project analyzes a public dataset of Brazilian Primary Healthcare Units (UBS) to map geographic distribution, evaluate coordinate quality and identify data governance opportunities for public health planning.

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
- The analysis describes the distribution of registered units, not healthcare coverage. Coverage analysis would require population, demand, catchment area and service production data.

## Methodology

1. Data dictionary validation
2. CSV ingestion and field standardization
3. Missing coordinate analysis
4. Classification of states by Brazilian region
5. Aggregation by region, state and municipality
6. Geolocation quality assessment
7. Preparation of outputs for dashboard and portfolio presentation

## Files in this project

```text
projects/ubs-healthcare-mapping/
├── README.md
├── data/
│   ├── data_quality_summary.csv
│   ├── region_distribution.csv
│   ├── state_distribution.csv
│   └── top_municipalities_by_ubs.csv
└── scripts/
    └── analyze_ubs.py
```

## Tools

Python, Pandas, Folium, Matplotlib, CSV, Geolocation, Data Quality, Health Analytics.

## Limitations

This project does not infer access to care, demand, productivity or adequacy of healthcare coverage. To answer those questions, the dataset should be enriched with population by municipality, socioeconomic indicators, primary care coverage and service production data.
