Eu queria sair um pouco da saúde e pegar um problema bem operacional:

quando uma compra online vira experiência ruim?

Usei o dataset público da Olist, com 99.441 pedidos do marketplace brasileiro, para olhar entrega, frete, seller, categoria, pagamento e review na mesma leitura.

A média até parece confortável. O review médio fica em 4,09.

Mas média esconde atrito.

Quando eu separo a operação, a história fica mais concreta. Entregas no mesmo estado levaram, em média, 7,9 dias. Entregas entre estados foram para 15,0 dias. O frete médio também quase dobra: R$ 13 no mesmo estado contra R$ 24 em entregas interestaduais.

E o modelo reforça o que a operação já sugeria. As variáveis mais fortes para risco de review baixo aparecem no caminho logístico: atraso, tempo total de entrega, quantidade de itens, frete, categoria e localização do cliente.

Não li esse projeto como “vamos prever o cliente”.

Li como uma forma de encontrar onde a operação começa a deixar marca na experiência. Atraso, distância, categoria difícil, pedido mais complexo. Tudo isso aparece antes do review ruim.

O modelo de Random Forest chegou a ROC-AUC de 0,759. É útil como camada analítica, mas não como decisão automática. A parte mais importante é menos o score e mais a fila de ação que ele ajuda a organizar:

monitorar atraso antes da reclamação;
separar entregas interestaduais;
olhar categorias com volume e atrito;
criar scorecards de seller com entrega e review juntos.

No fim, o projeto responde uma pergunta simples: a satisfação do cliente não quebra só no atendimento. Muitas vezes ela começa a quebrar na logística.

Repo: https://github.com/luandarodrigues/luandarodrigues/tree/main/projects/olist-ecommerce-experience-analytics

#DataScience #Ecommerce #CustomerExperience #Logistics #Python #MachineLearning #SQL
