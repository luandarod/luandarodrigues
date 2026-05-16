# UBS + IBGE + Cobertura Potencial APS

**Health Analytics | Territorial Intelligence | Data Quality | Public Health BI | Interactive Dashboard**

This is the main healthcare analytics project in my portfolio. It transforms a public registry of Brazilian Primary Healthcare Units (UBS) into an integrated territorial intelligence dashboard by combining three layers of data: physical UBS presence, IBGE/SIDRA population and territory indicators, and potential Primary Care coverage capacity.

## Interactive dashboard

**[Open the interactive dashboard →](https://luandarodrigues.github.io/luandarodrigues/dashboards/ubs-healthcare-mapping/?v=aps2)**

The dashboard works as the presentation layer of the project. It was built as a static, open-access GitHub Pages dashboard using HTML, CSS and JavaScript, with data prepared in Python.

It includes:

- executive KPI cards;
- UBS distribution by state and region;
- comparison between UBS volume, population and territorial area;
- coordinate quality indicators;
- APS potential coverage indicators;
- ranking of municipalities by lower or higher APS coverage;
- state-level integrated table;
- priority signals for territorial investigation;
- source explanation and analytical conclusion.

## Analytical question

Counting UBS is not enough to understand primary care capacity. A state may have many registered units and still face population pressure, geographic dispersion or gaps between physical presence and installed team capacity.

This project asks:

> What changes when the physical registry of UBS is analyzed together with population, territory and potential APS coverage?

## Data sources

| Layer | Source | Analytical role |
|---|---|---|
| UBS registry | Public UBS dataset | Physical presence of primary healthcare units, CNES, municipality, UF and coordinates |
| IBGE/SIDRA | Municipality-level population and territorial area | Population-adjusted and territory-adjusted indicators |
| Cobertura Potencial APS | APS potential coverage report | Installed team capacity and potential primary care coverage |

The raw files are stored at:

```text
projects/ubs-healthcare-mapping/data/Unidades_Basicas_Saude-UBS.csv
projects/ubs-healthcare-mapping/data/cobertura-aps-geral.xlsx
```

The enriched outputs are stored at:

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

## Key numbers

| Metric | Value |
|---|---:|
| Total UBS records | 47,714 |
| Unique CNES records | 47,714 |
| States represented | 27 |
| Municipalities represented | 5,483 |
| Records with valid coordinates | ~96% |
| APS population in coverage file | ~210.4 million |
| Estimated APS team capacity | ~180.3 million |

## Dashboard interpretation

The dashboard separates the analysis into three complementary views.

First, the UBS registry shows the **physical presence of the network**. It helps answer where units are registered and whether their coordinates are usable for map-based analysis.

Second, the IBGE/SIDRA enrichment adds **population and territorial context**. This makes it possible to compare states not only by number of units, but also by UBS per population and UBS per territorial area.

Third, the APS coverage layer adds **installed capacity signals**. It estimates how many people can potentially be covered by primary care teams in each municipality.

Together, these layers create a more responsible reading: the project does not claim real access to care, but it shows where further investigation may be needed.

## Main insights

- The dataset has national coverage, with all 27 Brazilian federative units represented.
- Around 96% of records have usable geographic coordinates, making the base suitable for mapping.
- The Northeast and Southeast concentrate the largest number of UBS records.
- Volume of UBS alone does not explain sufficiency, capacity or access.
- IBGE/SIDRA enrichment allows population- and area-adjusted analysis.
- APS coverage data helps separate physical units from potential care capacity.
- Some indicators should be interpreted as prioritization signals, not definitive conclusions.

## Methodology

1. Data dictionary validation
2. CSV ingestion and field standardization
3. Coordinate cleaning and geolocation quality assessment
4. Aggregation by municipality, state and region
5. IBGE/SIDRA enrichment for population and territorial analysis
6. APS coverage normalization and municipality-level integration
7. Construction of enriched analytical outputs
8. Static interactive dashboard development for GitHub Pages
9. Interpretation with explicit limitations

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

## Files in this project

```text
projects/ubs-healthcare-mapping/
├── README.md
├── DATA_ENRICHMENT.md
├── requirements.txt
├── data/
│   ├── Unidades_Basicas_Saude-UBS.csv
│   ├── cobertura-aps-geral.xlsx
│   ├── data_quality_summary.csv
│   ├── region_distribution.csv
│   ├── state_distribution.csv
│   └── enriched/
└── scripts/
    ├── analyze_ubs.py
    ├── enrich_with_ibge.py
    └── enrich_with_aps_coverage.py
```

Dashboard file:

```text
docs/dashboards/ubs-healthcare-mapping/index.html
```

## Tools

Python, Pandas, Requests, OpenPyXL, CSV, IBGE APIs, SIDRA, GitHub Pages, HTML, CSS, JavaScript, Data Quality, Health Analytics, Territorial Intelligence.

## Limitations

This dashboard does not measure real access to care, quality of care, service productivity or adequacy of primary care coverage. It organizes analytical signals from public datasets to support better questions and prioritize further investigation.

A stronger next version would include service production, active teams by period, socioeconomic indicators, catchment areas, distance to services and time-series coverage analysis.
