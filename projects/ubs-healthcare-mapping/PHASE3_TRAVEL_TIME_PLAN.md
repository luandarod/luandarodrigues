# Fase 3 - matriz de roteamento e tempo de viagem

Este documento define a transição entre a Fase 2, que mede distância geodésica, e uma Fase 3 com tempo de viagem em rede viária. A regra principal é não chamar distância em linha reta de tempo de viagem.

## Estado atual

Arquivo preparado: `data/enriched/telemedicine_phase3_routing_od_matrix.csv`.

O arquivo contém 12 pares origem-destino: seis municípios da shortlist conservadora da Fase 2, cada um com dois destinos:

- sede municipal oficial do IBGE 2022 até a UBS ativa mais próxima;
- sede municipal oficial do IBGE 2022 até a farmácia OSM mais próxima.

Todos os pares foram roteados de forma exploratória em `data/enriched/telemedicine_phase3_routing_od_matrix_routed.csv`, usando `https://router.project-osrm.org`, perfil `driving`, em 13/07/2026 UTC. Para publicação acadêmica, esta etapa deve ser rerodada em OSRM local com extrato OSM versionado.

A síntese municipal está em `data/enriched/telemedicine_phase3_routing_summary.csv`. Pela regra operacional UBS >= 15 min e farmácia <= 5 min, quatro municípios permanecem candidatos roteados: Guapimirim/RJ, Sananduva/RS, Angatuba/SP e Arraial do Cabo/RJ.

## Interpretação permitida

Com roteamento público, a Fase 3 pode ser descrita como proxy exploratória de tempo de carro em rede viária. Ela ainda não mede trânsito em tempo real, transporte público, caminhada, segurança viária, disponibilidade de atendimento ou prontidão operacional da farmácia.

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
python projects/ubs-healthcare-mapping/scripts/build_phase3_routing_summary.py
```

O script `fetch_phase3_osrm_travel_times.py` exige `--endpoint` ou `OSRM_BASE_URL` exatamente para impedir que o projeto use acidentalmente um serviço não documentado.

## Próximo salto metodológico

O passo seguinte, mais forte que sede municipal, é trocar a origem única por origens ponderadas por população. Isso exige grade populacional ou setores censitários com centroides, gerando múltiplos pares por município e uma média ponderada do tempo até UBS e farmácia.

## Uso em ads

Para posicionamento de mídia, a Fase 3 deve ser usada como filtro de validação, não como segmentação individual. A compra deve permanecer em nível geográfico agregado, com teste pareado e medição de conversão real.
