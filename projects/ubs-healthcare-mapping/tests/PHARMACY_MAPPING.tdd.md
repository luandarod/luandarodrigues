# Evidencia TDD: camada Farmacia Popular

## Jornada

Como pessoa pesquisadora, quero transformar um extrato oficial do Farmacia Popular em dados espaciais versionados para comparar acesso potencial a medicamentos com a rede de UBS.

## Evidencia

| Garantia | Teste | Tipo | Resultado |
|---|---|---|---|
| Variantes de colunas oficiais sao normalizadas | `test_normalizes_official_portuguese_columns_and_coordinates` | unitario | PASS |
| Coordenadas fora do Brasil nao entram no mapa | `test_rejects_coordinates_outside_brazil` | unitario | PASS |
| O agregado por UF e o GeoJSON refletem somente pontos validos | `test_builds_uf_summary_and_geojson_with_only_valid_points` | integracao | PASS |
| CSV, resumo e GeoJSON sao gravados para publicacao | `test_writes_versioned_dashboard_artifacts` | integracao | PASS |
| Municipios sem farmacias permanecem no universo analisado | `test_calculates_supply_rates_and_keeps_zero_pharmacy_municipalities` | unitario | PASS |
| Baixa oferta de UBS ativas, APS abaixo de 80% e farmacias acima da mediana geram sinal consistente | `test_flags_low_ubs_high_pharmacy_access_mismatch` | unitario | PASS |
| Farmacias populares e demais farmacias permanecem separadas | `test_separates_popular_and_other_pharmacies` | unitario | PASS |
| CNPJs repetidos sao contados apenas uma vez | `test_deduplicates_pharmacies_by_cnpj` | unitario | PASS |
| Goiania permanece com 345 linhas e 345 CNPJs unicos na fonte oficial | `test_real_goiania_source_counts_are_stable` | regressao | PASS |
| GeoJSON publica as dimensoes que explicam a classificacao | `test_builds_geojson_with_access_gap_properties` | integracao | PASS |

RED: `python -m unittest projects/ubs-healthcare-mapping/tests/test_pharmacy_mapping.py` falhou com quatro erros porque `build_pharmacy_layer.py` ainda nao existia.

GREEN: `python -m unittest discover -s projects/ubs-healthcare-mapping/tests` passou com 19 testes.

## Lacunas conhecidas

O teste usa fixtures sinteticas e nao substitui uma validacao de contrato contra cada novo extrato oficial. A validacao point-in-polygon municipal deve ser aplicada depois que o arquivo oficial e sua competencia forem definidos.
