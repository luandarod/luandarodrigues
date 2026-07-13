# Protocolo de pré-paper — potencial municipal para telemedicina assistida

Versão analítica: 0.1, 12 de julho de 2026.

## Pergunta de pesquisa

Quais municípios brasileiros combinam maior necessidade assistencial potencial e maior capilaridade municipal observada do Programa Farmácia Popular para orientar hipóteses de implantação de telemedicina assistida?

O instrumento é exploratório, transversal e ecológico. Ele não estima demanda individual, proximidade real, elegibilidade clínica ou efeito causal da telemedicina. A unidade de análise é o município.

## Hipóteses

- H1: municípios com maior volume estimado de população fora da cobertura potencial da APS e menor oferta relativa de UBS recentes apresentam maior necessidade potencial;
- H2: municípios com maior número absoluto e maior densidade de estabelecimentos credenciados ao PFPB apresentam maior capacidade municipal preliminar de implantação;
- H3: municípios que permanecem prioritários sob diferentes pesos constituem candidatos mais robustos para investigação e piloto.

## Fontes e alinhamento temporal

| Domínio | Fonte | Referência |
|---|---|---|
| Universo municipal | API de Localidades do IBGE | extração em 12/07/2026; 5.571 municípios |
| População e território | IBGE, já integrado ao projeto | versão registrada no manifesto de linhagem |
| Cobertura potencial da APS | e-Gestor APS | competência CNES 04/2026 |
| UBS observadas | CNES/ST | competência 05/2026 |
| Farmácias credenciadas | Ministério da Saúde, PFPB | lista de 01/06/2026; 28.225 CNPJs únicos |

A presença no CNES/ST é proxy cadastral recente, não comprovação de horário, equipe ou capacidade. O credenciamento PFPB não comprova conexão ativa, estoque ou disponibilidade para sediar teleconsulta.

## Reconciliação do universo

O pipeline faz junção por código IBGE de seis dígitos e nunca por nome. Dos 5.571 códigos oficiais, 5.568 foram encontrados na base integrada. Três municípios foram mantidos como `missing_source_record`, e dois registros oficiais adicionais não têm dados centrais completos. Um código inválido (`530040`) foi isolado no arquivo de qualidade e não participa do ranking.

Ausência não é convertida em zero. Municípios sem dados centrais recebem `insufficient_core_data` e não são pontuados.

## Definições

### Gap relativo de APS

```text
aps_relative_gap = 1 - min(max(cobertura_aps_pct, 0), 100) / 100
```

Cobertura potencial acima de 100% é truncada para interpretação populacional. Isso representa capacidade nominal, não utilização efetiva.

### População potencialmente descoberta

```text
potentially_uncovered_population = population × aps_relative_gap
```

O termo “potencialmente” é obrigatório. A variável não identifica pessoas específicas sem atendimento.

### Necessidade potencial

Os componentes são winsorizados nos percentis 1 e 99 e convertidos em percentis empíricos. Contagens recebem `log1p`. Zeros estruturais de gap e população descoberta permanecem zero.

```text
need_score = 100 × geometric_mean(
  uncovered_volume_percentile ^ 0.50,
  aps_gap_percentile ^ 0.25,
  active_ubs_scarcity_percentile ^ 0.25
)
```

Os pesos são normativos e pré-especificados, não estimativas causais. O maior peso do volume corresponde ao objetivo declarado de localizar mais pessoas potencialmente alcançáveis.

### Capilaridade farmacêutica observada

```text
pharmacy_launchability_score = 100 × geometric_mean(
  pfpb_absolute_count_percentile ^ 0.50,
  pfpb_per_100k_percentile ^ 0.50
)
```

O nome “launchability” é uma proxy municipal. Não deve ser traduzido como proximidade ou prontidão do estabelecimento. Municípios sem PFPB recebem segmento de lacuna de infraestrutura, não pontuação favorável.

### Cenários do índice

```text
balanced       = need ^ 0.50 × launchability ^ 0.50
equity_led     = need ^ 0.70 × launchability ^ 0.30
deployment_led = need ^ 0.40 × launchability ^ 0.60
```

A média geométrica reduz compensação: uma dimensão muito baixa limita o total. Os três cenários devem ser publicados juntos.

## Incerteza dos pesos

São realizadas 1.000 simulações, com semente fixa `20260712`:

- pesos internos de necessidade: Dirichlet(10, 5, 5);
- pesos internos de capilaridade: Dirichlet(5, 5);
- peso total de necessidade: Uniforme(0,40; 0,70).

Essas distribuições são hipóteses de sensibilidade, não priors empíricos. O arquivo Monte Carlo apresenta mediana, percentis 5 e 95 da pontuação e posição, além da probabilidade de pertencer ao primeiro decil.

## Resultado preliminar reproduzido

- 5.571 municípios no universo oficial;
- 4.988 elegíveis para o índice proxy;
- 578 sem Farmácia Popular observada;
- 5 com dados centrais insuficientes;
- 176 no quadrante preliminar de alta necessidade e alta capilaridade;
- 100 municípios na shortlist territorial conservadora para teste de mídia.

Goiânia apresenta população de 1.437.366, cobertura potencial APS de 52,04%, população potencialmente descoberta de aproximadamente 689.361, 87 UBS observadas e 345 CNPJs PFPB. Aparece em 2º no cenário de equidade, 4º no equilibrado e 6º no orientado à implantação. Nas simulações, a posição mediana é 3, com intervalo de sensibilidade P05–P95 de 2–13. Isso é evidência de estabilidade do sinal, não prova de demanda comercial.

## Validade e limitações

### Validade presente

- validade de conteúdo sustentada por literatura e definições explícitas;
- universo oficial reconciliado;
- análise de cenários e incerteza;
- código, fontes e transformações versionáveis;
- testes automatizados para zeros, ausências, reconciliação e reprodutibilidade.

### Validade ainda ausente

- validade de critério contra teleconsultas efetivamente realizadas;
- tempo de viagem até UBS e farmácias;
- médicos equivalentes a tempo integral e produção assistencial;
- conectividade e privacidade do estabelecimento;
- demanda clínica, preço, conversão e retenção;
- avaliação de transbordamento entre municípios.

O próximo estágio acadêmico deve geocodificar estabelecimentos, usar grade populacional e rede viária, estimar E2SFCA, incorporar profissionais/produção e validar o índice em piloto prospectivo.

## Plano de validação do piloto

Selecionar municípios em quatro quadrantes de necessidade e capilaridade, com diversidade regional e de porte. Desfechos pré-especificados:

- sessões ofertadas e realizadas por mil habitantes;
- taxa de agendamento e comparecimento;
- resolução sem encaminhamento presencial;
- tempo até atendimento;
- custo por consulta e por caso resolvido;
- encaminhamentos e eventos de segurança;
- satisfação e continuidade do cuidado.

O relato deve seguir STROBE e RECORD para a fase observacional. Dados individuais ou intervenção com pacientes exigem avaliação ética, governança e proteção de dados.

## Adendo pré-especificado — índice Fase 1 v1

O índice preliminar 0.1 é preservado para rastreabilidade. A versão `phase1-v1` incorpora capacidade médica cadastrada e conectividade municipal, sem reescrever retroativamente o resultado original.

### Estrutura conceitual

```text
necessidade = média geométrica ponderada(
  volume potencialmente descoberto 45%,
  gap relativo de APS 20%,
  escassez de UBS por 100 mil 15%,
  escassez de médico FTE por 100 mil 20%
)

prontidão digital = média geométrica ponderada(
  domicílios com internet 50%,
  moradores estimados com cobertura 4G/5G 30%,
  acessos fixos por 100 habitantes 20%
)

viabilidade = farmácias 70% × prontidão digital 30%
oportunidade equilibrada = necessidade 50% × viabilidade 50%
```

Os pesos são normativos e devem ser apresentados com a análise de sensibilidade. A necessidade não contém conectividade: um município com barreira digital continua podendo ter alta necessidade, mas terá menor viabilidade de implantação imediata. A média geométrica limita compensação completa entre pilares.

### Produção assistencial

`sia_quantity_all_procedures` e cobertura de reporte são carregadas para auditoria, mas recebem `sia_score_role = audit_only_not_scored`. A quantidade PA não é chamada de consulta e não entra em nenhuma fórmula até existir uma seleção de procedimentos vinculada ao SIGTAP de cada competência.

### Sensibilidade Fase 1

São feitas 1.000 simulações com semente `20260712`: necessidade `Dirichlet(9,4,3,4)`, digital `Dirichlet(5,3,2)`, farmácias `Dirichlet(5,5)`, participação farmacêutica na viabilidade `Uniforme(0,60; 0,80)` e participação da necessidade no total `Uniforme(0,40; 0,70)`. Essas distribuições são hipóteses de robustez, não priors empíricos.

### Resultado reproduzido da Fase 1

- 5.571 municípios preservados;
- 4.988 elegíveis, 578 sem PFPB observado e 5 incompletos;
- Goiânia: necessidade 96,97; prontidão digital 92,73; viabilidade 78,90; oportunidade equilibrada 87,47; posição 3;
- o resultado de Goiânia é conduzido por população grande, gap APS e oferta relativa de médico/UBS, e não por uma contagem absoluta isolada;
- tempo de viagem, prontidão do estabelecimento farmacêutico e demanda clínica individual continuam não medidos.

Esta versão continua com grau `B_enhanced_ecological_proxy`. Grau A permanece condicionado a validação espacial/operacional e a dados de desfecho.

## Adendo Fase 2 — acesso geodésico

A versão `phase2-geodesic-v1` adiciona coordenadas oficiais das sedes municipais do IBGE, UBS ativas com geometria auditada e farmácias comuns mapeadas no OpenStreetMap. Distâncias são de grande círculo e não recebem interpretação de tempo de viagem.

O sinal conservador exige UBS a pelo menos 5 km, farmácia OSM a até 2 km e PFPB oficial presente. São publicados cenários 3/2 km e 10/5 km. O índice geral combina necessidade Fase 1, descompasso espacial e viabilidade em três cenários, com 1.000 simulações de sensibilidade.

Dos 40 municípios que atendem ao sinal espacial 5/2 km, seis também apresentam necessidade positiva no modelo e formam a shortlist de investigação. O resultado é hipótese para validação de rotas, não comprovação de dificuldade real. Goiânia não atende ao sinal espacial conservador.

## Adendo Fase 3 - preparação para tempo de viagem

A versão `phase3-routing-v1` cria e executa uma matriz origem-destino para os seis municípios da shortlist conservadora da Fase 2. Cada município recebe dois pares: sede municipal oficial do IBGE 2022 até a UBS ativa mais próxima e sede municipal até a farmácia OSM mais próxima.

O arquivo `data/enriched/telemedicine_phase3_routing_od_matrix_routed.csv` tem 12 pares roteados por OSRM público, perfil `driving`. A síntese municipal está em `data/enriched/telemedicine_phase3_routing_summary.csv`.

Pela regra operacional UBS >= 15 minutos e farmácia OSM <= 5 minutos, quatro municípios permanecem como candidatos roteados: Guapimirim/RJ, Sananduva/RS, Angatuba/SP e Arraial do Cabo/RJ. Arroio do Meio/RS não atinge o limiar de UBS difícil por tempo; Santa Maria Madalena/RJ tem UBS difícil, mas a farmácia mais próxima também fica distante pela rede viária.

Como a execução usou endpoint público, a evidência deve ser descrita como proxy exploratória de tempo de carro. O cálculo deve ser rerodado em OSRM local com extrato OSM versionado antes de submissão acadêmica.

## Referências metodológicas essenciais

1. [OECD/JRC. Handbook on Constructing Composite Indicators](https://doi.org/10.1787/9789264043466-en).
2. [WHO AccessMod — geographic access to health care](https://www.who.int/tools/accessmod-geographic-access-to-health-care).
3. [Spatial accessibility of primary health care using 2SFCA](https://pmc.ncbi.nlm.nih.gov/articles/PMC3520708/).
4. [Gravity models for potential spatial healthcare access: systematic review](https://pmc.ncbi.nlm.nih.gov/articles/PMC10693160/).
5. [Telehealth Initiative to Enhance Primary Care Access in Brazil — UBS+Digital](https://doi.org/10.2196/68434).
6. [Digital divide in Brazil and barriers to telehealth](https://doi.org/10.2196/42483).
7. [Impact of the Programa Farmácia Popular on chronic disease outcomes](https://pubmed.ncbi.nlm.nih.gov/30726501/).
8. [Community pharmacies and pharmacists in Brazil](https://pubmed.ncbi.nlm.nih.gov/34221207/).
