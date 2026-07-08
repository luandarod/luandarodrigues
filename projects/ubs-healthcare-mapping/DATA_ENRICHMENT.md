# Enriquecimento UBS, IBGE/SIDRA e APS

Esta nota explica a parte técnica do projeto. Ela existe porque o ponto mais importante da análise não é o gráfico final, e sim a forma como bases com chaves, períodos e significados diferentes foram colocadas na mesma mesa.

## Chave municipal

O cadastro UBS e a Cobertura APS usam o código municipal IBGE com 6 dígitos. A API Localidades do IBGE e a tabela SIDRA 4714 usam o código oficial com 7 dígitos.

O pipeline mantém os dois formatos:

```text
ibge_municipio   = código de 6 dígitos usado no join com UBS e APS
ibge_municipio_7 = código oficial de 7 dígitos usado pelo IBGE/SIDRA
```

O join territorial é feito com `ibge_municipio`. Para dados vindos do IBGE/SIDRA, o código de 7 dígitos é convertido para 6 dígitos com divisão inteira por 10.

## Camadas

| Camada | Arquivo ou API | Chave | Saída principal |
|---|---|---|---|
| UBS | `data/Unidades_Basicas_Saude-UBS.csv` | `ibge_municipio` | contagem, UF, região, coordenadas |
| IBGE Localidades | `servicodados.ibge.gov.br` | `ibge_municipio_7` | município, UF e região |
| SIDRA 4714 | `apisidra.ibge.gov.br` | `ibge_municipio_7` | população, área e densidade |
| Cobertura APS | `data/cobertura-aps-latest.csv` | `ibge_municipio` | equipes, população, capacidade e cobertura |

## Atualização da APS

A base APS recente pode ser buscada pelo script:

```bash
python projects/ubs-healthcare-mapping/scripts/fetch_latest_aps_coverage.py
```

Na revisão de 2026-07-07, o endpoint público retornou a competência `04/2026`. O script grava:

```text
data/cobertura-aps-latest.csv
data/aps_api_metadata.json
```

O arquivo antigo `data/cobertura-aps-geral.xlsx` foi mantido como insumo manual de referência, mas o pipeline atual usa a extração oficial mais recente.

Além da competência mais recente, o projeto também salva uma série nacional:

```bash
python projects/ubs-healthcare-mapping/scripts/fetch_aps_national_timeseries.py
```

Essa saída reduz o risco de interpretar a APS como uma foto isolada.

## Indicadores territoriais

| Indicador | Fórmula | Leitura |
|---|---|---|
| UBS por 10 mil habitantes | `ubs_records / populacao_residente * 10.000` | disponibilidade relativa por população |
| UBS por 1.000 km² | `ubs_records / area_km2 * 1.000` | densidade territorial de unidades registradas |
| Validade de coordenadas | `valid_coordinate_records / ubs_records * 100` | prontidão básica para uso em mapa |
| Registros sem coordenada válida | `ubs_records - valid_coordinate_records` | trabalho de correção cadastral |

## Indicadores APS

A Cobertura APS pode passar de 100%. O projeto não apaga esse excesso, porque ele pode indicar capacidade nominal acima da população de referência. Ao mesmo tempo, ele não deve ser lido como acesso real.

Por isso foram criadas quatro leituras:

| Campo | Interpretação |
|---|---|
| `cobertura_aps_pct` | cobertura nominal do arquivo de origem |
| `cobertura_aps_capped_pct` | cobertura limitada a 100% para leitura populacional |
| `coverage_gap_pct` | gap positivo abaixo de 100% |
| `nominal_capacity_excess_pct` | excesso nominal acima de 100% |

A síntese por UF também inclui `cobertura_aps_ponderada_pct`, calculada como `sum(aps_capacidade_equipe) / sum(aps_populacao) * 100`. Essa medida é mais adequada do que a média simples municipal quando os municípios têm populações muito diferentes.

## Sensibilidade do score

O score exploratório é calculado com pesos. Para não tratar esses pesos como verdade fixa, o projeto gera `priority_sensitivity_uf_scores.csv` com quatro cenários:

| Cenário | Ideia |
|---|---|
| `base` | equilíbrio usado no dashboard |
| `coverage_led` | dá mais peso ao gap de cobertura APS |
| `territory_led` | dá mais peso à dispersão territorial |
| `data_quality_led` | dá mais peso à qualidade cadastral |

Essa etapa ajuda a separar sinais estáveis de resultados que dependem demais da escolha dos pesos.

## Saídas

```text
data/enriched/
├── aps_coverage_normalized.csv
├── aps_enrichment_metadata.json
├── enrichment_metadata.json
├── municipality_ubs_aps_coverage.csv
├── municipality_ubs_territory.csv
├── priority_matrix.csv
├── priority_sensitivity_uf_scores.csv
├── region_ubs_territory_summary.csv
├── uf_ubs_aps_coverage_summary.csv
└── uf_ubs_territory_summary.csv
```

## Validações adicionadas

- leitura de CSV com separador `;`, `,` ou tabulação;
- normalização de latitude e longitude com vírgula decimal;
- preservação de números decimais do SIDRA, como `164173.431`;
- leitura do formato retornado pelo endpoint público da APS;
- série nacional APS para reduzir leitura de competência isolada;
- auditoria de coordenadas por UF, separando ausentes, fora do bounding box e repetidas;
- manifesto de lineage com linhas, colunas, tamanho e SHA-256;
- join IBGE/SIDRA com conversão 7 dígitos para 6 dígitos;
- exclusão de linhas sem UF da síntese por UF;
- teste para garantir 27 UFs na saída territorial;
- teste para garantir cobertura APS ponderada e capada.

## Limites metodológicos

Este enriquecimento organiza sinais, não fecha diagnóstico. A análise ainda precisa de produção assistencial, equipe ativa, demanda, deslocamento, vulnerabilidade social e validação local para sustentar decisão de política pública.
