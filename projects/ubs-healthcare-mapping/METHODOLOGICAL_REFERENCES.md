# Bases metodológicas e bibliográficas

Este projeto não usa as referências como enfeite. Cada bloco metodológico existe para reduzir uma leitura apressada dos dados.

## Como as referências sustentam o método

| Decisão no projeto | Base metodológica | Como foi aplicada |
|---|---|---|
| Separar presença física, capacidade potencial e acesso real | Donabedian; Penchansky e Thomas | O cadastro UBS entra como estrutura. A Cobertura APS entra como capacidade potencial. O README evita chamar isso de acesso real. |
| Tratar cobertura APS acima de 100% com cuidado | Nota técnica da APS; lógica de capacidade potencial | Valores acima de 100% são preservados como capacidade nominal, mas também existe uma versão capada em 100% para leitura populacional. |
| Usar cobertura ponderada por população | Estatística descritiva para taxas agregadas | A média simples municipal é mantida como informação secundária. A leitura principal usa `sum(capacidade) / sum(população)`. |
| Validar coordenadas sem exagerar a conclusão | Qualidade de dados; geografia da saúde | Coordenada válida significa ponto em faixa plausível, não localização municipal comprovada. |
| Separar problemas de coordenada | Wang e Strong; qualidade contextual dos dados | A auditoria distingue coordenada ausente, fora do bounding box e repetida. |
| Evitar inferência individual a partir de UF ou município | Robinson; falácia ecológica | O projeto fala de sinais territoriais agregados, não de comportamento ou acesso individual. |
| Alertar sobre agregação espacial | Openshaw; MAUP | Rankings por UF são tratados como leitura agregada. O próximo passo recomendado é validar em escala municipal e com polígonos. |
| Reduzir leitura de foto única | Análise temporal descritiva | A série nacional APS acompanha 64 competências, em vez de depender apenas de 04/2026. |
| Usar score como triagem, não ranking oficial | OECD/JRC; indicadores compostos | O score é documentado como instrumento exploratório. Os pesos são testados em cenários. |
| Fazer sensibilidade do score | OECD/JRC; Saltelli/Saisana/Tarantola | O projeto compara quatro cenários de pesos para ver quais UFs são estáveis e quais dependem da escolha do peso. |
| Testar parsing, joins e saídas | Boas práticas de reprodutibilidade em dados | Foram adicionados testes de sanidade para parsing decimal, SIDRA, APS oficial, outputs territoriais e cobertura ponderada. |

## Referências

1. Donabedian, A. (1966/2005). *Evaluating the Quality of Medical Care*. Milbank Quarterly.  
   Referência: https://pubmed.ncbi.nlm.nih.gov/16279964/

2. Penchansky, R.; Thomas, J. W. (1981). *The Concept of Access: Definition and Relationship to Consumer Satisfaction*. Medical Care.  
   Referência: https://pubmed.ncbi.nlm.nih.gov/7206846/

3. Wang, R. Y.; Strong, D. M. (1996). *Beyond Accuracy: What Data Quality Means to Data Consumers*. Journal of Management Information Systems.  
   Referência: https://www.tandfonline.com/doi/abs/10.1080/07421222.1996.11518099

4. OECD; European Commission Joint Research Centre. (2008). *Handbook on Constructing Composite Indicators: Methodology and User Guide*.  
   Referência: https://www.oecd.org/content/dam/oecd/en/publications/reports/2008/08/handbook-on-constructing-composite-indicators-methodology-and-user-guide_g1gh9301/9789264043466-en.pdf

5. Saisana, M.; Saltelli, A.; Tarantola, S. (2005). *Uncertainty and sensitivity analysis techniques as tools for the quality assessment of composite indicators*.  
   Referência relacionada ao handbook OECD/JRC: https://www.semanticscholar.org/paper/OECD-JRC-Handbook-on-constructing-composite-.-into-Nardo-Saisana/33eb3485d310454e9874c3a05dabd3d4b33623b5

6. Openshaw, S. (1984). *The Modifiable Areal Unit Problem*. Concepts and Techniques in Modern Geography.  
   Referência: https://www.uio.no/studier/emner/sv/iss/SGO9010/openshaw1983.pdf

7. Robinson, W. S. (1950). *Ecological Correlations and the Behavior of Individuals*. American Sociological Review.  
   Referência: https://www.jstor.org/stable/2087176

8. WHO; USAID. *Service Availability and Readiness Assessment (SARA): Reference Manual*.  
   Referência: https://cdn.who.int/media/docs/default-source/service-availability-and-readinessassessment%28sara%29/sara_reference_manual_chapter3.pdf

9. Ministério da Saúde. *Relatórios Públicos da APS: Cobertura Potencial da APS*.  
   Página pública: https://relatorioaps.saude.gov.br/cobertura/aps  
   Endpoint usado no script: https://relatorioaps-prd.saude.gov.br/cobertura/aps

10. IBGE. *API de Localidades*.  
    Referência: https://servicodados.ibge.gov.br/api/docs/localidades

11. IBGE/SIDRA. *Tabela 4714: população residente, área territorial e densidade demográfica*.  
    Endpoint usado no script: https://apisidra.ibge.gov.br/values/t/4714/n6/all/p/last

## Leitura prática

O projeto fica defensável quando é apresentado como análise de sinais:

- UBS registrada indica estrutura física cadastrada.
- Cobertura APS indica capacidade potencial informada.
- A série APS nacional mostra contexto temporal para a competência mais recente.
- Indicadores por UF e município são agregados territoriais.
- O score é triagem exploratória.
- A sensibilidade dos pesos mostra onde a conclusão é mais ou menos estável.

Essa combinação sustenta um projeto de portfólio com boa ambição analítica, sem vender mais certeza do que os dados permitem.
