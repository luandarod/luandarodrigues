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
