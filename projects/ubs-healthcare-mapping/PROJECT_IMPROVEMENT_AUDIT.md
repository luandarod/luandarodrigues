# Auditoria de melhoria do projeto

Data da revisão: 2026-07-13

Esta auditoria separa melhorias para quatro objetivos diferentes:

1. fortalecer o projeto como pré-paper;
2. tornar o índice mais defensável academicamente;
3. preservar utilidade para posicionamento de ads de telemedicina;
4. deixar o pipeline mais robusto para trabalho assistido por IA.

## Diagnóstico curto

O projeto já tem uma base rara para um portfólio de dados: fontes públicas, pipeline reproduzível, testes, dashboard e documentação por fase. A melhoria agora não é "ter mais dados por ter mais dados"; é transformar a hipótese em uma arquitetura de evidência.

### O que está bom

- A pergunta foi corretamente separada em duas leituras: oportunidade nacional de telemedicina e piloto farmácia assistida.
- O pipeline já evita chamar distância geodésica de tempo de viagem.
- Há sensibilidade de pesos e cenários, o que é consistente com boas práticas de indicadores compostos.
- A Fase 4 deixa explícito que o roteamento público é proxy exploratória e que a versão acadêmica exige OSRM local.
- Os dados já incluem camadas de APS, CNES, SIA/SUS, conectividade, IBGE e farmácias.

### O principal risco

O índice nacional ainda pode ser interpretado como "verdade de mercado" ou "prova de acesso", quando ele é uma triagem territorial. Para pré-paper e ads, isso precisa aparecer como:

- score de priorização, não diagnóstico causal;
- ranking sensível a pesos, não medida absoluta;
- oportunidade territorial agregada, não targeting individual de pacientes;
- hipótese para validação, não resultado final.

## Checagens feitas nesta revisão

| Item | Resultado |
| --- | --- |
| Branch | `main` à frente do remoto; sem push nesta revisão |
| GeoJSON do dashboard | 5.567 geometrias municipais |
| Municípios com score nacional Fase 2 | 4.988 |
| Top 100 nacional | 100 municípios |
| Piloto roteado Fase 4 | 4 municípios |
| Goiânia | rank nacional 1, sem rank de piloto farmácia |
| Testes antes desta auditoria | 56 testes passavam no commit anterior |

## Melhorias prioritárias

### 1. Trocar "score final" por matriz de decisão

Prioridade: alta.

O dashboard deve continuar mostrando ranking, mas o pré-paper deve apresentar uma matriz:

- necessidade assistencial;
- barreira espacial;
- prontidão digital;
- viabilidade operacional;
- adequação para farmácia assistida;
- risco de exclusão digital.

Isso reduz a fragilidade acadêmica porque evita depender demais de uma única agregação ponderada.

Próximo artefato recomendado:

- `data/enriched/telemedicine_decision_matrix.csv`;
- colunas de classe: `high_need_high_readiness`, `high_need_low_readiness`, `pharmacy_assisted_candidate`, `digital_inclusion_first`.

### 2. Evoluir acesso espacial para E2SFCA ou gravity model

Prioridade: alta para paper; média para portfólio.

A distância ao ponto mais próximo é uma boa primeira aproximação, mas acesso em saúde costuma ser melhor medido por oferta e demanda concorrente. A evolução acadêmica natural é:

- origem: setores censitários ou grade estatística, não só sede municipal;
- oferta: UBS/equipes/profissionais;
- demanda: população ponderada;
- impedância: tempo de viagem;
- método: 2SFCA/E2SFCA ou modelo gravitacional.

Enquanto isso não existir, o texto deve continuar dizendo "triagem municipal".

### 3. Criar protocolo de revisão de literatura reproduzível

Prioridade: alta.

O projeto precisa de uma mini revisão de escopo, não só referências soltas. Estrutura mínima:

- pergunta de revisão;
- bases consultadas;
- strings de busca;
- critérios de inclusão e exclusão;
- tabela de evidências;
- ligação entre evidência e variável do índice.

Pergunta sugerida:

> Quais dimensões territoriais, digitais e assistenciais são usadas para priorizar telemedicina na atenção primária, especialmente em contextos de desigualdade geográfica e digital?

### 4. Separar "ads" de "política pública"

Prioridade: alta.

Para ads, o projeto deve entregar geos agregados para teste de aquisição, não alegações clínicas. Melhor desenho:

- estados/municípios como clusters;
- teste A/B ou geo-experimento;
- métricas: CTR, lead qualificado, agendamento, comparecimento, conversão clínica elegível;
- fairness guardrail: não excluir territórios de alta necessidade por baixa prontidão digital sem registrar esse trade-off.

### 5. Explicar o caso Goiânia no dashboard e docs

Prioridade: média.

Goiânia é útil como "caso didático":

- alta oportunidade nacional;
- grande população;
- forte necessidade relativa no score;
- boa viabilidade;
- não é caso de "UBS longe e farmácia perto" pela regra conservadora.

Isso mostra que o método separa mercado amplo de piloto operacional.

### 6. Fortalecer reprodutibilidade de OSRM

Prioridade: alta antes de publicação.

A Fase 4 deve virar:

- extrato OSM versionado;
- hash do arquivo `.osm.pbf`;
- versão Docker/binário OSRM;
- perfil usado;
- data/hora da execução;
- cache das respostas;
- comparação público vs local para os 12 pares iniciais.

### 7. Adicionar auditoria automática de saídas

Prioridade: média. Implementação inicial adicionada em `scripts/audit_telemedicine_outputs.py`.

Criar um script de auditoria com invariantes:

- GeoJSON tem campos do score nacional;
- dashboard tem filtros nacional, Top 100 e Fase 4;
- Fase 4 não substitui visão nacional;
- Goiânia aparece como oportunidade nacional e não como piloto farmácia;
- contagens principais são emitidas em JSON.

Isso reduz regressões típicas de desenvolvimento com IA.

Comando:

```bash
python projects/ubs-healthcare-mapping/scripts/audit_telemedicine_outputs.py
```

### 8. Melhorar frontend sem inflar complexidade

Prioridade: média.

O dashboard atual funciona, mas o JS inline começa a ficar denso. Próxima melhoria:

- mover lógica de filtro/cor/tabela para arquivo JS próprio;
- adicionar teste mínimo de parsing ou Playwright;
- mostrar cards estaduais agregados;
- adicionar camada "Top estados";
- permitir baixar CSV do recorte filtrado.

### 9. Tornar o índice mais explicável

Prioridade: média.

Para cada município no popup/tabela, mostrar a frase:

> Este município sobe no ranking principalmente por: necessidade / viabilidade / barreira espacial / população.

Isso pode ser calculado por maior pilar padronizado. Ajuda tanto em paper quanto em storytelling.

### 10. Incluir análise de robustez por rank interval

Prioridade: média.

Além do rank pontual, mostrar:

- rank mediano Monte Carlo;
- intervalo p10-p90;
- probabilidade de estar no Top 100;
- classe de estabilidade.

Isso é mais defensável que dizer "município X é o 1º".

## Ideias de pesquisa mais fortes

### Ideia A — "Telemedicina como substituto parcial de atrito geográfico"

Pergunta:

> A priorização territorial de telemedicina muda quando o acesso é modelado como combinação de barreira física, prontidão digital e escassez assistencial?

Contribuição:

- índice municipal transparente;
- comparação entre score nacional e piloto operacional;
- mapa reproduzível.

### Ideia B — "Farmácia como infraestrutura assistida de acesso digital"

Pergunta:

> Em municípios onde a UBS é espacialmente menos acessível, farmácias podem funcionar como pontos assistidos de acesso à telemedicina?

Contribuição:

- hipótese mais original;
- conecta acesso físico e cuidado digital;
- exige validação ética e operacional forte.

### Ideia C — "Risco de telemedicina reforçar desigualdade"

Pergunta:

> Quais municípios têm alta necessidade de telemedicina, mas baixa prontidão digital, exigindo intervenção de inclusão antes de campanha digital?

Contribuição:

- evita leitura ingênua de mercado;
- dialoga diretamente com literatura de exclusão digital.

## Fontes bibliográficas úteis para justificar próximos passos

| Tema | Fonte | Uso no projeto |
| --- | --- | --- |
| Indicadores compostos | OECD/EC-JRC, *Handbook on Constructing Composite Indicators* | Justifica transparência, normalização, pesos, sensibilidade e cautela na interpretação de rankings |
| Digitalização da APS no Brasil | OECD, *Primary Health Care in Brazil*, cap. 6 | Justifica prontidão digital como barreira central e desigual |
| Exclusão digital no Brasil | Nakayama et al., JMIR 2023 | Justifica incluir ruralidade, renda, idade e acesso à internet como limites de telemedicina |
| UBS+Digital | Lamas et al., JMIR 2025 | Mostra plausibilidade operacional de teleconsulta em UBS sem médico presencial e necessidade de infraestrutura |
| Acesso espacial em saúde | Literatura 2SFCA/E2SFCA | Justifica evolução de "distância ao serviço mais próximo" para oferta-demanda com impedância |

URLs consultadas:

- https://www.oecd.org/en/publications/handbook-on-constructing-composite-indicators-methodology-and-user-guide_9789264043466-en.html
- https://www.oecd.org/en/publications/2021/12/primary-health-care-in-brazil_8ba611b2/full-report/the-digital-transformation-of-primary-health-care-in-brazil_8d9f36fd.html
- https://www.jmir.org/2023/1/e42483/
- https://www.jmir.org/2025/1/e68434/

## Próximo pacote recomendado

Eu faria a próxima fase em três commits:

1. `feat: add telemedicine decision matrix`
   - gerar matriz municipal com classes interpretáveis;
   - adicionar teste de invariantes.
   - status: implementado em `scripts/build_telemedicine_decision_matrix.py` e documentado em `TELEMEDICINE_DECISION_MATRIX.md`.

2. `docs: add scoping review protocol`
   - protocolo de busca;
   - tabela de evidências;
   - relação variável ↔ literatura.

3. `feat: add state opportunity summary`
   - ranking estadual agregado;
   - cards no dashboard;
   - CSV exportável.
   - status: agregado estadual implementado em `scripts/build_telemedicine_state_summary.py`; cards no dashboard ficam como próximo incremento visual.

## Decisão metodológica recomendada

Manter dois produtos, com nomes fixos:

- **Índice Nacional de Oportunidade para Telemedicina**: triagem estratégica.
- **Piloto Farmácia Assistida**: validação operacional conservadora.

Essa separação é a espinha dorsal do projeto. Ela impede que poucos alvos Fase 4 pareçam "erro" e impede que o ranking nacional seja vendido como prova de acesso físico.
