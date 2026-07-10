Eu comecei esse projeto tentando responder uma pergunta bem prática:

com os dados públicos que existem hoje, onde faz sentido investigar primeiro a rede de UBS?

Não era para virar só um painel com números. Painel mostra. Eu queria que a análise ajudasse a decidir.

A resposta também não podia ser “onde tem menos UBS”. Isso seria rápido, mas frágil. Uma unidade cadastrada não garante acesso. Uma coordenada no mapa não garante que o ponto esteja certo. E ausência de produção recente no SIA/SUS não prova que uma UBS esteja fechada.

Então eu fui montando a leitura por camadas.

Primeiro, o cadastro: 47.714 UBS.

Depois, território. Das unidades analisadas, 43.717 caem dentro do município declarado, o que dá 91,6%. Mas 2.062 tinham coordenada válida no Brasil e, ainda assim, apareciam fora do polígono municipal informado.

Depois, sinal operacional. 43.578 aparecem no CNES/ST mais recente. Já 11.333 combinam presença cadastral recente com produção ambulatorial registrada no SIA/SUS em 3 competências.

Por fim, cruzei isso com UBS por população, cobertura potencial da APS, qualidade espacial e uma proxy territorial de vulnerabilidade.

Quando rodei o índice de prioridade e testei sensibilidade nos pesos, DF, SP e RJ apareceram como sinais estáveis no topo.

Isso não fecha diagnóstico. E esse cuidado importa.

O que o projeto entrega é uma fila de investigação mais honesta: olhar primeiro para os lugares onde estrutura, atividade recente, cobertura, território e qualidade do dado contam histórias diferentes.

Para mim, essa é a parte mais interessante da análise de dados aplicada a problema público. O dado raramente vem pronto para responder. A resposta aparece quando a gente cruza, testa, desconfia e declara o limite sem tentar parecer mais certo do que é.

Repo: https://github.com/luandarodrigues/luandarodrigues/tree/main/projects/ubs-healthcare-mapping

Imagem: carrossel com a pergunta, os filtros e a conclusão do projeto.

#DataScience #SaudePublica #AnaliseDeDados #Python #OpenData #SUS #Portfolio
