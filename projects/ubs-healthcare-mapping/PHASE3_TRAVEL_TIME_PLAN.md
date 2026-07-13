# Fase 3 - matriz de roteamento e tempo de viagem

Este documento define a transição entre a Fase 2, que mede distância geodésica, e uma Fase 3 com tempo de viagem em rede viária. A regra principal é não chamar distância em linha reta de tempo de viagem.

## Estado atual

Arquivo preparado: `data/enriched/telemedicine_phase3_routing_od_matrix.csv`.

O arquivo contém 12 pares origem-destino: seis municípios da shortlist conservadora da Fase 2, cada um com dois destinos:

- sede municipal oficial do IBGE 2022 até a UBS ativa mais próxima;
- sede municipal oficial do IBGE 2022 até a farmácia OSM mais próxima.

Todos os pares estão com `routing_readiness_status = ready_for_network_routing`. Os campos `travel_time_minutes` e `network_distance_km` permanecem vazios até execução de um motor de roteamento documentado.

## Interpretação permitida

Antes do roteamento, a Fase 3 só pode ser descrita como "matriz OD pronta para cálculo de rota". Ela não mede acesso real, trânsito, transporte público, caminhada, segurança viária ou disponibilidade de atendimento.

Depois do roteamento, o tempo será uma proxy de deslocamento pelo perfil escolhido. Para uso acadêmico, o relatório deve informar:

- motor de roteamento, versão e endpoint;
- origem dos dados viários, por exemplo OpenStreetMap PBF e data de download;
- perfil usado, por exemplo carro, caminhada ou transporte público;
- data e hora da execução;
- tratamento de rotas sem resposta;
- comparação entre distância geodésica e distância em rede.

## Roteamento recomendado

Para pré-paper, a opção preferida é OSRM local com extrato OSM versionado. Um serviço público pode ser útil para protótipo pequeno, mas não deve sustentar resultado acadêmico sem garantia de reprodutibilidade.

Fluxo mínimo:

```powershell
python projects/ubs-healthcare-mapping/scripts/build_phase3_routing_od_matrix.py
$env:OSRM_BASE_URL = "http://localhost:5000"
python projects/ubs-healthcare-mapping/scripts/fetch_phase3_osrm_travel_times.py
```

O script `fetch_phase3_osrm_travel_times.py` exige `--endpoint` ou `OSRM_BASE_URL` exatamente para impedir que o projeto use acidentalmente um serviço não documentado.

## Próximo salto metodológico

O passo seguinte, mais forte que sede municipal, é trocar a origem única por origens ponderadas por população. Isso exige grade populacional ou setores censitários com centroides, gerando múltiplos pares por município e uma média ponderada do tempo até UBS e farmácia.

## Uso em ads

Para posicionamento de mídia, a Fase 3 deve ser usada como filtro de validação, não como segmentação individual. A compra deve permanecer em nível geográfico agregado, com teste pareado e medição de conversão real.
