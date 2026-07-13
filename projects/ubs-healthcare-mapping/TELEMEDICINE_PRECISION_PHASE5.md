# Fase 5 — precisão espacial para telemedicina

Esta fase cria uma camada metodológica para aproximar melhor a pergunta:

> quais municípios combinam muita gente, menor acesso à saúde pública territorial e facilidade relativa de acesso a farmácias?

Ela não substitui a Fase 2 nem a Fase 4. A Fase 2 segue como ranking nacional geodésico municipal; a Fase 4 segue como piloto roteado conservador. A Fase 5 prepara o caminho acadêmico para origens intramunicipais ponderadas por população.

## Status atual

Arquivos principais:

- `data/enriched/telemedicine_population_origins.csv.gz`
- `data/enriched/telemedicine_precision_spatial_access.csv`
- `data/enriched/telemedicine_precision_index.csv`
- `data/enriched/telemedicine_precision_shortlist.csv`
- `data/enriched/telemedicine_precision_metadata.json`

Nesta execução, o Brasil foi processado com setores censitários IBGE 2022: 468.097 setores válidos para 5.570 municípios. Um município novo do universo atual, Boa Esperança do Norte/MT, não aparece na malha/agregado setorial de 2022 e permanece com backfill municipal. Por isso há dois graus de evidência:

- `A_intramunicipal_population_weighted` para 5.570 municípios;
- `B2_municipal_population_proxy` para 1 município em backfill.

Isso é proposital. O pipeline só afirma precisão intramunicipal onde há setores censitários 2022 compatíveis.

## Como evolui para uso acadêmico forte

A entrada preferencial é um CSV local derivado de setores censitários ou grade estatística IBGE 2022, já convertido para pontos representativos:

| Campo | Obrigatório | Observação |
|---|---:|---|
| `origin_id` | sim | identificador único do setor/célula |
| `ibge_municipio_7` | sim | código IBGE municipal de 7 dígitos |
| `origin_latitude` | sim | ponto representativo em graus |
| `origin_longitude` | sim | ponto representativo em graus |
| `origin_population` | sim | população do setor/célula |
| `origin_source` | sim | fonte/produto usado |
| `origin_granularity` | sim | por exemplo `census_sector` ou `statistical_grid` |
| `source_year` | recomendado | deve ser 2022 por padrão |

O script rejeita anos diferentes de 2022, salvo uso explícito de `--allow-non-2022`. Isso evita um fallback silencioso para 2010.

## Métricas publicadas

`telemedicine_precision_spatial_access.csv` traz, por município:

- distância média UBS ponderada por população;
- p50 e p90 da distância até UBS ponderadas por população;
- distância média, p50 e p90 até farmácia OSM;
- proporção da população a mais de 5 km da UBS ativa mais próxima;
- proporção da população a até 2 km de farmácia;
- proporção da população simultaneamente a mais de 5 km da UBS e a até 2 km de farmácia;
- população por UBS ativa, por FTE médico e por farmácia PFPB.

Esses campos também deixam o projeto pronto para uma versão futura com E2SFCA ou modelo gravitacional.

## Índice Fase 5

`telemedicine_precision_index.csv` calcula:

```text
telemedicine_precision_index =
  45% necessidade assistencial
+ 35% descompasso espacial população-ponderado
+ 20% viabilidade
```

O descompasso espacial usa:

```text
45% p90 UBS distante
25% proporção com farmácia <= 2 km
30% proporção simultânea UBS > 5 km e farmácia <= 2 km
```

Todos os componentes espaciais são normalizados por percentil nacional. A agregação usa média geométrica para penalizar municípios que só são fortes em uma dimensão.

## Reproduzir

Sem origens intramunicipais:

```bash
python projects/ubs-healthcare-mapping/scripts/build_telemedicine_population_origins.py
python projects/ubs-healthcare-mapping/scripts/build_telemedicine_precision_spatial_access.py
python projects/ubs-healthcare-mapping/scripts/build_telemedicine_precision_index.py
```

Com origens oficiais IBGE 2022 já preparadas para parte do país:

```bash
python projects/ubs-healthcare-mapping/scripts/build_telemedicine_population_origins.py ^
  --manual-origins caminho/para/origens_ibge_2022.csv ^
  --blend-with-proxy

python projects/ubs-healthcare-mapping/scripts/build_telemedicine_precision_spatial_access.py
python projects/ubs-healthcare-mapping/scripts/build_telemedicine_precision_index.py
```

Para baixar e preparar uma UF a partir das fontes oficiais:

```bash
python projects/ubs-healthcare-mapping/scripts/fetch_ibge_2022_sector_sources.py --download --uf GO

python projects/ubs-healthcare-mapping/scripts/prepare_ibge_2022_sector_origins.py ^
  --sector-shapefile-zip projects/ubs-healthcare-mapping/data/raw/ibge_censo_2022_phase5/GO_setores_CD2022.zip ^
  --basic-aggregate projects/ubs-healthcare-mapping/data/raw/ibge_censo_2022_phase5/Agregados_por_setores_basico_BR_20260520.zip ^
  --output projects/ubs-healthcare-mapping/data/enriched/telemedicine_population_origins_ibge2022_go_sectors.csv
```

Depois:

```bash
python projects/ubs-healthcare-mapping/scripts/build_dashboard_data.py
python projects/ubs-healthcare-mapping/scripts/audit_telemedicine_outputs.py
```

## Fontes recomendadas para a próxima entrada

- Censo Demográfico 2022/IBGE: https://www.ibge.gov.br/estatisticas/sociais/populacao/22827-censo-demografico-2022.html
- Downloads estatísticos IBGE: https://www.ibge.gov.br/estatisticas/downloads-estatisticas.html
- Malhas de Setores Censitários/IBGE: https://www.ibge.gov.br/geociencias/organizacao-do-territorio/malhas-territoriais/26565-malhas-de-setores-censitarios-divisoes-intramunicipais.html

## Limites

- A execução atual ainda é geodésica, não tempo de viagem.
- Farmácias OSM têm completude heterogênea.
- Farmácia Popular municipal não comprova estoque, sala privada ou disponibilidade operacional.
- Resultados devem ser usados em geografia agregada; não há segmentação individual de pacientes.
- Para pré-paper, a versão A deve combinar origens IBGE 2022 intramunicipais e OSRM local versionado.
