# Guia de posicionamento territorial para ads de telemedicina

## Objetivo

Usar sinais municipais agregados para decidir onde testar campanhas, sem inferir condição médica, vulnerabilidade ou intenção individual.

O arquivo operacional conservador atualizado é `data/enriched/telemedicine_phase2_ads_geo_shortlist.csv`. Ele contém somente municípios com UBS ≥5 km, farmácia OSM ≤2 km, PFPB presente e necessidade positiva, ordenados pela robustez Monte Carlo e pelo cenário equilibrado. As shortlists anteriores são preservadas para comparação de versões.

Para validação espacial antes de compra de mídia, use também `data/enriched/telemedicine_phase3_routing_summary.csv`. Na execução exploratória por OSRM público, quatro municípios mantêm o padrão UBS >= 15 min e farmácia <= 5 min: Guapimirim/RJ, Sananduva/RS, Angatuba/SP e Arraial do Cabo/RJ.

O arquivo mais conservador para campanha piloto agora é `data/enriched/telemedicine_phase4_ads_routed_shortlist.csv`. Ele ordena apenas os alvos roteados, combinando necessidade, acesso por tempo e viabilidade.

Para uma primeira compra pequena, priorize Guapimirim/RJ e Angatuba/SP: eles sobrevivem também ao limiar mais duro de UBS >= 20 minutos. Sananduva/RS e Arraial do Cabo/RJ entram como segunda dupla, ainda consistentes no cenário UBS >= 15 minutos.

## Uso recomendado

1. Selecionar de 6 a 12 municípios da shortlist, preservando diversidade de região e porte;
2. confirmar cobertura comercial, disponibilidade médica, regras de atendimento e parceiros locais;
3. validar manualmente pelo menos duas farmácias por município;
4. rerodar ou auditar o tempo de viagem dos pares da Fase 3 com motor documentado;
5. confirmar internet, privacidade, acessibilidade e equipe em cada estabelecimento participante;
6. executar teste geográfico com orçamento e criativos equivalentes;
7. medir funil completo e comparar com municípios-controle pareados;
8. recalibrar o índice somente após acumular desfechos suficientes.

## Mensagem por segmento

| Segmento | Hipótese de posicionamento | Decisão |
|---|---|---|
| `pilot_candidate` | conveniência, orientação e acesso remoto com encaminhamento responsável | primeira onda, após validação local |
| `high_need_build_supply` | acesso remoto direto ou parceria alternativa | testar somente se operação não depender da farmácia |
| `launchable_secondary` | conveniência e integração com rede farmacêutica | segunda onda ou controle de viabilidade |
| `infrastructure_gap` | nenhuma recomendação de mídia baseada em farmácia | desenvolver canal antes de comprar mídia |

## Desenho mínimo de experimento

- unidade de randomização preferencial: município ou conjunto de municípios pareados;
- duração: definida por cálculo de poder, não por prazo arbitrário;
- desfecho primário: consulta concluída por mil impressões ou por população alcançada;
- secundários: custo por agendamento, comparecimento, resolução, encaminhamento e retenção;
- controles: orçamento, frequência, criativo, canal, preço, horários e disponibilidade médica;
- análise: intenção de tratar no nível geográfico, intervalos de confiança e ajuste por exposição.

Não otimizar apenas por clique. Cliques podem favorecer curiosidade e não acesso efetivo.

## Guardrails

- usar somente localização municipal ou regional agregada;
- não combinar o índice com prontuários, diagnósticos, medicamentos ou listas de pacientes;
- não criar públicos de hipertensos, diabéticos ou outras condições sensíveis sem base legal e revisão específica;
- não apresentar o anúncio como substituição universal da consulta presencial;
- não prometer disponibilidade que a operação não consegue cumprir;
- manter triagem, consentimento, privacidade, segurança e encaminhamento presencial quando indicado;
- avaliar políticas atuais de cada plataforma antes da campanha.

## Leitura correta

O índice serve para escolher onde aprender primeiro. Ele não demonstra que residentes de um município desejam telemedicina, que uma farmácia aceitará parceria ou que a campanha será rentável. Conversão e impacto precisam ser medidos no experimento.
