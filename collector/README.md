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
