Eu queria que esse projeto respondesse uma pergunta, nao apenas mostrasse um painel:

com os dados publicos disponiveis, onde vale investigar primeiro a rede de UBS?

A resposta que encontrei nao e "onde tem menos UBS". Isso seria simples demais e provavelmente errado.

A resposta mais defensavel e procurar territorios onde varios sinais entram em tensao ao mesmo tempo: quantidade de UBS por populacao, cobertura potencial da APS, atividade recente, qualidade das coordenadas e uma proxy territorial de vulnerabilidade.

Alguns achados mudaram a leitura:

47.714 UBS aparecem no cadastro analisado.

43.717 estao dentro do municipio declarado, o que da 91,6%. Mas 2.062 tinham coordenada valida no Brasil e, ainda assim, caiam fora do poligono municipal informado.

43.578 aparecem no CNES/ST mais recente.

11.333 combinam presenca no CNES/ST com producao ambulatorial registrada no SIA/SUS em 3 competencias recentes.

Quando juntei essas camadas num indice robusto de prioridade, DF, SP e RJ apareceram como sinais estaveis no cenario balanceado e tambem nas analises de sensibilidade.

Essa e a parte mais importante: isso nao prova falta de acesso. Tambem nao prova que uma UBS sem producao recente esteja fechada. O dado publico nao autoriza esse salto.

Mas ele permite uma resposta pratica:

em vez de olhar para o cadastro bruto, da para construir uma fila de auditoria mais inteligente, priorizando os lugares onde estrutura, atividade, cobertura, territorio e qualidade do dado contam historias diferentes.

Foi isso que eu tentei fazer aqui: transformar dados publicos imperfeitos em uma pergunta melhor, uma resposta reproduzivel e limites metodologicos declarados sem maquiagem.

Repo: https://github.com/luandarodrigues/luandarodrigues/tree/main/projects/ubs-healthcare-mapping

Imagem: carrossel com a pergunta, os filtros e a conclusao do projeto.

#DataScience #SaudePublica #AnaliseDeDados #Python #OpenData #SUS #Portfolio
