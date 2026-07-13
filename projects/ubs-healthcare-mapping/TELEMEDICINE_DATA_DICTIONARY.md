# Dicionário do dado analítico de telemedicina

Arquivo principal: `data/enriched/telemedicine_pre_paper_analytic.csv`.

## Identificação e cobertura

| Campo | Definição |
|---|---|
| `ibge_municipio` | código municipal de seis dígitos usado nas integrações |
| `ibge_municipio_7` | código oficial IBGE de sete dígitos |
| `municipio_nome_ibge` | nome oficial ou nome integrado validado |
| `uf_sigla` | unidade federativa |
| `regiao_nome_oficial` | macrorregião IBGE |
| `universe_status` | `matched_source` ou `missing_source_record` |
| `academic_eligibility` | elegibilidade para cálculo: proxy elegível, ausência de PFPB ou dados insuficientes |
| `evidence_grade` | `B_proxy_only` ou `C_incomplete`; grau A é reservado para dados espaciais e operacionais validados |

## Variáveis observadas

| Campo | Unidade | Interpretação |
|---|---:|---|
| `populacao_residente` | pessoas | população integrada do IBGE |
| `aps_coverage_capped_pct` | % | cobertura potencial APS truncada em 100% |
| `ubs_records` | estabelecimentos | UBS cadastradas na fonte-base |
| `active_ubs` | estabelecimentos | UBS presentes no CNES/ST recente |
| `active_ubs_per_100k` | por 100 mil | oferta cadastral recente relativa |
| `pharmacies` | CNPJs | estabelecimentos únicos credenciados no PFPB |
| `pharmacies_per_100k` | por 100 mil | densidade municipal PFPB |

## Variáveis derivadas

| Campo | Escala | Interpretação |
|---|---:|---|
| `aps_relative_gap` | 0–1 | complemento da cobertura potencial truncada |
| `potentially_uncovered_population` | pessoas | estimativa ecológica, não contagem observada |
| `uncovered_volume_percentile` | 0–1 | percentil nacional do volume com transformação logarítmica |
| `aps_gap_percentile` | 0–1 | percentil nacional do gap relativo |
| `active_ubs_scarcity_percentile` | 0–1 | percentil inverso de UBS recentes por 100 mil |
| `pharmacy_count_percentile` | 0–1 | percentil da quantidade absoluta PFPB |
| `pharmacy_density_percentile` | 0–1 | percentil de PFPB por 100 mil |
| `need_score` | 0–100 | eixo de necessidade potencial |
| `pharmacy_launchability_score` | 0–100 | proxy de capilaridade municipal; não mede prontidão real |

## Cenários e incerteza

| Campo | Interpretação |
|---|---|
| `telemedicine_opportunity_balanced` | necessidade 50% e capilaridade 50% |
| `telemedicine_opportunity_equity_led` | necessidade 70% e capilaridade 30% |
| `telemedicine_opportunity_deployment_led` | necessidade 40% e capilaridade 60% |
| `rank_*` | posição entre municípios elegíveis no cenário indicado |
| `rank_best`, `rank_worst`, `rank_range` | estabilidade nos três cenários fixos |
| `mc_score_median`, `mc_score_p05`, `mc_score_p95` | distribuição da pontuação em 1.000 simulações |
| `mc_rank_median`, `mc_rank_p05`, `mc_rank_p95` | distribuição da posição nas simulações |
| `mc_probability_top_decile` | proporção das simulações no primeiro decil |

## Segmentação territorial

| Valor | Uso permitido |
|---|---|
| `pilot_candidate` | investigar município com alta necessidade e alta capilaridade relativas |
| `high_need_build_supply` | alta necessidade, mas capilaridade inferior; requer parceiros ou outro canal |
| `launchable_secondary` | boa capilaridade, menor prioridade de necessidade |
| `monitor` | fora dos quadrantes superiores nesta versão |
| `infrastructure_gap` | nenhuma Farmácia Popular observada; não é alvo de implantação farmacêutica imediata |
| `insufficient_data` | não pontuar nem interpretar |

Os status `spatial_access_status`, `digital_readiness_status` e `clinical_demand_status` permanecem `not_measured` para impedir que essas dimensões sejam inferidas indevidamente.

## Extensão Fase 1 v1

Arquivo: `data/enriched/telemedicine_opportunity_phase1.csv`.

| Campo | Unidade | Interpretação |
|---|---:|---|
| `physician_fte_per_100k` | FTE 40h/100 mil | carga ambulatorial médica cadastrada no CNES, não presença observada |
| `households_with_internet_pct` | % | domicílios com internet no Censo 2022 |
| `mobile_4g5g_resident_coverage_pct` | % | moradores estimados cobertos pela união 4G/5G da Anatel |
| `fixed_broadband_accesses_per_100_people` | acessos/100 | densidade de acessos fixos; pode superar 100 |
| `phase1_need_score` | 0–100 | necessidade potencial com escassez de médico FTE |
| `digital_readiness_score` | 0–100 | prontidão digital municipal relativa, não prontidão da farmácia |
| `phase1_pharmacy_launchability_score` | 0–100 | capilaridade PFPB recalculada no universo completo da Fase 1 |
| `phase1_deployment_feasibility_score` | 0–100 | farmácias 70% e prontidão digital 30% |
| `telemedicine_phase1_*` | 0–100 | cenários equilibrado, equidade e implantação |
| `phase1_rank_*` | posição | posição somente entre elegíveis |
| `phase1_eligibility` | categoria | elegível, sem PFPB ou dados insuficientes |
| `sia_score_role` | categoria | sempre `audit_only_not_scored` nesta versão |
| `spatial_travel_time_status` | categoria | `not_measured` até a Fase 2 |

Ausências em profissional, internet ou conectividade não são imputadas como zero. Os campos SIA permanecem na base somente para verificação operacional.

## Extensão Fase 2 geodésica

Arquivo: `data/enriched/telemedicine_opportunity_phase2.csv`.

| Campo | Unidade | Interpretação |
|---|---:|---|
| `origin_latitude`, `origin_longitude` | graus | sede municipal oficial do IBGE 2022 |
| `nearest_ubs_geodesic_km` | km | linha geodésica até UBS ativa auditada mais próxima |
| `nearest_pharmacy_geodesic_km` | km | linha geodésica até farmácia OSM mais próxima |
| `hard_ubs_easy_pharmacy_flag` | booleano | regra conservadora UBS ≥5 km, farmácia ≤2 km e PFPB presente |
| `hard_ubs_easy_pharmacy_flag_3km_2km` | booleano | sensibilidade mais inclusiva |
| `hard_ubs_easy_pharmacy_flag_10km_5km` | booleano | sensibilidade territorial alternativa |
| `phase2_spatial_mismatch_score` | 0–100 | combinação relativa de barreira UBS e facilidade farmacêutica |
| `telemedicine_phase2_*` | 0–100 | cenários com necessidade, espaço e viabilidade |
| `phase2_spatial_target_rank` | posição | somente municípios 5/2 km com necessidade positiva |
| `travel_time_status` | categoria | `not_measured_geodesic_only` |

`nearest_*_geodesic_km` não é distância rodoviária, tempo de carro, caminhada ou transporte público.

## Extensão Fase 3 - roteamento

Arquivos:

- `data/enriched/telemedicine_phase3_routing_od_matrix.csv`;
- `data/enriched/telemedicine_phase3_routing_od_matrix_routed.csv`;
- `data/enriched/telemedicine_phase3_routing_summary.csv`.

| Campo | Unidade | Interpretação |
|---|---:|---|
| `od_pair_id` | identificador | par origem-destino único |
| `destination_type` | categoria | `active_ubs` ou `osm_pharmacy` |
| `destination_id` | identificador | CNES da UBS ou ID da feição OSM |
| `destination_latitude`, `destination_longitude` | graus | coordenada do destino usado no roteamento |
| `phase2_geodesic_km` | km | distância de linha geodésica herdada da Fase 2 |
| `routing_profile` | categoria | perfil planejado, inicialmente `driving` |
| `routing_readiness_status` | categoria | `ready_for_network_routing`, `missing_coordinate_for_routing` ou `routed` |
| `travel_time_minutes` | minutos | tempo de rota quando `routing_readiness_status = routed` |
| `network_distance_km` | km | distância viária quando `routing_readiness_status = routed` |
| `routing_source` | texto | endpoint ou motor usado no roteamento |
| `routing_measured_at_utc` | timestamp | momento da medição de rota |
| `academic_interpretation` | categoria | `phase3_od_pair_pending_travel_time` ou `phase3_network_travel_time_proxy` |
| `phase3_routed_hard_ubs_easy_pharmacy_flag` | booleano | UBS >= 15 min e farmácia <= 5 min na síntese municipal |
| `phase3_access_interpretation` | categoria | leitura roteada municipal |

Na execução atual, o roteamento usa OSRM público e perfil `driving`; deve ser tratado como proxy exploratória até rerodagem local versionada.

## Extensão Fase 4 - validação roteada

Arquivos:

- `data/enriched/telemedicine_opportunity_phase4.csv`;
- `data/enriched/telemedicine_phase4_ads_routed_shortlist.csv`;
- `data/enriched/telemedicine_phase4_threshold_sensitivity.csv`.

| Campo | Unidade | Interpretação |
|---|---:|---|
| `phase4_eligibility` | categoria | elegível somente se o município foi roteado na Fase 3 |
| `phase4_evidence_grade` | categoria | `B_routed_public_osrm_proxy` ou `C_not_routed` |
| `phase4_ubs_travel_barrier_percentile_routed_subset` | 0-1 | percentil de tempo até UBS apenas entre municípios roteados |
| `phase4_pharmacy_travel_ease_percentile_routed_subset` | 0-1 | percentil inverso de tempo até farmácia apenas entre municípios roteados |
| `phase4_routed_access_score` | 0-100 | barreira UBS 65% e facilidade farmácia 35% |
| `telemedicine_phase4_routed_validation` | 0-100 | necessidade 45%, acesso roteado 35% e viabilidade 20% |
| `phase4_routed_validation_rank` | posição | ranking somente entre municípios roteados |
| `phase4_routed_target_rank` | posição | ranking somente entre alvos UBS >= 15 min e farmácia <= 5 min |
| `phase4_interpretation` | categoria | leitura operacional da Fase 4 |
| `ubs_hard_minutes_threshold` | minutos | limiar testado na sensibilidade |
| `pharmacy_easy_minutes_threshold` | minutos | limiar testado na sensibilidade |
| `candidate_count` | municípios | quantidade de alvos sob o par de limiares |
| `candidate_municipalities` | texto | municípios selecionados no cenário |

A Fase 4 é uma validação de piloto; não é um ranking nacional.
