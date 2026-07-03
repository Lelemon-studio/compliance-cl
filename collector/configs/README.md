# Perfiles de configuración del colector

Estos perfiles son plantillas independientes para ejecutar una porción concreta del stack Oracle. No contienen credenciales ni identificadores reales. Antes de usarlos, copie el perfil, cambie `run.name` y reemplace cada valor `[REPLACE_...]`.

## On-premises

### Oracle Database

| Perfil | Alcance |
|---|---|
| `configs/onprem/database/dbsat-only.yaml` | Oracle Database mediante DBSAT |
| `configs/onprem/database/direct-sql-only.yaml` | Consultas allowlist de catálogo Oracle |
| `configs/onprem/database/database-full.yaml` | DBSAT y catálogo directo |

### Middleware

| Perfil | Alcance |
|---|---|
| `configs/onprem/middleware/weblogic.yaml` | WebLogic exportado |
| `configs/onprem/middleware/ohs.yaml` | Oracle HTTP Server exportado |
| `configs/onprem/middleware/oam.yaml` | Oracle Access Manager exportado |
| `configs/onprem/middleware/oaa.yaml` | Oracle Advanced Authentication exportado |
| `configs/onprem/middleware/webgate.yaml` | WebGate exportado |
| `configs/onprem/middleware/oag.yaml` | Oracle API Gateway on-premises exportado |
| `configs/onprem/middleware/avdf.yaml` | Audit Vault and Database Firewall exportado |
| `configs/onprem/middleware/middleware-full.yaml` | Todos los middleware soportados |

## OCI

| Perfil | Alcance |
|---|---|
| `configs/oci/full-stack.yaml` | Todos los servicios OCI registrados |
| `configs/oci/identity-governance.yaml` | IAM, Cloud Guard, Security Zones y Vault |
| `configs/oci/database-data-safe.yaml` | Bases gestionadas, Data Safe y replicación |
| `configs/oci/compute-storage-oke.yaml` | Compute, volúmenes, OKE, Object Storage y runtimes |
| `configs/oci/network-perimeter.yaml` | VCN, WAF, firewall, balanceadores, bastion, certificados y API Gateway |
| `configs/oci/observability-dr.yaml` | Audit, logs, alarmas, eventos, notificaciones, amenazas y DR |
| `configs/oci/object-storage.yaml` | Object Storage únicamente |

## Hybrid

| Perfil | Alcance |
|---|---|
| `configs/hybrid/onprem-oci-full.yaml` | Base de datos, middleware y OCI combinados |

## Crear configuraciones por ambiente

Las combinaciones desarrollo/QA/producción son copias de estos perfiles, no perfiles nuevos del producto:

```bash
mkdir -p configs/dev configs/qa configs/prod
cp collector/configs/oci/full-stack.yaml configs/prod/oci-full.yaml
cp collector/configs/onprem/middleware/weblogic.yaml configs/qa/weblogic.yaml
```

En cada copia:

1. Cambie `run.name` por un nombre único, por ejemplo `prod-oci-2026-07`.
2. Reemplace todos los valores `[REPLACE_...]`.
3. Mantenga secretos fuera del YAML; use perfiles OCI, instance/resource principals y wallets/external credentials.
4. Ajuste `regions`, `compartments` y `services` para OCI.
5. Mantenga `read_config_only: true` para middleware.

## Ejecutar perfiles

```bash
# WebLogic QA
./collector/run-collector.sh \
  --config configs/qa/weblogic.yaml \
  --only middleware \
  --offline-only

# Oracle Database on-premises
./collector/run-collector.sh \
  --config collector/configs/onprem/database/database-full.yaml \
  --only dbsat \
  --only direct_sql \
  --offline-only

# OCI Identity y gobierno
./collector/run-collector.sh \
  --config collector/configs/oci/identity-governance.yaml

# Solo Object Storage
./collector/run-collector.sh \
  --config collector/configs/oci/object-storage.yaml
```

## Selección y límites

- `--only dbsat` y `--only direct_sql` distinguen las fuentes de base de datos.
- `--only oci` ejecuta todos los servicios configurados; `--only oci.<service>` selecciona uno.
- El filtro CLI actual agrupa WebLogic, OHS, OAM, OAA, WebGate, OAG y AVDF bajo `middleware`. Para ejecutar uno solo, use su perfil individual.
- Un perfil híbrido se puede recortar con `--only` o `--skip` sin modificarlo.

El wrapper y el parser validan estructura y rutas, pero no sustituyen la revisión de permisos mínimos descrita en `collector/README.md`.
