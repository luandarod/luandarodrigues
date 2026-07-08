# Bases metodologicas e bibliograficas

Este projeto nao usa referencias como enfeite. Cada bloco metodologico existe para reduzir uma leitura apressada dos dados.

## Como as referencias sustentam o metodo

| Decisao no projeto | Base metodologica | Como foi aplicada |
|---|---|---|
| Separar presenca fisica, capacidade potencial e acesso real | Donabedian; Penchansky e Thomas | O cadastro UBS entra como estrutura. A Cobertura APS entra como capacidade potencial. O texto evita chamar isso de acesso real. |
| Tratar cobertura APS acima de 100% com cuidado | Logica de capacidade potencial | Valores acima de 100% sao preservados como capacidade nominal, mas tambem existe uma versao capada para leitura populacional. |
| Usar cobertura ponderada por populacao | Estatistica descritiva para taxas agregadas | A leitura principal usa `sum(capacidade) / sum(populacao)`, evitando media simples entre municipios muito diferentes. |
| Validar coordenadas em duas camadas | Qualidade de dados; geografia da saude | Primeiro vem a checagem de plausibilidade no Brasil. Depois vem o teste point-in-polygon contra o municipio declarado. |
| Separar problemas de coordenada | Wang e Strong; qualidade contextual dos dados | A auditoria distingue coordenada ausente, fora do bounding box, repetida e fora do municipio declarado. |
| Usar malhas municipais simplificadas | IBGE API de Malhas Geograficas | As malhas servem para triagem espacial reproduzivel. Casos de fronteira nao sao tratados como erro definitivo. |
| Evitar inferencia individual a partir de UF ou municipio | Robinson; falacia ecologica | O projeto fala de sinais territoriais agregados, nao de comportamento ou acesso individual. |
| Alertar sobre agregacao espacial | Openshaw; MAUP | Rankings por UF sao tratados como leitura agregada e sensivel a escala. |
| Reduzir leitura de foto unica | Analise temporal descritiva | A serie nacional APS acompanha 64 competencias, em vez de depender apenas de `04/2026`. |
| Usar score como triagem, nao ranking oficial | OECD/JRC; indicadores compostos | O score e documentado como instrumento exploratorio. Os pesos sao testados em cenarios. |
| Fazer sensibilidade do score | OECD/JRC; Saltelli/Saisana/Tarantola | O projeto compara quatro cenarios de pesos para ver quais UFs sao estaveis e quais dependem da escolha do peso. |
| Testar parsing, joins e saidas | Boas praticas de reprodutibilidade em dados | Foram adicionados testes de sanidade para parsing decimal, SIDRA, APS oficial, outputs territoriais e validacao espacial. |

## Referencias

1. Donabedian, A. (1966/2005). *Evaluating the Quality of Medical Care*. Milbank Quarterly.  
   https://pubmed.ncbi.nlm.nih.gov/16279964/

2. Penchansky, R.; Thomas, J. W. (1981). *The Concept of Access: Definition and Relationship to Consumer Satisfaction*. Medical Care.  
   https://pubmed.ncbi.nlm.nih.gov/7206846/

3. Wang, R. Y.; Strong, D. M. (1996). *Beyond Accuracy: What Data Quality Means to Data Consumers*. Journal of Management Information Systems.  
   https://www.tandfonline.com/doi/abs/10.1080/07421222.1996.11518099

4. OECD; European Commission Joint Research Centre. (2008). *Handbook on Constructing Composite Indicators: Methodology and User Guide*.  
   https://www.oecd.org/content/dam/oecd/en/publications/reports/2008/08/handbook-on-constructing-composite-indicators-methodology-and-user-guide_g1gh9301/9789264043466-en.pdf

5. Saisana, M.; Saltelli, A.; Tarantola, S. (2005). *Uncertainty and sensitivity analysis techniques as tools for the quality assessment of composite indicators*.  
   https://www.semanticscholar.org/paper/OECD-JRC-Handbook-on-constructing-composite-.-into-Nardo-Saisana/33eb3485d310454e9874c3a05dabd3d4b33623b5

6. Openshaw, S. (1984). *The Modifiable Areal Unit Problem*. Concepts and Techniques in Modern Geography.  
   https://www.uio.no/studier/emner/sv/iss/SGO9010/openshaw1983.pdf

7. Robinson, W. S. (1950). *Ecological Correlations and the Behavior of Individuals*. American Sociological Review.  
   https://www.jstor.org/stable/2087176

8. WHO; USAID. *Service Availability and Readiness Assessment (SARA): Reference Manual*.  
   https://cdn.who.int/media/docs/default-source/service-availability-and-readinessassessment%28sara%29/sara_reference_manual_chapter3.pdf

9. Ministerio da Saude. *Relatorios Publicos da APS: Cobertura Potencial da APS*.  
   Pagina publica: https://relatorioaps.saude.gov.br/cobertura/aps  
   Endpoint usado no script: https://relatorioaps-prd.saude.gov.br/cobertura/aps

10. IBGE. *API de Localidades*.  
    https://servicodados.ibge.gov.br/api/docs/localidades

11. IBGE. *API de Malhas Geograficas*.  
    https://servicodados.ibge.gov.br/api/docs/malhas?versao=3

12. IBGE/SIDRA. *Tabela 4714: populacao residente, area territorial e densidade demografica*.  
    Endpoint usado no script: https://apisidra.ibge.gov.br/values/t/4714/n6/all/p/last

## Leitura pratica

O projeto fica defensavel quando e apresentado como analise de sinais:

- UBS registrada indica estrutura fisica cadastrada.
- Cobertura APS indica capacidade potencial informada.
- A serie APS nacional mostra contexto temporal para a competencia mais recente.
- A validacao espacial mostra se a coordenada e consistente com o municipio declarado.
- Indicadores por UF e municipio sao agregados territoriais.
- O score e triagem exploratoria.
- A sensibilidade dos pesos mostra onde a conclusao e mais ou menos estavel.

Essa combinacao sustenta um projeto de portfolio com boa ambicao analitica, sem vender mais certeza do que os dados permitem.
