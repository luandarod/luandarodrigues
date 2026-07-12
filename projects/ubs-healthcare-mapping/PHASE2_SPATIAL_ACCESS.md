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
