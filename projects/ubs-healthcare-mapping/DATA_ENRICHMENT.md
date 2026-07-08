# Enriquecimento UBS, IBGE/SIDRA, APS e malhas municipais

Esta nota explica a parte tecnica do projeto. O ponto mais importante nao e o grafico final, e sim a forma como bases com chaves, periodos e significados diferentes foram colocadas na mesma mesa.

## Chave municipal

O cadastro UBS e a Cobertura APS usam o codigo municipal IBGE com 6 digitos. A API Localidades, a tabela SIDRA 4714 e a API de Malhas usam o codigo oficial de 7 digitos.

O pipeline mantem os dois formatos:

```text
ibge_municipio   = codigo de 6 digitos usado no join com UBS e APS
ibge_municipio_7 = codigo oficial de 7 digitos usado por IBGE/SIDRA/Malhas
```

Para dados vindos do IBGE/SIDRA, o codigo de 7 digitos e convertido para 6 digitos com divisao inteira por 10 quando necessario.

## Camadas

| Camada | Arquivo ou API | Chave | Saida principal |
|---|---|---|---|
| UBS | `data/Unidades_Basicas_Saude-UBS.csv` | `ibge_municipio` | contagem, UF, regiao, coordenadas |
| IBGE Localidades | `servicodados.ibge.gov.br` | `ibge_municipio_7` | municipio, UF e regiao |
| IBGE Malhas | `servicodados.ibge.gov.br/api/v3/malhas` | `ibge_municipio_7` | poligonos municipais simplificados |
| SIDRA 4714 | `apisidra.ibge.gov.br` | `ibge_municipio_7` | populacao, area e densidade |
| Cobertura APS | `data/cobertura-aps-latest.csv` | `ibge_municipio` | equipes, populacao, capacidade e cobertura |
| CNES/ST | FTP DATASUS/CNES | `CNES` | presenca cadastral no arquivo mensal mais recente |
| SIA/SUS PA | FTP DATASUS/SIASUS | `PA_CODUNI` | producao ambulatorial recente por CNES |

## Atualizacao da APS

A base APS recente pode ser buscada pelo script:

```bash
python projects/ubs-healthcare-mapping/scripts/fetch_latest_aps_coverage.py
```

Na revisao atual, o endpoint publico retornou a competencia `04/2026`. O script grava:

```text
data/cobertura-aps-latest.csv
data/aps_api_metadata.json
```

Alem da competencia mais recente, o projeto salva uma serie nacional:

```bash
python projects/ubs-healthcare-mapping/scripts/fetch_aps_national_timeseries.py
```

Essa saida reduz o risco de interpretar a APS como uma foto isolada.

## Indicadores territoriais

| Indicador | Formula | Leitura |
|---|---|---|
| UBS por 10 mil habitantes | `ubs_records / populacao_residente * 10.000` | disponibilidade relativa por populacao |
| UBS por 1.000 km2 | `ubs_records / area_km2 * 1.000` | densidade territorial de unidades registradas |
| Validade de coordenadas | `valid_coordinate_records / ubs_records * 100` | prontidao basica para uso em mapa |
| Consistencia municipal | UBS dentro do poligono do municipio declarado | qualidade espacial do cadastro |

## Validacao espacial municipal

O script `validate_ubs_municipal_geometry.py` baixa malhas municipais simplificadas do IBGE por UF, usando `intrarregiao=municipio`, e testa cada UBS com coordenada completa contra o poligono do municipio declarado.

Saidas geradas:

```text
data/geodata/ibge_malhas_municipais_minima.json
data/spatial_validation_by_uf.csv
data/spatial_validation_suspect_ubs.csv
data/spatial_validation_metadata.json
```

O teste separa cinco situacoes:

- `inside_declared_municipality`
- `outside_declared_municipality`
- `missing_coordinates`
- `outside_brazil_bbox`
- `missing_municipal_polygon`

Resultado atual:

| Status | Registros |
|---|---:|
| Dentro do municipio declarado | 43.717 |
| Fora do municipio declarado | 2.062 |
| Sem coordenada completa | 1.929 |
| Fora do bounding box do Brasil | 3 |
| Sem poligono municipal correspondente | 3 |

Essa etapa melhora a analise porque uma coordenada pode estar dentro do Brasil e, ainda assim, fora do municipio informado. Como a malha usada e simplificada, os registros fora do poligono devem ser lidos como suspeitos para revisao, nao como erro definitivo.

## Indicadores APS

A Cobertura APS pode passar de 100%. O projeto nao apaga esse excesso, porque ele pode indicar capacidade nominal acima da populacao de referencia. Ao mesmo tempo, ele nao deve ser lido como acesso real.

Por isso foram criadas quatro leituras:

| Campo | Interpretacao |
|---|---|
| `cobertura_aps_pct` | cobertura nominal do arquivo de origem |
| `cobertura_aps_capped_pct` | cobertura limitada a 100% para leitura populacional |
| `coverage_gap_pct` | gap positivo abaixo de 100% |
| `nominal_capacity_excess_pct` | excesso nominal acima de 100% |

A sintese por UF tambem inclui `cobertura_aps_ponderada_pct`, calculada como `sum(aps_capacidade_equipe) / sum(aps_populacao) * 100`. Essa medida e mais adequada do que a media simples municipal quando os municipios tem populacoes muito diferentes.

## Sensibilidade do score

O score exploratorio e calculado com pesos. Para nao tratar esses pesos como verdade fixa, o projeto gera `priority_sensitivity_uf_scores.csv` com quatro cenarios:

| Cenario | Ideia |
|---|---|
| `base` | equilibrio usado no dashboard |
| `coverage_led` | da mais peso ao gap de cobertura APS |
| `territory_led` | da mais peso a dispersao territorial |
| `data_quality_led` | da mais peso a qualidade cadastral |

Essa etapa ajuda a separar sinais estaveis de resultados que dependem demais da escolha dos pesos.

## Proxy operacional CNES + SIA/SUS

O script `fetch_ubs_operational_status.py` cruza o CNES de cada UBS do projeto com duas bases do DATASUS:

- CNES/ST mais recente: se o CNES aparece nesse arquivo, o projeto marca `cnes_present_latest_st = True`.
- SIA/SUS PA mais recente: se o CNES aparece com producao ambulatorial, o projeto marca `sia_recent_production = True` e agrega quantidade, valor e numero de registros.

Saidas:

```text
data/ubs_operational_status.csv
data/ubs_operational_status_by_uf.csv
data/ubs_operational_status_metadata.json
```

O campo `operational_status` usa quatro categorias:

- `cadastral_active_with_recent_sia_production`
- `cadastral_active_without_recent_sia_production`
- `not_in_latest_cnes_st_but_has_recent_sia_production`
- `registered_only_no_current_cnes_or_sia_signal`

Resultado atual:

| Indicador | Registros |
|---|---:|
| UBS do cadastro do projeto | 47.714 |
| Presentes no CNES/ST mais recente | 43.578 |
| Com producao SIA/PA recente | 7.145 |
| Com CNES/ST e producao SIA/PA recente | 7.144 |

Essa e uma proxy operacional conservadora. SIA/SUS PA e registro de producao/faturamento, nao prova de funcionamento completo. A ausencia de producao em uma competencia pode refletir atraso, regra local de registro, producao consolidada em outro CNES ou servicos que nao entram nessa leitura.

## Saidas

```text
data/enriched/
|-- aps_coverage_normalized.csv
|-- aps_enrichment_metadata.json
|-- enrichment_metadata.json
|-- municipality_ubs_aps_coverage.csv
|-- municipality_ubs_territory.csv
|-- priority_matrix.csv
|-- priority_sensitivity_uf_scores.csv
|-- region_ubs_territory_summary.csv
|-- uf_ubs_aps_coverage_summary.csv
`-- uf_ubs_territory_summary.csv
```

## Validacoes adicionadas

- leitura de CSV com separador `;`, `,` ou tabulacao;
- normalizacao de latitude e longitude com virgula decimal;
- preservacao de numeros decimais do SIDRA, como `164173.431`;
- leitura do formato retornado pelo endpoint publico da APS;
- serie nacional APS para reduzir leitura de competencia isolada;
- auditoria de coordenadas por UF, separando ausentes, fora do bounding box e repetidas;
- validacao point-in-polygon contra malhas municipais do IBGE;
- proxy operacional com CNES/ST e SIA/SUS PA;
- manifesto de lineage com linhas, colunas, tamanho e SHA-256;
- join IBGE/SIDRA com conversao 7 digitos para 6 digitos;
- exclusao de linhas sem UF da sintese por UF;
- testes para garantir 27 UFs nas saidas principais.

## Limites metodologicos

Este enriquecimento organiza sinais, nao fecha diagnostico. A analise ainda precisa de producao assistencial, equipe ativa, demanda, deslocamento, vulnerabilidade social e validacao local para sustentar decisao de politica publica.
