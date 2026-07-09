Eu comecei esse projeto com uma pergunta simples:

se o Brasil tem milhares de UBS cadastradas, o que exatamente esse número conta?

A resposta curta: conta estrutura. Mas não conta acesso sozinho.

Então eu fui colocando camadas em cima do cadastro. Primeiro população e território, com IBGE/SIDRA. Depois cobertura potencial da APS. Depois coordenadas, usando malhas municipais do IBGE para testar se cada ponto caía dentro do município declarado. Por fim, entrei com CNES e SIA/SUS para separar cadastro de sinal operacional recente.

Alguns achados que mudaram minha leitura:

47.714 UBS aparecem no cadastro analisado.

43.717 estão dentro do município declarado, o que dá 91,6%. Ainda assim, 2.062 têm coordenada válida no Brasil, mas caem fora do polígono municipal informado.

43.578 aparecem no CNES/ST mais recente.

11.333 combinam presença no CNES/ST com produção ambulatorial registrada no SIA/SUS em 3 competências recentes.

E quando juntei UBS por população, cobertura APS, atividade recente, qualidade espacial e uma proxy territorial de vulnerabilidade, DF, SP e RJ apareceram como sinais estáveis no índice de prioridade.

Isso não quer dizer que esses estados “são os piores”. Também não quer dizer que uma UBS sem produção no SIA esteja fechada. O dado público não permite esse salto.

Mas já muda bastante a conversa.

Uma contagem simples responde “quantas unidades existem no cadastro”.

Uma base cruzada começa a responder perguntas melhores:

onde o cadastro parece consistente?
onde existe sinal recente de produção?
onde a cobertura potencial não conversa tão bem com população e território?
onde vale investigar antes de concluir?

Montei o projeto como um relatório reproduzível, com código, dados processados, gráficos, testes e uma seção bem explícita de limites metodológicos.

Repo: https://github.com/luandarodrigues/luandarodrigues/tree/main/projects/ubs-healthcare-mapping

Imagem: carrossel com o caminho da análise, da contagem bruta ao índice de prioridade.

#DataScience #SaudePublica #AnaliseDeDados #Python #OpenData #SUS #Portfolio
