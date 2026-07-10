Peguei o dataset público da Olist porque queria olhar um problema bem pé no chão:

em que ponto uma compra online começa a virar experiência ruim?

A base tem 99.441 pedidos do marketplace brasileiro. Dá para cruzar entrega, frete, seller, categoria, pagamento e review. O tipo de dado que parece simples até você tentar juntar tudo numa leitura só.

A primeira média engana um pouco. O review médio fica em 4,09.

Bonito.

Só que a operação aparece nas bordas. Entregas no mesmo estado levaram, em média, 7,9 dias. Entregas entre estados foram para 15,0 dias. O frete médio saiu de R$ 13 para R$ 24 quando a entrega virou interestadual.

Aí a história muda de tom.

Quando treinei um modelo para risco de review baixo, os sinais mais fortes vieram do caminho logístico: atraso, tempo total de entrega, quantidade de itens, frete, categoria e localização do cliente.

Não li isso como “vamos prever o cliente”.

Cliente não é variável obediente.

Li como uma forma de enxergar onde a operação começa a deixar rastro antes da reclamação aparecer. Atraso. Distância. Pedido mais complexo. Categoria que já carrega expectativa difícil.

O Random Forest chegou a ROC-AUC de 0,759. Útil, mas não mágico. A parte que eu mais usaria numa operação real não é o score isolado. É a fila de atenção que sai dele: olhar atraso cedo, separar entregas interestaduais, acompanhar categorias com volume e atrito, e montar scorecards de seller juntando entrega e review.

No fim, a satisfação do cliente não quebra só no atendimento.

Às vezes ela começa a quebrar no caminho até a porta.

Repo: https://github.com/luandarodrigues/luandarodrigues/tree/main/projects/olist-ecommerce-experience-analytics

#DataScience #Ecommerce #CustomerExperience #Logistics #Python #MachineLearning #SQL
