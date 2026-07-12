# Fase 1 — aquisição de capacidade assistencial e prontidão digital

Este documento registra fonte, competência, transformação, uso e limites de cada incremento da Fase 1. Cada bloco deve corresponder a um commit verificável.

## Produção assistencial SIA/SUS

### Fonte

- arquivo municipal derivado de `ubs_operational_status.csv`;
- origem remota: arquivos PA do SIA/SUS no DATASUS;
- janela do snapshot: três arquivos PA recentes por UF, registrada em `ubs_operational_status_metadata.json`.

### Métricas

- UBS presentes no CNES/ST;
- UBS com algum registro SIA recente;
- cobertura de reporte entre UBS presentes no CNES/ST;
- linhas de produção PA;
- quantidade total de procedimentos;
- quantidade por mil habitantes e por UBS reportante.

### Limite obrigatório

`PA_QTDPRO` mistura procedimentos ambulatoriais. Nesta etapa não é chamada de consulta e não compõe o score. A métrica entra apenas como evidência de reporte e operação. Uma contagem de consultas exigirá seleção de procedimentos pela versão do SIGTAP de cada competência.

## Profissionais e equipes CNES

### Fonte

- profissionais: arquivos CNES/PF, competência mais recente por UF;
- equipes: arquivos CNES/EP, competência mais recente por UF;
- escopo: estabelecimentos UBS presentes no cadastro do projeto.

### Regras

- médico: CBO iniciado por `225`;
- vínculo duplicado profissional–CNES–CBO: preserva a maior carga horária ambulatorial;
- FTE médico: soma de horas ambulatoriais semanais dividida por 40;
- equipe ativa: `DT_DESAT` vazio ou sentinela CNES `900001`;
- nenhum CPF, CNS, nome ou registro profissional é gravado no produto final;
- valores de FTE por 100 mil acima do percentil 99 recebem flag de revisão.

### Limites

CNES mede carga cadastrada, não presença real. Uma única competência não informa rotatividade. As equipes EP incluem todos os tipos; os quantitativos financiados de eSF/eAP continuam vindo do e-Gestor APS.

## Internet domiciliar — IBGE

### Fonte

- Censo Demográfico 2022;
- SIDRA, tabela 9936;
- variável de domicílios particulares permanentes ocupados por existência de conexão domiciliar à internet;
- condição de ocupação e tipo de domicílio mantidos em `Total`.

### Métricas

- domicílios totais;
- domicílios com e sem internet;
- percentual de domicílios com e sem internet;
- readiness municipal normalizada entre 0 e 1.

### Limites

Ter internet no domicílio não comprova velocidade, estabilidade, letramento digital ou conectividade da farmácia. Municípios criados após a malha de 2022 permanecem ausentes, nunca recebem zero.

## Conectividade municipal — Anatel

### Fontes e competências

- Cobertura Móvel, dados abertos da Anatel, arquivo municipal de março de 2026;
- Densidade de Banda Larga Fixa, dados abertos da Anatel, maio de 2026;
- URLs, membros internos dos ZIPs e datas efetivamente usadas ficam registrados no JSON de metadados;
- o coletor lê o diretório central dos ZIPs por HTTP Range e baixa somente os dois CSVs necessários. Assim, a execução é reproduzível sem transferir os arquivos históricos completos, que somam mais de 1 GB.

### Regras

- cobertura móvel principal: percentual estimado de moradores cobertos pela união de redes 4G/5G;
- operadora: linha agregada `Todas`; coberturas de operadoras individuais não são somadas;
- 5G permanece em coluna separada para análise, sem substituir o requisito mínimo 4G/5G;
- banda larga fixa: acessos em serviço por 100 habitantes na competência municipal mais recente;
- cobertura originalmente publicada como fração entre 0 e 1 é convertida para percentual entre 0 e 100;
- ausência de registro permanece nula, nunca é convertida em zero.

### Limites

A cobertura móvel é uma estimativa de propagação baseada em estações, antenas, potência, edificações e relevo. Ela pode diferir de medições de campo e não mede estabilidade, franquia ou preço. A densidade fixa conta acessos, não pessoas únicas; pode superar 100 e não informa velocidade ou qualidade. Nenhuma das duas fontes comprova conectividade dentro da farmácia nem letramento digital. Por isso, ambas entram como proxies de viabilidade de implantação, e não como necessidade de saúde ou tempo de viagem.

## Fechamento analítico da Fase 1

O script `build_telemedicine_phase1_index.py` integra as quatro aquisições sem substituir o índice preliminar. Médico FTE entra no pilar de necessidade; IBGE e Anatel entram na prontidão digital; produção SIA permanece apenas como auditoria. Todas as fórmulas e distribuições de sensibilidade ficam no protocolo e no JSON de metadados. O tempo de viagem permanece explicitamente fora do escopo desta fase.
