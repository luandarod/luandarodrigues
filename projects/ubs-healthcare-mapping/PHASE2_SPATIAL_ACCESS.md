# Fase 2 — acesso espacial a UBS e farmácias

Este documento registra fontes, decisões, fórmulas e limites da Fase 2. O objetivo é testar a hipótese “difícil chegar à UBS, mas fácil chegar à farmácia” sem confundir cadastro municipal com proximidade espacial.

## Farmácias comuns georreferenciadas

### Fonte

- OpenStreetMap, feições `amenity=pharmacy` no território brasileiro;
- extração via Overpass API com `out center tags`;
- licença ODbL 1.0;
- timestamp da base, endpoint, consulta e data de geração registrados em `osm_pharmacies_metadata.json`.

### Separação conceitual

A camada OSM representa farmácias comuns mapeadas e com coordenadas. Ela não substitui nem identifica a lista oficial do Programa Farmácia Popular. O PFPB permanece como evidência oficial de credenciamento municipal; OSM fornece apenas evidência espacial de uma farmácia próxima.

### Limites

O OpenStreetMap tem completude desigual. Ausência de feição não significa ausência de farmácia. Uma feição pode estar desatualizada, duplicada, fechada ou inadequada para telemedicina. Por isso, distâncias baseadas nessa camada recebem grau de proxy e exigem validação local antes de qualquer piloto.

## Origem municipal e distâncias

### Origem

Para cada município é calculado o centroide do maior polígono da malha municipal simplificada do IBGE. O campo `origin_inside_main_polygon` verifica se o ponto resultante permanece dentro desse polígono. Municípios sem geometria não são imputados.

Esse centroide é geométrico, não populacional. Ele não representa necessariamente a sede, bairros mais habitados ou população rural. A escolha permite uma triagem nacional reproduzível, mas não substitui uma grade populacional.

### UBS

- UBS com coordenadas válidas;
- presença confirmada na competência CNES/ST usada pelo projeto;
- exclusão dos CNES presentes no arquivo de suspeitas da auditoria municipal de coordenadas.

### Distância

As distâncias são de grande círculo, em quilômetros, entre o centroide municipal e o ponto de serviço mais próximo. Elas são limites inferiores geodésicos. Não incorporam ruas, rios, relevo, transporte público, velocidade ou trânsito e nunca recebem o nome de tempo de viagem.

### Sinal “UBS difícil, farmácia fácil”

```text
UBS distante     = distância à UBS >= percentil nacional 75
farmácia próxima = distância à farmácia OSM <= percentil nacional 25
PFPB presente    = ao menos um credenciamento oficial observado no município
```

O sinal exige as três condições. Os limiares e as distâncias individuais ficam publicados no arquivo analítico, evitando uma classificação opaca.

### Resultado da extração

- 5.571 municípios no universo;
- 5.570 com geometria e ambas as distâncias;
- 48 centroides do maior polígono ficaram fora de polígonos côncavos e recebem flag de qualidade;
- 66 municípios satisfazem o sinal relativo de descompasso espacial;
- Boa Esperança do Norte não aparece na malha simplificada anterior à sua criação e permanece ausente;
- Goiânia: 0,41 km até a UBS ativa mais próxima e 0,50 km até a farmácia OSM mais próxima; não satisfaz o sinal espacial.
