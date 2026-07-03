# Colector técnico Oracle para Ley 21.719

Paquete Python de solo lectura que recolecta señales técnicas de seguridad desde Oracle Database y middleware on-premises, además de servicios OCI. Produce un `evidence-bundle.json` trazable para una etapa posterior de análisis.

El colector no emite un veredicto legal, no remedia configuraciones y no constituye asesoría legal.

## Requisitos

- Python 3.9 o superior.
- DBSAT 4.0 o superior para recolección DBSAT.
- OCI Python SDK para OCI.
- `python-oracledb` para consultas opcionales de catálogo.
- Credenciales dedicadas de solo lectura.

Para OCI, usar preferentemente Python 3.9–3.11, rango actualmente soportado por el SDK en Oracle Linux/Ubuntu. El núcleo offline mantiene compatibilidad declarada con Python 3.9 o superior.

## Instalación

Desde la raíz del repositorio:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e 'collector[all]'
collector --help
```

Si solo se procesarán reportes DBSAT o fixtures exportados:

```bash
python -m pip install -e 'collector[dev]'
```

Las dependencias `oci` y `oracledb` se importan de forma diferida. No son necesarias para los tests mockeados.

## Configuración

Copiar `collector.config.example.yaml` y reemplazar identificadores, regiones y rutas. El archivo puede referenciar perfiles OCI, wallets y archivos exportados, pero no puede contener contraseñas, tokens, llaves privadas ni valores de secretos.

```bash
cp collector/collector.config.example.yaml collector.config.yaml
```

Modos OCI admitidos:

- `instance_principal`
- `resource_principal`
- `session_token`
- `config_file`

Orden operacional recomendado: instance/resource principal, session token y, finalmente, config file.

La versión inicial procesa una tenancy OCI por corrida y múltiples regiones y compartments dentro de ella.

### Perfiles por stack y ambiente

El directorio [`configs/`](configs/README.md) contiene perfiles independientes para:

- Base de datos on-premises: DBSAT, SQL directo o ambos.
- Middleware: WebLogic, OHS, OAM, OAA, WebGate, OAG, AVDF o todos.
- OCI: stack completo o perfiles por identidad, datos, cómputo, red, observabilidad y Object Storage.
- Ambiente híbrido on-premises + OCI.

Copie el perfil apropiado a un directorio propio de ambiente (`configs/dev`, `configs/qa` o `configs/prod`), cambie `run.name` y reemplace los valores `[REPLACE_...]`. Los perfiles no contienen secretos y no deben recibir contraseñas, tokens ni llaves privadas.

## Guía de productos y perfiles

Cada perfil habilita solo el producto o la capa indicada. Las rutas siguientes son relativas a `collector/`; puede ejecutarlas desde la raíz del repositorio anteponiendo `collector/` al argumento de `--config`.

### Oracle Database on-premises

| Producto/fuente | Qué recolecta | Perfil |
|---|---|---|
| **DBSAT** | Findings de TDE, redacción/masking, Database Vault, Label Security, auditoría, usuarios, autenticación, parches, TLS, STIG y CIS. Requiere DBSAT 4.0+ o un reporte JSON existente. | `configs/onprem/database/dbsat-only.yaml` |
| **Direct SQL** | Solo vistas allowlist de catálogo: wallet/TDE, auditoría, RMAN, backup, rol de base, Data Guard y RAC. Requiere `python-oracledb`, wallet/external credentials y rol `readonly_monitor` o `select_catalog_role`. | `configs/onprem/database/direct-sql-only.yaml` |
| **DBSAT + Direct SQL** | Combina evaluación DBSAT con estado efectivo del catálogo para una visión on-premises completa. | `configs/onprem/database/database-full.yaml` |

Uso:

```bash
# Solo DBSAT
./collector/run-collector.sh \
  --config collector/configs/onprem/database/dbsat-only.yaml \
  --only dbsat \
  --offline-only

# Solo catálogo SQL
./collector/run-collector.sh \
  --config collector/configs/onprem/database/direct-sql-only.yaml \
  --only direct_sql \
  --offline-only

# Ambos colectores de base de datos
./collector/run-collector.sh \
  --config collector/configs/onprem/database/database-full.yaml \
  --only dbsat \
  --only direct_sql \
  --offline-only
```

### Middleware on-premises

Todos los productos de middleware se leen desde exports JSON locales y exigen `read_config_only: true`; el colector no conduce una consola administrativa ni modifica el dominio.

| Producto | Qué recolecta | Perfil |
|---|---|---|
| **WebLogic** | TLS, protocolos/ciphers, listeners, Node Manager y política de contraseñas del dominio. | `configs/onprem/middleware/weblogic.yaml` |
| **Oracle HTTP Server (OHS)** | SSL/TLS, protocolo mínimo, ciphers y listeners del frontend HTTP. | `configs/onprem/middleware/ohs.yaml` |
| **Oracle Access Manager (OAM)** | MFA, autenticación fuerte y políticas de acceso exportadas. | `configs/onprem/middleware/oam.yaml` |
| **Oracle Advanced Authentication (OAA)** | Señales de autenticación fuerte y factores adicionales. | `configs/onprem/middleware/oaa.yaml` |
| **WebGate** | Integración FIDO/MFA y controles de acceso del agente WebGate. | `configs/onprem/middleware/webgate.yaml` |
| **Oracle API Gateway on-premises (OAG)** | Autenticación en el borde y throttling. | `configs/onprem/middleware/oag.yaml` |
| **Audit Vault and Database Firewall (AVDF)** | Bases monitorizadas, SQL Firewall, bloqueo y señales de auditoría/incidentes. | `configs/onprem/middleware/avdf.yaml` |
| **Middleware completo** | Ejecuta todos los targets anteriores desde sus exports JSON. | `configs/onprem/middleware/middleware-full.yaml` |

Uso de un producto individual:

```bash
./collector/run-collector.sh \
  --config collector/configs/onprem/middleware/weblogic.yaml \
  --only middleware \
  --offline-only
```

Para OHS, OAM, OAA, WebGate, OAG o AVDF cambie la ruta por su perfil. El CLI agrupa todos bajo `middleware`; por eso el archivo seleccionado determina qué producto se ejecuta.

### OCI Identity y gobierno

Perfil: `configs/oci/identity-governance.yaml`

| Producto/servicio | Qué recolecta |
|---|---|
| **OCI IAM** | Usuarios, grupos, políticas y estado MFA; advierte políticas observadas con permisos de escritura. |
| **Cloud Guard** | Resúmenes de problems y targets devueltos por `list_problems` y `list_targets`. |
| **Security Zones** | Zonas devueltas por `list_security_zones`. |
| **OCI Vault/KMS** | Resúmenes de vaults devueltos por `list_vaults`; no lista llaves ni extrae material secreto. |

```bash
./collector/run-collector.sh \
  --config collector/configs/oci/identity-governance.yaml \
  --only oci
```

### OCI Datos y bases gestionadas

Perfil: `configs/oci/database-data-safe.yaml`

| Producto/servicio | Qué recolecta |
|---|---|
| **OCI Data Safe** | Bases registradas y resúmenes de security assessments devueltos por las operaciones de listado registradas. No ejecuta masking, discovery ni auditoría. |
| **OCI Database** | Resúmenes de DB Systems y Autonomous Database. No enumera backups ni configuraciones Data Guard adicionales. |
| **GoldenGate** | Deployments y presencia de replicación. |
| **MySQL HeatWave** | Resúmenes de DB Systems MySQL devueltos por `list_db_systems`. |
| **OCI Database with PostgreSQL** | Resúmenes de DB Systems PostgreSQL devueltos por `list_db_systems`. |
| **NoSQL Database Cloud** | Resúmenes de tablas devueltos por `list_tables`. |

```bash
./collector/run-collector.sh \
  --config collector/configs/oci/database-data-safe.yaml \
  --only oci
```

### OCI Cómputo, almacenamiento y contenedores

Perfil: `configs/oci/compute-storage-oke.yaml`

| Producto/servicio | Qué recolecta |
|---|---|
| **OCI Compute** | Resúmenes de instancias devueltos por `list_instances`; no lista imágenes ni agentes por separado. |
| **Block/Boot Volume** | Resúmenes de volúmenes y boot volumes por compartment/availability domain; no enumera backups. |
| **Oracle Kubernetes Engine (OKE)** | Resúmenes de clusters y node pools devueltos por sus operaciones de listado. |
| **Object Storage** | Resúmenes de buckets y campos disponibles en `list_buckets`, incluido `public_access_type` cuando la API lo devuelve. No lista lifecycle ni retention rules adicionales. |
| **OCI Functions** | Resúmenes de applications y functions, recorriendo primero cada application. |
| **Container Instances** | Resúmenes de container instances devueltos por `list_container_instances`. |

```bash
./collector/run-collector.sh \
  --config collector/configs/oci/compute-storage-oke.yaml \
  --only oci
```

Para recolectar únicamente buckets use `configs/oci/object-storage.yaml`:

```bash
./collector/run-collector.sh \
  --config collector/configs/oci/object-storage.yaml \
  --only oci.object_storage
```

### OCI Red y perímetro

Perfil: `configs/oci/network-perimeter.yaml`

| Producto/servicio | Qué recolecta |
|---|---|
| **VCN/Networking** | Resúmenes de VCNs, subnets y NSGs; no lista route tables ni gateways adicionales. |
| **OCI WAF** | Resúmenes de Web Application Firewalls y WAF policies; no enumera reglas internas de cada policy. |
| **Network Firewall** | Resúmenes de network firewalls; no enumera el contenido de sus policies. |
| **Load Balancer** | Resúmenes devueltos por `list_load_balancers`; no consulta listeners individualmente. |
| **OCI Bastion** | Bastions y contexto de acceso administrado. |
| **OCI Certificates** | Resúmenes de certificados devueltos por `list_certificates`; no enumera CAs por separado. |
| **OCI API Gateway** | Resúmenes de gateways devueltos por `list_gateways`; no consulta deployments ni configuración de autenticación. |

```bash
./collector/run-collector.sh \
  --config collector/configs/oci/network-perimeter.yaml \
  --only oci
```

### OCI Observabilidad, incidentes y recuperación

Perfil: `configs/oci/observability-dr.yaml`

| Producto/servicio | Qué recolecta |
|---|---|
| **OCI Audit** | Eventos recientes y presencia de auditoría del tenant. |
| **OCI Logging** | Log groups devueltos por `list_log_groups`; no enumera logs individuales. |
| **Logging Analytics** | Namespaces y entidades de Logging Analytics. |
| **OCI Monitoring** | Alarmas configuradas, especialmente señales de seguridad. |
| **OCI Events** | Reglas que reaccionan ante cambios o incidentes. |
| **OCI Notifications** | Topics usados para avisos y flujos de respuesta. |
| **Threat Intelligence** | Indicadores disponibles para detección de amenazas. |
| **Full Stack Disaster Recovery** | DR Protection Groups devueltos por `list_dr_protection_groups`; no enumera planes de recuperación. |

```bash
./collector/run-collector.sh \
  --config collector/configs/oci/observability-dr.yaml \
  --only oci
```

### OCI completo e híbrido

| Perfil | Uso |
|---|---|
| `configs/oci/full-stack.yaml` | Ejecuta todos los servicios OCI registrados en las regiones/compartments configurados. |
| `configs/hybrid/onprem-oci-full.yaml` | Combina DBSAT, SQL directo, todos los middleware soportados y OCI completo. |

```bash
# Todo OCI
./collector/run-collector.sh \
  --config collector/configs/oci/full-stack.yaml \
  --only oci

# Stack híbrido completo
./collector/run-collector.sh \
  --config collector/configs/hybrid/onprem-oci-full.yaml
```

Antes de una corrida real, ejecute el mismo comando con `--dry-run`. Un perfil define el alcance máximo; `--only` y `--skip` permiten reducirlo para una corrida concreta.

## Operación

Inventario OCI sin DBSAT:

```bash
collector run --config collector.config.yaml --only oci --skip dbsat
```

Corrida completa:

```bash
collector run --config collector.config.yaml --out ./out
```

Validación y plan sin llamadas de inventario:

```bash
collector run --config collector.config.yaml --dry-run
```

Solo fuentes on-premises:

```bash
collector run --config collector.config.yaml --offline-only
```

Un servicio individual:

```bash
collector run --config collector.config.yaml --only oci.object_storage
```

Los valores de `--only` y `--skip` se pueden repetir o separar por comas.

### Wrapper Bash

El repositorio incluye `collector/run-collector.sh` para ejecutar el mismo CLI mediante opciones largas, sin activar manualmente un entorno virtual:

```bash
./collector/run-collector.sh \
  --config ./collector.config.yaml \
  --out ./out
```

Ejemplos:

```bash
# Validar configuración y mostrar el plan
./collector/run-collector.sh --config ./collector.config.yaml --dry-run

# Ejecutar solo Object Storage y omitir DBSAT
./collector/run-collector.sh \
  --config ./collector.config.yaml \
  --only oci.object_storage \
  --skip dbsat

# Ejecutar solo fuentes on-premises y cifrar el bundle
./collector/run-collector.sh \
  --config ./collector.config.yaml \
  --offline-only \
  --encryption-key-file ./bundle.key
```

Opciones disponibles:

- `--config PATH` — por defecto `./collector.config.yaml`.
- `--out PATH` — por defecto `./out`.
- `--only NAME` y `--skip NAME` — repetibles.
- `--dry-run` y `--offline-only`.
- `--encryption-key-file PATH`.
- `--collector-bin PATH` — fuerza un ejecutable específico.
- `--help` y `--version`.

El wrapper resuelve el ejecutable en este orden: `--collector-bin`, `.venv/bin/collector` en la raíz del repositorio, `collector` disponible en `PATH` y, finalmente, `python3 -m oracle_collector` usando el código local. No instala dependencias ni crea entornos virtuales. Propaga sin cambios el código de salida del colector.

### Códigos de salida

- `0`: corrida completa sin errores.
- `2`: terminó con servicios saltados o errores parciales no fatales.
- `1`: configuración, autenticación u otro error fatal.

Un colector fallido no cancela los demás.

## Salida

```text
out/<run.name>/
├── evidence-bundle.json
├── raw/
│   ├── dbsat/
│   └── oci/<service>/<region>.json
└── collector.log
```

Cada evidencia incluye `layer`, `resource`, `attribute`, `value`, `signal`, controles candidatos, remediaciones candidatas y una referencia a su fuente. `signal` solo admite `present`, `absent`, `unknown` o `misconfigured`; el bundle nunca incluye un `status` legal.

Los contratos están en:

- `schema/evidence-bundle.schema.json`
- `schema/assessment.schema.json`

El segundo schema documenta la salida de la etapa GPT; este paquete no ejecuta esa etapa.

## Redacción y cifrado

`strict` hashea OCIDs y elimina secretos. `minimal` conserva más contexto, pero también reemplaza OCIDs completos. Ambos modos eliminan contraseñas, tokens, autorizaciones, llaves privadas y credenciales embebidas en URI/DSN.

Para cifrar el bundle durante transporte, entregar una llave AES-256-GCM de 32 bytes, cruda o en Base64:

```bash
openssl rand -base64 32 > bundle.key
chmod 600 bundle.key
collector run --config collector.config.yaml --encryption-key-file bundle.key
```

Se crea `evidence-bundle.json.aesgcm` y no se escribe una copia JSON en claro.

## Permisos mínimos OCI

Usar un grupo o dynamic group exclusivo. Punto de partida:

```text
Allow group ComplianceCollectorReaders to inspect all-resources in tenancy
Allow group ComplianceCollectorReaders to read audit-events in tenancy
```

Agregar permisos `read` solo para servicios cuya API no exponga la configuración requerida con `inspect`, y limitar por compartment cuando sea posible. No otorgar `manage`. El colector usa únicamente operaciones list/get/read y advierte cuando observa políticas IAM con verbos `use` o `manage`.

Algunos servicios requieren permisos específicos adicionales, entre ellos Data Safe, Logging Analytics, Threat Intelligence y Full Stack Disaster Recovery. Un permiso faltante queda registrado como error parcial o servicio saltado.

## Permisos mínimos Oracle Database

Usar una cuenta dedicada, nunca `SYS`, `SYSTEM`, `SYSDBA`, `SYSOPER`, `DBA` ni equivalentes. La cuenta debe estar limitada al catálogo requerido, por ejemplo mediante un rol dedicado basado en `SELECT_CATALOG_ROLE`, sin grants sobre esquemas de negocio.

El módulo SQL ejecuta una allowlist fija sobre:

- `V$ENCRYPTION_WALLET`
- `V$ENCRYPTED_TABLESPACES`
- `DBA_AUDIT_MGMT_CONFIG_PARAMS`
- `AUDIT_UNIFIED_POLICIES`
- `V$RMAN_BACKUP_JOB_DETAILS`
- `V$BACKUP`
- `V$DATABASE`
- `V$DATAGUARD_CONFIG`
- `GV$INSTANCE`

La configuración debe usar `role: readonly_monitor` o `select_catalog_role`. La autenticación se resuelve fuera del YAML mediante wallet/external credentials.

## DBSAT

El colector invoca `dbsat collect` y `dbsat report -f json` mediante listas de argumentos y `shell=False`. Rechaza connection strings con passwords embebidos y sesiones privilegiadas. También puede procesar un reporte JSON preexistente mediante `report_path` en el target.

## Middleware

WebLogic, OHS, OAM, OAA, WebGate, OAG y AVDF se leen desde exports JSON locales o datos inyectados por un integrador. Cada target exige `read_config_only: true`. Una URL administrativa sin export local se rechaza: el colector no automatiza cambios ni conduce una sesión remota propietaria.

## Servicios OCI

El registro cubre IAM, Cloud Guard, Security Zones, Vault/KMS, Data Safe, Database, GoldenGate, MySQL, PostgreSQL, NoSQL, Compute, Block/Boot Storage, OKE, Object Storage, Functions, Container Instances, Networking, WAF, Network Firewall, Load Balancer, Bastion, Certificates, API Gateway, Audit, Logging, Logging Analytics, Monitoring, Events, Notifications, Threat Intelligence y Full Stack Disaster Recovery.

Cada cliente pagina respuestas, reintenta throttling HTTP 429 con backoff y degrada de forma segura cuando una operación o permiso no está disponible.

## Desarrollo y validación

```bash
python -m pytest collector/tests
python -m build collector
```

Los tests usan fixtures y dobles del SDK; no necesitan una base Oracle ni una tenancy OCI real.
