# Auditoria de publicação

Data da revisão: 2026-07-07

## Status

O projeto está publicável como análise exploratória de dados em saúde pública, desde que as limitações continuem visíveis no README e no dashboard.

Ele não deve ser apresentado como diagnóstico de acesso real à Atenção Primária.

## O que foi corrigido ou evoluído

| Ponto | Antes | Depois |
|---|---|---|
| Join IBGE/SIDRA | UBS usava código municipal de 6 dígitos e IBGE/SIDRA usavam 7, quebrando população e área | pipeline mantém as duas chaves e junta pelo código de 6 dígitos |
| Área territorial | parser removia todos os pontos e inflava áreas como AC para `164173431` | parser preserva ponto decimal e aceita formato brasileiro |
| Coordenadas | `analyze_ubs.py` não lia vírgula decimal | latitude e longitude são normalizadas antes da validação |
| Síntese por UF | havia grupo nulo com população e área zero | linhas sem UF ficam documentadas, mas saem da agregação por UF |
| Cobertura APS | média simples municipal escondia diferença de população | síntese traz cobertura ponderada, capada e excesso nominal |
| Atualidade da APS | arquivo manual de `01/2021` | extração oficial via endpoint público, competência `04/2026` |
| Score | triagem com um único conjunto de pesos | análise de sensibilidade com quatro cenários de pesos |
| Dashboard | números de UF estavam hardcoded e divergiam dos CSVs | dashboard carrega CSVs locais versionados |
| Série temporal | APS era analisada como uma competência isolada | série nacional de 64 competências foi adicionada |
| Coordenadas | só havia percentual geral de validade | auditoria por UF separa ausentes, fora do bounding box e repetidas |
| Proveniência | fontes eram descritas, mas sem manifesto técnico | manifesto registra linhas, colunas, bytes e SHA-256 |
| Testes | não havia proteção mínima | foram adicionados testes de parsing, SIDRA, APS oficial, outputs territoriais e cobertura |

## Fragilidades que continuam

- A validação de coordenadas ainda não usa polígonos municipais. Ela agora separa ausentes, fora do bounding box e repetidas, mas não prova que o ponto está dentro do município correto.
- A competência APS mais recente foi obtida do endpoint público em 2026-07-07. Para decisão operacional, a extração precisa ser refeita no dia da análise.
- O cadastro UBS não prova atividade da unidade, produção, equipe em funcionamento ou qualidade do atendimento.
- O score de prioridade continua sendo uma triagem exploratória. A sensibilidade ajuda, mas não transforma o score em ranking oficial.
- A série temporal APS foi adicionada no nível Brasil. Ainda falta série municipal ou por UF.
- A análise ainda não tem mapa com polígonos municipais ou distância até serviços.

## Verificações executadas

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
python projects/ubs-healthcare-mapping/scripts/generate_report_assets.py
python projects/ubs-healthcare-mapping/scripts/build_dashboard_data.py
python projects/ubs-healthcare-mapping/scripts/build_data_lineage.py
python -m unittest discover -s projects/ubs-healthcare-mapping/tests
python -m compileall projects/ubs-healthcare-mapping/scripts projects/ubs-healthcare-mapping/tests
```

Resultado: testes passaram, scripts compilaram e o dashboard renderizou sem erro de console no smoke test local.

## Próximo salto de qualidade

1. Validar coordenadas com polígonos municipais do IBGE.
2. Criar série temporal da APS, não só uma foto de `04/2026`.
3. Adicionar produção ambulatorial e equipes ativas por competência.
4. Levar a sensibilidade do score para intervalos de incerteza.
5. Publicar uma seção curta explicando por que média simples de cobertura APS pode enganar.
