# Fase 4 - validação roteada para priorização operacional

A Fase 4 transforma a rota exploratória da Fase 3 em uma camada de decisão para piloto e ads. Ela não substitui o ranking nacional da Fase 2, porque somente os seis alvos conservadores foram roteados.

## Regra operacional

Um município é alvo primário Fase 4 quando:

```text
tempo até UBS ativa >= 15 minutos
tempo até farmácia OSM <= 5 minutos
```

O tempo foi calculado com OSRM público, perfil `driving`. Isso é uma proxy exploratória; para pré-paper, a etapa deve ser rerodada em OSRM local com extrato OSM versionado.

## Resultado

Quatro municípios permanecem como alvos roteados:

| Rank | Município | UF | Tempo até UBS | Tempo até farmácia |
|---:|---|---|---:|---:|
| 1 | Guapimirim | RJ | 24,1 min | 0,1 min |
| 2 | Angatuba | SP | 20,1 min | 1,3 min |
| 3 | Sananduva | RS | 19,5 min | 0,7 min |
| 4 | Arraial do Cabo | RJ | 19,3 min | 1,5 min |

Arroio do Meio/RS perde o sinal por não atingir 15 minutos até UBS. Santa Maria Madalena/RJ mantém UBS difícil, mas a farmácia também fica distante pela rede viária.

## Índice Fase 4

O score combina:

- necessidade Fase 2: 45%;
- acesso roteado: 35%;
- viabilidade Fase 2: 20%.

O acesso roteado combina barreira até UBS, com peso 65%, e facilidade até farmácia, com peso 35%, em percentis apenas da subamostra roteada.

## Uso correto

Use `data/enriched/telemedicine_phase4_ads_routed_shortlist.csv` para escolher pilotos territoriais pequenos e validação local. Não use a Fase 4 para segmentar indivíduos, inferir condição clínica, ou afirmar disponibilidade real da farmácia.

## Sensibilidade dos limiares

Arquivo: `data/enriched/telemedicine_phase4_threshold_sensitivity.csv`.

O resultado é estável para os limiares UBS >= 10 ou >= 15 minutos combinados com farmácia <= 3, <= 5 ou <= 10 minutos: os quatro alvos permanecem. Ao exigir UBS >= 20 minutos, a lista fica mais restrita e mantém apenas Guapimirim/RJ e Angatuba/SP.

Essa sensibilidade deve acompanhar qualquer apresentação externa, porque deixa claro que Sananduva/RS e Arraial do Cabo/RJ dependem de um limiar de barreira UBS de 15 minutos, enquanto Guapimirim/RJ e Angatuba/SP são os dois casos mais robustos ao limiar mais duro.
