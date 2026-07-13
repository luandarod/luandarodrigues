# OSRM local para reprodutibilidade acadêmica

A execução atual da Fase 3/Fase 4 usa `https://router.project-osrm.org`. Isso é suficiente para protótipo e revisão operacional, mas não para uma afirmação acadêmica forte.

## Recomendação

Rerodar as 12 rotas em OSRM local, registrando:

- URL e data do extrato `.osm.pbf`;
- hash SHA-256 do PBF;
- imagem Docker ou versão do binário OSRM;
- perfil usado, por exemplo `car.lua`;
- comandos de preparo;
- timestamp da medição;
- arquivo de saída e metadata.

## Fluxo sugerido com Docker

```powershell
mkdir data\osrm
# Baixar um extrato OSM versionado, por exemplo do Geofabrik, para data\osrm\brasil.osm.pbf
Get-FileHash data\osrm\brasil.osm.pbf -Algorithm SHA256

docker run --rm -t -v "${PWD}\data\osrm:/data" osrm/osrm-backend osrm-extract -p /opt/car.lua /data/brasil.osm.pbf
docker run --rm -t -v "${PWD}\data\osrm:/data" osrm/osrm-backend osrm-partition /data/brasil.osrm
docker run --rm -t -v "${PWD}\data\osrm:/data" osrm/osrm-backend osrm-customize /data/brasil.osrm
docker run --rm -p 5000:5000 -v "${PWD}\data\osrm:/data" osrm/osrm-backend osrm-routed --algorithm mld /data/brasil.osrm
```

Depois:

```powershell
$env:OSRM_BASE_URL = "http://127.0.0.1:5000"
python projects/ubs-healthcare-mapping/scripts/fetch_phase3_osrm_travel_times.py
python projects/ubs-healthcare-mapping/scripts/build_phase3_routing_summary.py
python projects/ubs-healthcare-mapping/scripts/build_telemedicine_phase4_index.py
python projects/ubs-healthcare-mapping/scripts/build_phase4_threshold_sensitivity.py
```

## Interpretação

Mesmo com OSRM local, o resultado continua sendo tempo de carro estimado. Para uma medida de acesso mais forte, a próxima evolução é origem ponderada por população e, se possível, perfis alternativos como caminhada ou transporte público.
