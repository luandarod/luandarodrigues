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

A origem principal é o ponto oficial da sede municipal no produto IBGE “Localidades do Brasil — Censo 2022”, selecionando `Sede Municipal`, `Capital Federal` e o Distrito Estadual de Fernando de Noronha. O centroide do maior polígono da malha simplificada permanece como fallback e campo de auditoria.

A sede representa melhor o núcleo urbano que o centro geométrico, mas ainda não é uma origem ponderada pela população e não representa todos os bairros ou moradores rurais. A escolha permite uma triagem nacional reproduzível, mas não substitui uma grade populacional.

### UBS

- UBS com coordenadas válidas;
- presença confirmada na competência CNES/ST usada pelo projeto;
- exclusão dos CNES presentes no arquivo de suspeitas da auditoria municipal de coordenadas.

### Distância

As distâncias são de grande círculo, em quilômetros, entre o centroide municipal e o ponto de serviço mais próximo. Elas são limites inferiores geodésicos. Não incorporam ruas, rios, relevo, transporte público, velocidade ou trânsito e nunca recebem o nome de tempo de viagem.

### Sinal “UBS difícil, farmácia fácil”

```text
UBS distante     = distância geodésica à UBS >= 5 km
farmácia próxima = distância geodésica à farmácia OSM <= 2 km
PFPB presente    = ao menos um credenciamento oficial observado no município
```

O sinal exige as três condições. Também são publicados cenários de sensibilidade 3/2 km e 10/5 km, além dos percentis nacionais P75/P25 para comparação relativa. Os limites absolutos são regras operacionais conservadoras e não equivalem a 30 minutos de viagem.

### Resultado da extração

- 5.571 municípios no universo;
- 5.571 sedes oficiais e ambas as distâncias;
- 40 municípios satisfazem a regra conservadora 5/2 km;
- 51 satisfazem a sensibilidade 3/2 km e 24 a sensibilidade 10/5 km;
- Goiânia: 1,80 km até a UBS ativa mais próxima e 0,40 km até a farmácia OSM mais próxima; não satisfaz a regra conservadora.
