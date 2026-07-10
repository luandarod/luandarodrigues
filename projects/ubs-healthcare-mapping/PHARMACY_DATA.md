# Camada de farmacias

## Escopo inicial

Esta camada representa estabelecimentos credenciados no Programa Farmacia Popular. Ela nao deve ser usada como sinonimo de todas as farmacias privadas nem como evidencia de estoque ou dispensacao em tempo real.

## Entrada minima

O pipeline aceita CSV ou XLSX. Latitude e longitude sao opcionais, mas apenas registros com coordenadas plausiveis no territorio brasileiro entram no GeoJSON. CNPJ ou CNES sao usados como identificadores quando presentes; registros sem ambos recebem um identificador tecnico local.

## Proveniencia obrigatoria

Antes de publicar uma nova competencia, registre:

- URL oficial de origem;
- data e hora do download;
- competencia ou data de referencia;
- nome original do arquivo;
- licenca ou termos de uso informados pela fonte;
- SHA-256 no manifesto gerado por `build_data_lineage.py`.

## Limites

- Credenciamento nao confirma que o estabelecimento esteja aberto.
- Presenca cadastral nao confirma estoque de medicamentos.
- Coordenada plausivel no Brasil nao confirma o municipio declarado.
- Geocodificacao derivada de endereco deve ser identificada separadamente de coordenada publicada pela fonte.
