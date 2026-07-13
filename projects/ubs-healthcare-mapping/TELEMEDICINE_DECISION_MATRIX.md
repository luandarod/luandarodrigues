# Matriz de decisão municipal para telemedicina

Esta fase transforma o ranking em classes de decisão. O objetivo é evitar que o projeto dependa de uma única posição ordinal e facilitar dois usos diferentes:

- pré-paper: classes ecológicas e auditáveis;
- ads: geos agregados para experimentos, sem targeting individual.

Arquivo principal:

`data/enriched/telemedicine_decision_matrix.csv`

Metadados:

`data/enriched/telemedicine_decision_matrix_metadata.json`

## Por que uma matriz?

Um ranking responde "quem vem primeiro?". Uma matriz responde "que tipo de decisão este município permite?".

Essa diferença é central porque telemedicina pode significar coisas diferentes:

- campanha digital direta;
- atendimento assistido em farmácia;
- inclusão digital antes de campanha;
- investigação regional;
- correção de dado antes de qualquer ação.

## Classes v1

| Classe | Leitura | Uso recomendado |
| --- | --- | --- |
| `national_priority_high_readiness` | Alta posição nacional e prontidão digital acima da mediana dos elegíveis | Teste de mídia agregado por município/UF |
| `national_priority_inclusion_first` | Alta posição nacional, mas prontidão digital abaixo da mediana | Oferta assistida, baixo consumo de dados ou inclusão digital antes |
| `high_need_digital_inclusion_first` | Necessidade alta e baixa prontidão digital | Não tratar como campanha digital simples |
| `regional_scale_opportunity` | Top 500 nacional fora do Top 100 | Experimento regional ou lista ampliada |
| `pharmacy_assisted_geodesic_candidate` | Sinal geodésico de UBS difícil e farmácia próxima | Roteirizar e validar parceiro |
| `pharmacy_assisted_pilot` | Subamostra Fase 4 com rota compatível | Piloto conservador com parceiro local |
| `monitor_or_low_priority` | Elegível, mas sem sinal prioritário nesta versão | Monitorar atualização de dados |
| `insufficient_evidence` | Falta dado suficiente para score nacional | Corrigir/complementar dado |

## Contagens atuais

| Classe | Municípios |
| --- | ---: |
| `national_priority_high_readiness` | 100 |
| `regional_scale_opportunity` | 395 |
| `pharmacy_assisted_pilot` | 4 |
| `pharmacy_assisted_geodesic_candidate` | 2 |
| `high_need_digital_inclusion_first` | 2 |
| `monitor_or_low_priority` | 4.485 |
| `insufficient_evidence` | 583 |

Na fotografia atual, todos os municípios Top 100 nacional têm prontidão digital acima da mediana dos municípios elegíveis. Por isso `national_priority_inclusion_first` existe como classe metodológica, mas não aparece nas contagens atuais.

## Regra de precedência

As classes são aplicadas em ordem de decisão:

1. evidência insuficiente;
2. oportunidade regional;
3. alta necessidade com inclusão digital antes;
4. prioridade nacional com inclusão digital antes;
5. prioridade nacional com prontidão;
6. candidato farmácia por distância geodésica;
7. piloto farmácia roteado.

Quando um município satisfaz mais de uma regra, prevalece a classe mais operacional. Exemplo: um município Fase 4 também pode ser Top 500, mas aparece como `pharmacy_assisted_pilot`.

## Caso Goiânia

Goiânia é um bom teste de coerência:

- rank nacional: 1;
- classe: `national_priority_high_readiness`;
- Fase 4: não é piloto farmácia.

Isso confirma que o projeto separa oportunidade nacional de telemedicina da hipótese específica de farmácia assistida.

## Uso em ads

A coluna `ads_positioning_tier` traduz a classe em uso de mídia:

- `test_digital_ads_now`;
- `regional_experiment`;
- `validate_route_and_partner`;
- `pilot_with_local_partner`;
- `digital_inclusion_first`;
- `monitor`;
- `do_not_target_before_data_fix`.

Essas classes são para compra e avaliação geográfica agregada. Não devem ser usadas para segmentar indivíduos, inferir condição clínica ou excluir pessoas de cuidado.

## Limitações

- A matriz ainda é ecológica e municipal.
- A origem espacial ainda não é ponderada por população intramunicipal.
- Farmácia assistida exige validação de parceiro, privacidade, agenda clínica e conectividade local.
- O score não prova causalidade nem substitui avaliação de demanda, qualidade ou desfecho clínico.

## Comandos

Gerar matriz:

```bash
python projects/ubs-healthcare-mapping/scripts/build_telemedicine_decision_matrix.py
```

Atualizar dashboard:

```bash
python projects/ubs-healthcare-mapping/scripts/build_dashboard_data.py
```

Auditar saídas:

```bash
python projects/ubs-healthcare-mapping/scripts/audit_telemedicine_outputs.py
```
