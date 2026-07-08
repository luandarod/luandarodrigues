# Auditoria de publicacao

Data da revisao: 2026-07-08

## Status

O projeto esta publicavel como analise exploratoria de dados em saude publica. Ele ficou mais forte depois da validacao espacial, mas ainda nao deve ser apresentado como diagnostico de acesso real a Atencao Primaria.

O que ele sustenta bem:

- comparacao territorial de registros de UBS;
- disponibilidade relativa por populacao e area;
- cobertura potencial APS ponderada por populacao;
- qualidade cadastral das coordenadas;
- proxy operacional com CNES/ST e SIA/SUS PA;
- triagem de UFs e municipios que merecem investigacao.

O que ele ainda nao sustenta:

- funcionamento real de cada UBS;
- qualidade do cuidado;
- tempo real de deslocamento;
- capacidade operacional diaria;
- causalidade entre cobertura, UBS e resultado de saude.

## O que foi corrigido ou evoluido

| Ponto | Antes | Depois |
|---|---|---|
| Join IBGE/SIDRA | UBS usava codigo municipal de 6 digitos e IBGE/SIDRA usavam 7 | pipeline mantem as duas chaves e junta corretamente |
| Area territorial | parser podia inflar valores do SIDRA | parser preserva ponto decimal e aceita formato brasileiro |
| Coordenadas | havia apenas checagem ampla de latitude/longitude | agora ha auditoria por UF e validacao point-in-polygon com malhas municipais do IBGE |
| Operacao da UBS | cadastro era tratado apenas como presenca fisica | agora ha proxy operacional com CNES/ST mais recente e producao SIA/SUS PA |
| Sintese por UF | havia risco de grupo nulo | linhas sem UF ficam documentadas, mas saem da agregacao por UF |
| Cobertura APS | media simples municipal podia enganar | sintese usa cobertura ponderada, capada e excesso nominal |
| Atualidade da APS | arquivo manual antigo | extracao oficial via endpoint publico, competencia `04/2026` |
| Serie temporal | APS era uma foto unica | serie nacional de 64 competencias foi adicionada |
| Score | um unico conjunto de pesos | analise de sensibilidade com quatro cenarios |
| Dashboard | alguns numeros estavam hardcoded | dashboard carrega CSVs locais versionados |
| Proveniencia | fontes descritas sem manifesto tecnico | manifesto registra linhas, colunas, bytes e SHA-256 |
| Testes | protecao minima ausente | testes cobrem parsing, SIDRA, APS, outputs territoriais e validacao espacial |

## Validacao espacial

O script `validate_ubs_municipal_geometry.py` baixa 5.570 poligonos municipais simplificados pela API de Malhas Geograficas do IBGE e testa cada UBS contra o municipio declarado.

Resultado atual:

| Status | Registros |
|---|---:|
| Dentro do municipio declarado | 43.717 |
| Fora do municipio declarado | 2.062 |
| Sem coordenada completa | 1.929 |
| Fora do bounding box do Brasil | 3 |
| Sem poligono municipal correspondente | 3 |

Essa etapa resolve o limite anterior mais importante da qualidade espacial: coordenada valida no Brasil nao e a mesma coisa que coordenada consistente com o municipio do cadastro.

Limite remanescente: a malha usada e simplificada. Casos de fronteira municipal devem ser lidos como suspeitos para revisao, nao como erro cadastral definitivo.

## Proxy operacional

O script `fetch_ubs_operational_status.py` cruza os CNES do cadastro UBS com CNES/ST e SIA/SUS PA.

Resultado atual:

| Status | Registros |
|---|---:|
| Presente no CNES/ST mais recente | 43.578 |
| Com producao SIA/PA recente | 7.145 |
| Com CNES/ST e producao SIA/PA recente | 7.144 |
| Cadastro do projeto sem sinal atual CNES/ST ou SIA/PA | 4.135 |

Leitura correta: esse e um sinal de atividade registrada, nao uma auditoria de funcionamento. O SIA/SUS PA e uma base de producao/faturamento; ausencia de registro no mes mais recente pode refletir atraso, centralizacao de producao, regra local de registro ou producao vinculada a outro CNES.

## Fragilidades que continuam

- O cadastro UBS agora foi cruzado com CNES/ST e SIA/SUS PA, mas isso ainda nao prova equipe em funcionamento, horario de abertura ou qualidade do atendimento.
- A competencia APS mais recente foi obtida em 2026-07-07; para uso operacional, a extracao deve ser refeita no dia da analise.
- A serie temporal APS ainda esta no nivel Brasil; falta serie por UF ou municipio.
- O score de prioridade continua sendo triagem exploratoria. A sensibilidade ajuda, mas nao transforma o score em ranking oficial.
- A analise ainda nao integra vulnerabilidade social, distancias reais por rede viaria ou producao ambulatorial recente.

## Verificacoes executadas

```bash
python projects/ubs-healthcare-mapping/scripts/analyze_ubs.py \
  projects/ubs-healthcare-mapping/data/Unidades_Basicas_Saude-UBS.csv \
  projects/ubs-healthcare-mapping/data

python projects/ubs-healthcare-mapping/scripts/enrich_with_ibge.py \
  --input projects/ubs-healthcare-mapping/data/Unidades_Basicas_Saude-UBS.csv \
  --output-dir projects/ubs-healthcare-mapping/data/enriched

python projects/ubs-healthcare-mapping/scripts/fetch_latest_aps_coverage.py
python projects/ubs-healthcare-mapping/scripts/fetch_aps_national_timeseries.py

python projects/ubs-healthcare-mapping/scripts/enrich_with_aps_coverage.py \
  --ubs-territory projects/ubs-healthcare-mapping/data/enriched/municipality_ubs_territory.csv \
  --aps-file projects/ubs-healthcare-mapping/data/cobertura-aps-latest.csv \
  --output-dir projects/ubs-healthcare-mapping/data/enriched

python projects/ubs-healthcare-mapping/scripts/priority_sensitivity_analysis.py
python projects/ubs-healthcare-mapping/scripts/coordinate_quality_audit.py
python projects/ubs-healthcare-mapping/scripts/validate_ubs_municipal_geometry.py
python projects/ubs-healthcare-mapping/scripts/fetch_ubs_operational_status.py
python projects/ubs-healthcare-mapping/scripts/generate_report_assets.py
python projects/ubs-healthcare-mapping/scripts/build_dashboard_data.py
python projects/ubs-healthcare-mapping/scripts/build_data_lineage.py
python -m unittest discover -s projects/ubs-healthcare-mapping/tests
python -m compileall projects/ubs-healthcare-mapping/scripts projects/ubs-healthcare-mapping/tests
```

Resultado esperado: testes passando, scripts compilando e dashboard renderizando sem erro de console.

## Proximo salto de qualidade

1. Ampliar o SIA/SUS para janela de 3 a 6 meses e investigar outros blocos de producao.
2. Integrar equipes CNES por competencia.
3. Criar serie temporal APS por UF ou municipio.
4. Adicionar vulnerabilidade socioeconomica e estimativas de distancia/acesso.
5. Revisar os 2.062 registros fora do poligono municipal declarado.
