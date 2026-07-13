# Ranking estadual de oportunidade para telemedicina

Esta fase agrega a matriz municipal por UF para responder uma pergunta diferente:

> Em quais estados faz sentido priorizar telemedicina, piloto assistido ou melhoria de dados antes de expandir?

Arquivo principal:

`data/enriched/telemedicine_state_opportunity_summary.csv`

Metadados:

`data/enriched/telemedicine_state_opportunity_summary_metadata.json`

## Por que agregar por estado?

A decisão municipal é melhor para validação local. A decisão estadual é melhor para:

- leitura nacional;
- priorização de mercado;
- desenho de geoexperimentos;
- conversa com portfólio e estratégia.

O agregado estadual não substitui a matriz municipal. Ele resume onde existe escala.

## Score estadual v1

O `state_opportunity_score` combina intensidade e escala:

| Componente | Peso |
| --- | ---: |
| Score municipal Fase 2 ponderado por população | 0,35 |
| Necessidade ponderada por população | 0,20 |
| Prontidão digital ponderada por população | 0,10 |
| Contagem de municípios Top 100, escalada pelo melhor estado | 0,25 |
| População relativa, com raiz quadrada para reduzir dominância de escala | 0,10 |

Essa fórmula evita dois problemas:

- tratar um estado grande como prioritário só por população;
- tratar uma UF pequena como prioridade nacional só por intensidade alta em uma única unidade.

## Top estadual atual

| Rank | UF | Estratégia | Leitura |
| ---: | --- | --- | --- |
| 1 | SP | `hybrid_national_and_pharmacy_pilot` | Maior escala nacional, muitos Top 100 e um piloto farmácia |
| 2 | DF | `selective_city_ads` | Intensidade muito alta, mas sem escala intramunicipal |
| 3 | RJ | `hybrid_national_and_pharmacy_pilot` | Score alto e dois pilotos farmácia |
| 4 | RS | `hybrid_national_and_pharmacy_pilot` | Forte presença no Top 100 e um piloto farmácia |
| 5 | GO | `national_ads_priority` | Goiânia puxa oportunidade nacional e há múltiplos municípios Top 100 |
| 6 | PR | `national_ads_priority` | Boa escala para teste digital |
| 7 | MG | `national_ads_priority` | Muitos municípios Top 100, mas score ponderado menor |

## Estratégias estaduais

| Estratégia | Uso |
| --- | --- |
| `hybrid_national_and_pharmacy_pilot` | Combinar teste digital estadual com validação local dos pilotos farmácia |
| `national_ads_priority` | Priorizar geoexperimento digital em municípios Top 100 |
| `selective_city_ads` | Testar apenas municípios líderes, sem extrapolar para todo o estado |
| `digital_inclusion_first` | Desenhar oferta assistida ou de baixo consumo antes de campanha digital ampla |
| `regional_experiment` | Usar como lista ampliada ou experimento regional controlado |
| `data_quality_first` | Complementar dados antes de recomendar investimento territorial |
| `monitor` | Aguardar nova evidência ou atualização de dados |

## Controles de coerência

O resumo estadual precisa fechar com a matriz municipal:

- 27 UFs;
- soma estadual de Top 100 = 100;
- soma estadual de pilotos farmácia = 4;
- ranking estadual único;
- SP aparece como primeira UF na fórmula com escala v1.

## Limitações

- UF esconde heterogeneidade intramunicipal e intraestadual.
- DF é caso especial porque UF e município praticamente coincidem.
- O score estadual é ferramenta de triagem, não diagnóstico causal.
- A recomendação de ads deve ser validada por experimento geográfico, não por campanha individual.

## Comandos

Gerar resumo estadual:

```bash
python projects/ubs-healthcare-mapping/scripts/build_telemedicine_state_summary.py
```

Atualizar dados publicados:

```bash
python projects/ubs-healthcare-mapping/scripts/build_dashboard_data.py
```

Auditar coerência:

```bash
python projects/ubs-healthcare-mapping/scripts/audit_telemedicine_outputs.py
```
