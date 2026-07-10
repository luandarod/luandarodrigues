A nota baixa do cliente raramente nasce no momento em que ele escreve o review.

Ela começa antes.

No pedido que atravessa estado.
No frete que fica pesado para uma entrega lenta.
No pacote que demora mais do que deveria.
Na categoria em que expectativa e logística já chegam meio desalinhadas.

Foi isso que fui procurar no dataset público da Olist.

A base tem 99.441 pedidos do marketplace brasileiro. No agregado, tudo parece razoável: review médio de 4,09. Só que média é uma superfície lisa. Ela não mostra onde a operação arranha.

Quando separei as entregas, a diferença apareceu rápido.

Pedidos dentro do mesmo estado levaram, em média, 7,9 dias.
Pedidos entre estados foram para 15,0 dias.

O frete médio também mudou de patamar: R$ 13 no mesmo estado contra R$ 24 em entregas interestaduais.

Depois treinei um modelo para risco de review baixo. O ponto não era "prever o cliente". Cliente não é uma célula obediente numa tabela.

Eu queria ver quais sinais apareciam antes da insatisfação.

E eles vieram do caminho logístico: atraso, tempo total de entrega, quantidade de itens, frete, categoria e localização do cliente.

O Random Forest chegou a ROC-AUC de 0,759. Bom o bastante para servir como camada de leitura. Não bom o bastante para virar decisão automática.

A parte útil está em outra coisa: transformar review ruim em fila de investigação operacional.

Olhar atraso antes da reclamação.
Separar entregas interestaduais.
Acompanhar categorias com volume e atrito.
Juntar seller, entrega e review no mesmo scorecard.

A satisfação do cliente não quebra só no atendimento.

Às vezes ela começa a quebrar no caminho até a porta.

Repo: https://github.com/luandarodrigues/luandarodrigues/tree/main/projects/olist-ecommerce-experience-analytics

#DataScience #Ecommerce #CustomerExperience #Logistics #Python #MachineLearning #SQL
