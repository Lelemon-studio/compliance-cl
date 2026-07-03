# Spec — Colector técnico para stack Oracle (On-Premise + OCI) → insumo GPT de cumplimiento Ley 21.719

> **Estado:** borrador (spec, no implementación).
> **Autor:** compliance-cl.
> **Alcance normativo:** Ley 21.719 (Protección de Datos Personales), con foco en el **deber de
> seguridad (Art. 14 quinquies)** y el mapeo de productos Oracle del **Art. 14** documentado en
> [`specs/ldp.pdf`](ldp.pdf).
> **Fuentes de verdad legal:** [`sources/`](../sources/) + [`references/mapa-articulos-21719.md`](../references/mapa-articulos-21719.md).
> **DISCLAIMER:** el colector NO decide cumplimiento. Solo **recolecta evidencia técnica normalizada**
> para que un modelo (GPT) la analice después contra la ley. No es asesoría legal.

---

## 1. Propósito y no-objetivos

### 1.1 Propósito
Construir un **script de recolección** (read-only) que barra un ambiente Oracle heterogéneo —base de
datos y middleware **on-premise** + productos **OCI** en todas las capas— y produzca un **paquete de
evidencia estructurado (JSON)** que describe, por recurso:

1. **Qué hay desplegado** (inventario: DB, OKE, Compute, WAF, LB, Vault, Object Storage, middleware…).
2. **Cómo está configurado** respecto a los controles de seguridad que la Ley 21.719 exige (cifrado,
   seudonimización, control de acceso, auditoría, respaldo/resiliencia, notificación de brechas).
3. **Qué producto/acción Oracle mitigaría cada brecha**, según el mapeo Art. 14 de [`ldp.pdf`](ldp.pdf).

Ese paquete es el **input del GPT**, que en una segunda etapa emite el diagnóstico y llena el estado
`.compliance/` (ver [`references/output-model.md`](../references/output-model.md)).

### 1.2 No-objetivos (explícitos)
- **No analiza ni puntúa cumplimiento.** No asigna ✅/⚠️/❌ ni score; eso lo hace el GPT/`SKILL.md`.
- **No modifica nada.** Cero `CREATE/ALTER/DROP`, cero cambios de config OCI. Estrictamente read-only.
- **No exfiltra datos personales.** Recolecta **metadata y configuración**, nunca filas de tablas con
  PII (ver §8, Seguridad y privacidad del propio colector).
- **No representa ni certifica.** El monitoreo 24/7 y la supervisión externa quedan fuera (coherente con
  el "Qué no hace" del [`README.md`](../README.md)).

---

## 2. Contexto: qué exige la ley y cómo la satisface el stack Oracle

La lámina de mapeo de [`ldp.pdf`](ldp.pdf) (Art. 14 / Art. 14 quinquies) es el **catálogo de mitigación**.
El colector debe recolectar exactamente la evidencia que permite decidir, para cada requisito, si el
producto que lo satisface está presente y activo.

### 2.1 Requisitos del Art. 14 quinquies (deber de seguridad) → señal técnica a recolectar

| Requisito legal (Art. 14 quinquies) | Control interno ([controls.md](../references/controls.md)) | Señal técnica que el colector debe capturar |
|---|---|---|
| Seudonimización y **cifrado** | `sec-rest`, `data-pseudonym`, `sec-tls` | TDE activo, algoritmo, wallet/KMS; enmascaramiento/redacción; TLS en LB/DB/endpoints |
| Confidencialidad, integridad, disponibilidad, **resiliencia permanente** | `sec-tenant`, `sec-backups`, `sec-monitoring` | Control de acceso (Vault/Label Security/IAM), HA (RAC/DG), replicación, aislamiento |
| **Restaurar disponibilidad** rápido ante incidente | `sec-backups`, `inc-brechas` | Backups (RMAN/ZDLRA/Autonomous Recovery), DR, RTO/RPO, inmutabilidad |
| Proceso de **verificación/evaluación regular** de las medidas | `gov-auditoria`, `sec-logs` | Auditoría (Audit Vault/OCI Audit/Data Safe), DBSAT findings, logging |
| **Acreditar** las medidas ante incidente/juicio (carga de la prueba del responsable) | `gov-registro`, `sec-logs` | Existencia de reportes/auditorías versionables como evidencia |

### 2.2 Mapeo de productos Oracle (del `ldp.pdf`, Art. 14) — embebido como catálogo de remediación

El colector **incluye esta tabla en su salida** (`remediation_catalog`), de modo que el GPT tenga a la
mano, por requisito, qué producto proponer según el tipo de despliegue.

**On-Premise** (láminas 23–24 de `ldp.pdf`):

| Requisito | Producto(s) Oracle |
|---|---|
| Cifrado | Oracle Advanced Security (TDE), Data Masking & Subsetting |
| Seudonimización | Oracle Data Masking & Subsetting, Data Redaction |
| Confidencialidad | Database Vault, Oracle Label Security, OAA + Oracle WebGate + OAM (FIDO) |
| Integridad | Data Masking & Subsetting |
| Disponibilidad | RAC (hasta 18), Active Data Guard, Zero Data Loss Recovery Appliance (ZDLRA) |
| Resiliencia de sistemas | RAC, Active Data Guard, ZDLRA, Exadata |
| Recuperación ante incidentes | RAC, Active Data Guard, ZDLRA |
| Auditorías y evaluaciones | Database Vault, Audit Vault & Database Firewall |

**OCI / Cloud** (láminas 25–27 de `ldp.pdf`):

| Requisito | Producto(s) Oracle |
|---|---|
| Cifrado | Advanced Security, Data Masking & Subsetting, **OCI Data Safe (masking)**, encryption at-rest/in-transit |
| Seudonimización | Data Masking & Subsetting, Data Redaction |
| Confidencialidad | Database Vault, **OCI IAM**, **OCI OAG** (API Gateway) |
| Integridad | Data Masking & Subsetting |
| Disponibilidad | RAC, GoldenGate / GG Cloud, (Active) Data Guard, Autonomous Data Guard, Autonomous Recovery |
| Resiliencia / Recuperación | RAC, Active DG, SEHA, Autonomous Recovery, DB Cloud Backup, **Full Stack Disaster Recovery** |
| Auditorías y evaluaciones | Database Vault, **Audit Vault & Database Firewall**, **OCI Audit**, **OCI Data Safe**, **OCI Logging Analytics**, DB Lifecycle Management Pack |
| **Zero Trust (transversal)** | OCI IAM & Governance, **Network Firewall**, **WAF**, **Threat Intelligence**, **Cloud Guard**, **Logging Analytics** |

**Tiers de resiliencia** (Bronze/Silver/Gold/Platinum, láminas 15–22): el colector infiere y reporta el
tier observado (por RTO/RPO/HA/DR presentes) como `resilience_tier_observed`, para que el GPT lo contraste
con la criticidad del dato (sensible / financiero / niños → exige tier más alto).

---

## 3. Arquitectura

```
                    ┌──────────────────────── collector (read-only) ────────────────────────┐
                    │                                                                        │
   config/auth ───► │  orchestrator  ──►  [ collectors ]  ──►  normalizer  ──►  mapper       │ ──► evidence-bundle.json
                    │                       │                     │              │           │       (+ raw/  DBSAT reports)
                    │                       │                     │              │           │
                    │        on-prem DB ────┤            control-model      Art.14 catalog    │
                    │        on-prem MW ────┤            (controls.md ids)  (ldp.pdf)         │
                    │        OCI (SDK)  ────┘                                                 │
                    └────────────────────────────────────────────────────────────────────────┘
                                                                                              │
                                                                                              ▼
                                                                          (etapa 2, fuera de este spec)
                                                                          GPT / SKILL.md → .compliance/
```

### 3.1 Componentes
- **orchestrator** — lee config, decide qué colectores correr, paraleliza, agrega errores parciales
  (un colector que falla no aborta el resto), sella el bundle con timestamp + versión.
- **collectors/** — un módulo por fuente (§5). Cada uno emite `EvidenceRecord[]` (§6.2) + `raw` opcional.
- **normalizer** — homogeniza a un esquema común (`layer`, `resource`, `attribute`, `value`, `source`).
- **mapper** — sin juicio de cumplimiento: adjunta a cada record los `control_ids` candidatos y las
  entradas de `remediation_catalog` (Art. 14) relevantes. Marca `signal: present|absent|unknown`.
- **writer** — serializa `evidence-bundle.json` + copia los reportes crudos (DBSAT JSON, showoci, etc.).

### 3.2 Lenguaje y dependencias
- **Python 3.9+** (alineado con OCI Python SDK y con el patrón `showoci` del propio SDK).
- **OCI Python SDK** (`oci`) — clientes por servicio; auth por config file, instance principal o
  session token. Prior art recomendado: **ShowOCI** (inventario multi-servicio del SDK).
- **DBSAT 4.0+** — binario externo Oracle; el colector lo **invoca** (`dbsat collect` + `dbsat report
  -f json`) y **parsea el JSON**. No reimplementa DBSAT.
- **oracledb** (python-oracledb, thin mode) — opcional, para queries puntuales read-only de config
  (ej. `V$ENCRYPTION_WALLET`, `DBA_AUDIT_MGMT`, `DBA_TDE_*`) cuando DBSAT no basta.
- Sin dependencias de red externas más allá de los endpoints OCI/DB del propio tenant.

---

## 4. Entradas y configuración

Un archivo `collector.config.yaml` (+ overrides por CLI). Nada de secretos en claro: referencia perfiles
y wallets, no contraseñas embebidas.

```yaml
run:
  name: "acme-prod-2026-07"
  redaction: strict          # strict | minimal  (§8)
  offline_only: false        # si true, no llama OCI; solo on-prem/DBSAT
  parallelism: 8

oci:
  enabled: true
  auth: config_file          # config_file | instance_principal | session_token | resource_principal
  profile: DEFAULT
  config_path: ~/.oci/config
  tenancy_ocid: ocid1.tenancy...
  regions: [sa-santiago-1, sa-vinhedo-1]   # multi-región
  compartments: all          # all | [ocid...]  (recorre subárbol)
  services: all              # all | subset (§5.3)

onprem_db:
  enabled: true
  dbsat:
    binary: /opt/dbsat/dbsat
    targets:
      - { alias: coreprod, connect: "coreprod_reader@//db1:1521/PDB1", wallet: /sec/wallets/coreprod }
    report_formats: [json]   # 4.0: -f json para consumo por herramientas
    exclude_sections: []
  direct_sql:
    enabled: true            # queries de config read-only (no data)
    role: readonly_monitor   # cuenta con SELECT_CATALOG_ROLE, sin acceso a datos de negocio

onprem_middleware:
  enabled: true
  targets:
    - { type: weblogic, admin_url: "t3s://mw1:7002", read_config_only: true }
    - { type: ohs,      config_dir: /u01/ohs/config }
    - { type: oam,      metadata_url: "https://sso/oam/..." }
```

**Modos de autenticación OCI** (en orden de preferencia operacional): instance/resource principal (sin
llaves en disco) > session token > config file. El colector **exige credenciales de solo lectura**
(grupo con policy `inspect`/`read` sobre los compartments objetivo). Si detecta permisos de escritura,
lo **advierte** en el bundle (`warnings`) pero no los usa.

---

## 5. Colectores por capa (qué recolectar)

> Para cada ítem: **layer · recurso · atributos · control_ids · producto Art.14 candidato**.
> "Señal" = qué convierte el dato en evidencia de presente/ausente para el GPT.

### 5.1 On-Premise — Base de datos (DBSAT + SQL de config)

**Vía DBSAT** (`collect` → `report -f json`), extraer los findings de:
- **Cifrado / TDE** → `sec-rest`. Wallet abierto, tablespaces cifrados, algoritmo. Producto: Advanced Security (TDE).
- **Data Redaction / Masking** → `data-pseudonym`. Políticas de redacción activas. Producto: Data Redaction, Data Masking & Subsetting.
- **Database Vault** → confidencialidad/`sec-tenant`. Realms, command rules. Producto: Database Vault.
- **Oracle Label Security** → confidencialidad. Etiquetas activas. Producto: Label Security.
- **Auditoría** (Unified/Traditional Audit, políticas, purge) → `sec-logs`, `gov-auditoria`. Producto: Audit Vault & DB Firewall.
- **Usuarios/privilegios/roles** (cuentas default, privilegios excesivos, DBA sprawl) → control de acceso.
- **Autenticación** (perfiles de password, complejidad, expiración) → `sec-passwords`.
- **Parcheo / versión / CVE-relevantes** → `sec-monitoring` (higiene).
- **Network encryption** (`sqlnet.ora`, native encryption) → `sec-tls`.
- **STIG / CIS findings** (DBSAT 4.0 trae checks STIG) → higiene transversal.

**Vía SQL de config read-only** (complemento, sin tocar datos):
- `V$ENCRYPTION_WALLET`, `V$ENCRYPTED_TABLESPACES` — estado TDE real.
- `DBA_AUDIT_MGMT_CONFIG_PARAMS`, `AUDIT_UNIFIED_POLICIES` — auditoría efectiva.
- **RMAN** / `V$RMAN_BACKUP_JOB_DETAILS`, `V$BACKUP` — respaldos, último éxito, RPO real → `sec-backups`.
- **Data Guard** `V$DATABASE` (`DATABASE_ROLE`, `PROTECTION_MODE`), `V$DATAGUARD_CONFIG` — HA/DR → resiliencia.
- **RAC** `GV$INSTANCE` — nodos activos → disponibilidad.

> ⚠️ La cuenta usada debe ser de **monitoreo/catálogo** (p.ej. `SELECT_CATALOG_ROLE`), nunca una con
> acceso a las tablas de negocio. El colector **rechaza** conectarse con SYSDBA/cuentas de datos.

### 5.2 On-Premise — Middleware

- **WebLogic / OHS**: TLS/SSL configurado (versiones, ciphers), listeners, `NodeManager`, políticas de
  password del dominio → `sec-tls`, `sec-secrets`. Solo lectura de config (MBeans read-only / archivos).
- **OAM / OAA / WebGate (FIDO)**: presencia de MFA/autenticación fuerte, políticas de acceso → `sec-mfa`,
  confidencialidad. Producto Art.14: OAA + WebGate + OAM (FIDO).
- **OAG / API Gateway on-prem**: throttling, auth en el borde → confidencialidad.
- **Audit Vault & Database Firewall (AVDF)**: si existe, qué DBs monitorea, SQL Firewall/blocking →
  `sec-logs`, `sec-monitoring`, `inc-brechas`.

### 5.3 OCI — vía Python SDK (todas las capas)

El colector recorre `regions × compartments` y, por cada servicio, lista recursos y extrae la config
relevante a seguridad. Servicios (subset seleccionable en `oci.services`):

**Identidad y gobierno**
- **IAM** (`IdentityClient`): usuarios, grupos, **políticas**, dominios, dynamic groups, **estado MFA por
  usuario**, API keys antiguas, admins → `sec-mfa`, confidencialidad. Zero Trust: IAM & Governance.
- **Cloud Guard** (`CloudGuardClient`): habilitado sí/no, targets, **problemas abiertos por severidad**,
  recipes/detectores → `inc-brechas`, `sec-monitoring`. Zero Trust: Cloud Guard.
- **Security Zones**: recipes activos sobre compartments → confidencialidad/higiene.
- **Vault / KMS** (`KmsVaultClient`, `KmsManagementClient`): vaults, llaves, rotación, HSM vs software,
  **secretos** en Vault vs hardcodeados → `sec-secrets`, `sec-rest`. Zero Trust: Key Vault.

**Datos / Base de datos**
- **Data Safe** (`DataSafeClient`): registrado sí/no, **security assessment** y **user assessment**
  (findings), **data discovery** (sensitive data), **masking**, **audit collection**, alertas →
  `sec-rest`, `data-pseudonym`, `sec-logs`, `inc-brechas`. Producto Art.14 clave (cloud).
- **Database** (`DatabaseClient`): DB Systems, **ExaCS/ExaDB**, VM DB, **Autonomous DB**; **TDE/encryption**,
  **Data Guard / Autonomous Data Guard**, **backups / Autonomous Recovery / ZDLRA**, **patch level** →
  `sec-rest`, `sec-backups`, resiliencia/recuperación.
- **GoldenGate** (`GoldenGateClient`): deployments/replicación → disponibilidad.
- **MySQL / PostgreSQL / NoSQL** gestionados: cifrado, backups, HA.

**Cómputo y orquestación**
- **Compute** (`ComputeClient`): instancias, imágenes, **estado de encryption de boot volume**,
  `legacy IMDS v1` habilitado, agentes, shapes → higiene, `sec-rest`.
- **Block/Boot Storage** (`BlockstorageClient`): cifrado (llave OCI vs **customer-managed key/CMK**),
  backups, policies → `sec-rest`, `sec-backups`.
- **OKE / Kubernetes** (`ContainerEngineClient`): clusters, **versión**, **API endpoint público vs
  privado**, **RBAC/pod security**, node pools, image signing, secrets encryption → confidencialidad,
  higiene, `sec-secrets`.
- **Object Storage** (`ObjectStorageClient`): buckets **públicos vs privados**, **encryption + CMK**,
  **versioning**, **retention rules / immutability** (anti-ransomware), lifecycle → `sec-rest`,
  `sec-backups`, `inc-brechas`. Zero Trust: Backup inmutable.
- **Functions / Container Instances**: config, subnets, roles.

**Red y perímetro**
- **VCN / Networking** (`VirtualNetworkClient`): VCNs, subnets **públicas/privadas**, **Security Lists /
  NSGs** (reglas 0.0.0.0/0), route tables, IGW/NAT, **DRG**, VPN/FastConnect → confidencialidad,
  segmentación.
- **WAF** (`WafClient`): políticas WAF, reglas, rate-limit, protecciones OWASP → confidencialidad,
  perímetro. Zero Trust: WAF.
- **Network Firewall** (`NetworkFirewallClient`): firewalls, policies → Zero Trust: Network Firewall.
- **Load Balancer** (`LoadBalancerClient`, `NetworkLoadBalancerClient`): **listeners TLS**, versión de
  TLS, ciphers, cert expiry, redirect HTTP→HTTPS → `sec-tls`.
- **Bastion** (`BastionClient`): uso de bastion vs acceso directo, sesiones → confidencialidad, acceso.
- **Certificates** (`CertificatesManagementClient`): certs, **expiración**, CA → `sec-tls`.
- **API Gateway** (`GatewayClient`): auth, TLS → confidencialidad (OAG cloud).

**Observabilidad y auditoría**
- **Audit** (`AuditClient`): retención del audit log del tenant, presencia → `sec-logs`, `gov-auditoria`.
  Producto Art.14: OCI Audit.
- **Logging** (`LoggingManagementClient`): log groups, service/audit/custom logs habilitados → `sec-logs`.
- **Logging Analytics** (`LogAnalyticsClient`): habilitado, fuentes → `sec-monitoring`. Zero Trust.
- **Monitoring / Alarms** (`MonitoringClient`): alarmas de seguridad configuradas → `sec-monitoring`.
- **Events / Notifications** (`EventsClient`, `NotificationDataPlaneClient`): reglas → `inc-brechas`
  (detección/aviso de brechas).
- **Threat Intelligence** (`ThreatintelClient`): habilitado → Zero Trust.
- **Full Stack Disaster Recovery** (`DisasterRecoveryClient`): DR protection groups, planes → resiliencia.

> **Extensibilidad:** un colector nuevo = una entrada en un registro `SERVICE_COLLECTORS`, con el patrón
> `list_all_resources(client, compartment, region) -> EvidenceRecord[]`. Igual que `showoci` agrega
> servicios. Un servicio no soportado nunca rompe la corrida (degradación elegante).

---

## 6. Salida — el "input del GPT"

Un único **`evidence-bundle.json`** (más una carpeta `raw/` con los reportes crudos referenciados). Está
diseñado para ser **auto-contenido**: el GPT no necesita acceso al ambiente, solo este archivo.

### 6.1 Estructura de archivos
```
out/<run.name>/
├── evidence-bundle.json          # el input principal para el GPT
├── raw/
│   ├── dbsat/coreprod.report.json
│   ├── oci/showoci-inventory.json
│   └── oci/<service>/<region>.json
└── collector.log                 # trazas (sin secretos)
```

### 6.2 Esquema de `evidence-bundle.json`
```json
{
  "schema": 1,
  "generated_at": "2026-07-03T12:00:00Z",
  "collector_version": "0.1.0",
  "run": { "name": "acme-prod-2026-07", "redaction": "strict" },
  "environment": {
    "onprem_db": [{ "alias": "coreprod", "version": "19.24", "dbsat_version": "4.0" }],
    "oci": { "tenancy_ocid": "ocid1.tenancy...", "regions": ["sa-santiago-1"], "compartments_scanned": 12 }
  },

  "inventory": [
    { "id": "ocid1.instance...", "layer": "compute", "type": "vm.standard", "region": "sa-santiago-1",
      "compartment": "prod", "name": "app-01" }
  ],

  "evidence": [
    {
      "id": "ev-0007",
      "layer": "database",                    // database | middleware | compute | storage | network | iam | monitoring | oke | waf
      "resource": "coreprod",
      "attribute": "tde_encryption",
      "value": { "wallet_status": "OPEN", "encrypted_tablespaces": 3, "algorithm": "AES256" },
      "signal": "present",                    // present | absent | unknown | misconfigured
      "control_ids": ["sec-rest"],            // ids de references/controls.md (NO veredicto)
      "law_refs": ["Art. 14 quinquies"],      // referencia informativa, verificable en sources/
      "remediation_candidates": [             // del catálogo Art.14 (ldp.pdf) — NO decide, sugiere
        { "product": "Oracle Advanced Security (TDE)", "deployment": "onprem", "applies": "already_present" }
      ],
      "source": { "collector": "dbsat", "ref": "raw/dbsat/coreprod.report.json#/findings/TDE" },
      "confidence": "high"
    },
    {
      "id": "ev-0031",
      "layer": "storage", "resource": "bucket:clientes-export",
      "attribute": "public_access", "value": { "visibility": "public" },
      "signal": "misconfigured",
      "control_ids": ["sec-rest", "inc-brechas"],
      "law_refs": ["Art. 14 quinquies", "Art. 14 sexies"],
      "remediation_candidates": [
        { "product": "Object Storage private + CMK (OCI Vault)", "deployment": "oci", "applies": "recommended" },
        { "product": "Cloud Guard detector", "deployment": "oci", "applies": "recommended" }
      ],
      "source": { "collector": "oci.object_storage", "ref": "raw/oci/object_storage/sa-santiago-1.json" }
    }
  ],

  "remediation_catalog": {                    // tabla Art.14 completa embebida (§2.2), on-prem + cloud
    "source": "specs/ldp.pdf (Art. 14 / 14 quinquies)",
    "onprem": [ { "requirement": "Cifrado", "products": ["Advanced Security (TDE)", "Data Masking & Subsetting"] } ],
    "cloud":  [ { "requirement": "Auditorías", "products": ["OCI Audit", "OCI Data Safe", "Audit Vault & DB Firewall", "Logging Analytics"] } ],
    "zero_trust": ["IAM & Governance", "Network Firewall", "WAF", "Threat Intelligence", "Cloud Guard", "Logging Analytics"]
  },

  "resilience_tier_observed": {               // Bronze/Silver/Gold/Platinum inferido (láminas 15–22)
    "coreprod": { "tier": "silver", "signals": ["Data Guard active", "RMAN daily", "no cross-region DR"] }
  },

  "coverage": {                               // honestidad: qué se pudo y qué no
    "services_scanned": ["iam", "cloud_guard", "data_safe", "object_storage", "..."],
    "services_skipped": [{ "service": "goldengate", "reason": "no permission (inspect denied)" }],
    "warnings": ["IAM user 'ci-bot' tiene permisos de escritura; el colector no los usó"]
  },

  "errors": [ { "collector": "oci.oke", "region": "sa-vinhedo-1", "error": "TimeoutError", "fatal": false } ]
}
```

### 6.3 Contrato con la etapa GPT (segunda etapa, fuera de este spec)
El GPT recibe `evidence-bundle.json` + los packs/`controls.md`/`sources/` y produce el veredicto:
- Por cada `evidence[].control_ids`, asigna estado (✅/⚠️/❌/❓) **con** la evidencia y la remediación.
- Cruza `remediation_candidates` con el `resilience_tier_observed` y la criticidad del dato (sensible/
  financiero/niños) para **priorizar** la acción Art. 14.
- Alimenta `state.json` y `RESUMEN.md` según [`output-model.md`](../references/output-model.md).

> **Regla dura:** el colector deja `signal` (observación técnica), **nunca** `status` (veredicto legal).
> `signal: misconfigured` es un hecho ("bucket público"), no una conclusión de cumplimiento.

---

## 7. Operación (CLI)

```bash
# 1) Solo inventario (rápido, sin DBSAT)
collector run --config collector.config.yaml --only oci --skip dbsat

# 2) Corrida completa
collector run --config collector.config.yaml --out ./out

# 3) Dry-run: valida auth/permisos y lista qué recolectaría, sin llamar a servicios de datos
collector run --config collector.config.yaml --dry-run

# 4) Solo on-prem (ambiente sin OCI)
collector run --config collector.config.yaml --offline-only
```
- **Idempotente y reanudable:** cada colector escribe su `raw/` de forma independiente; re-correr uno
  solo (`--only oci.object_storage`) es válido.
- **Códigos de salida:** `0` ok · `2` completó con colectores saltados/errores no fatales · `>0` fatal
  (auth inválida, config mala). Un error parcial nunca debe abortar la corrida.
- **Rendimiento:** paralelismo por servicio/región con back-off ante throttling del SDK.

---

## 8. Seguridad y privacidad del propio colector

El colector audita cumplimiento de datos: **no puede él mismo ser un riesgo de datos.**

1. **Read-only verificable:** usa credenciales `inspect/read` (OCI) y `SELECT_CATALOG_ROLE` (DB). Si
   detecta que la identidad tiene permisos de escritura, lo reporta en `coverage.warnings` y no los ejerce.
2. **Nunca lee datos de negocio.** DBSAT y las queries son de **catálogo/config**. Prohibido `SELECT` a
   tablas de aplicación. No se extraen filas con PII.
3. **Redacción (`redaction: strict`):** OCIDs se truncan/hashean en el bundle (con mapa reversible solo
   local si `minimal`); connection strings sin password; se **eliminan** secretos, llaves, tokens, valores
   de Vault (solo se reporta *existencia* y *rotación*, no el material).
4. **Sin secretos en logs.** `collector.log` pasa por un filtro de redacción.
5. **Salida cifrable:** opción de escribir `evidence-bundle.json` cifrado (AES-256-GCM) para transporte,
   coherente con `references/build/seguridad.md`.
6. **Reproducible y trazable:** cada `evidence[].source.ref` apunta al `raw/` que lo respalda → auditable,
   igual que `FUENTES.md` hace con la ley.
7. **Consentimiento operacional:** el colector es una herramienta que el propio responsable corre sobre su
   ambiente; no se ejecuta contra terceros.

---

## 9. Entregables de la implementación

1. `collector/` (paquete Python): `orchestrator`, `collectors/{onprem_db,onprem_mw,oci}/*`, `normalizer`,
   `mapper`, `writer`, `redaction`.
2. `collector.config.example.yaml`.
3. `remediation_catalog.json` — la tabla Art. 14 de `ldp.pdf` en datos (fuente única del mapeo).
4. `schema/evidence-bundle.schema.json` — JSON Schema del §6.2 (validación del contrato con el GPT).
5. `README` de operación + matriz de **permisos mínimos** (policy OCI + rol DB).
6. Tests: fixtures de DBSAT JSON y de respuestas del SDK (mocking) → sin necesitar un tenant real.

---

## 10. Preguntas abiertas / a decidir antes de implementar

1. **Alcance middleware:** ¿WebLogic/OAM/OHS entran en v1 o se difiere a v2? (mayor esfuerzo, config
   heterogénea).
2. **`oracledb` directo sí/no:** ¿se permite el complemento SQL de config, o el insumo DB es **solo**
   DBSAT (menos superficie, menos señal)?
3. **Multi-tenancy OCI:** ¿un tenant por corrida o federación de varios?
4. **Verificación legal:** las `law_refs` del bundle son informativas; ¿el GPT las re-verifica contra
   `sources/` (recomendado) o se confía en el colector? (Este spec asume: el GPT verifica).
5. **`resilience_tier` :** ¿la inferencia Bronze/Silver/Gold/Platinum la hace el colector (heurística) o
   se deja como señales crudas para que el tier lo decida el GPT? (Propuesta: colector propone, GPT decide).

---

## 11. Especificación del prompt del GPT (etapa 2 — análisis y priorización)

Esta sección define **cómo se instruye al GPT** que consume el `evidence-bundle.json` del §6. El colector
observa; **el GPT juzga y prioriza**. Para cada hallazgo con remediación, el GPT debe entregar tres
métricas obligatorias: **(1) criticidad, (2) esfuerzo de implementación, (3) costo** — más una prioridad
derivada de las tres. Todo con cita de artículo verificable en `sources/`.

### 11.1 Rol y objetivo del GPT
> Eres un analista de cumplimiento técnico-legal de la Ley 21.719 (Chile). Recibes un paquete de evidencia
> técnica read-only (`evidence-bundle.json`) de un ambiente Oracle on-premise + OCI. Tu tarea NO es
> recolectar: es **evaluar cada hallazgo contra la ley, decidir el estado del control, y puntuar cada
> remediación por criticidad, esfuerzo y costo**, para producir un plan priorizado. No inventas datos ni
> normativa; toda afirmación legal cita **ley + artículo + archivo de `sources/`**; lo no verificable se
> marca `[verificar contra fuente oficial]`. No es asesoría legal (incluir disclaimer).

### 11.2 Entradas del GPT
- `evidence-bundle.json` (§6.2) — inventario, `evidence[]` con `signal`, `control_ids`, `law_refs`,
  `remediation_candidates`, `resilience_tier_observed`, `coverage`.
- `references/controls.md` — catálogo/crosswalk de controles (define qué exige cada marco).
- `packs/ley-21719/pack.md` + `references/mapa-articulos-21719.md` — obligaciones y artículos verificados
  (incluye la clasificación de sanciones Art. 34 y montos Art. 35).
- `remediation_catalog` embebido (mapeo Art. 14 de `ldp.pdf`).
- Contexto de negocio del cuestionario (Fase 0 del `SKILL.md`): tamaño de empresa, rol responsable/
  encargado, si trata **datos sensibles / financieros / de niños**, ingresos anuales (para reincidencia).

### 11.3 Las tres dimensiones (rúbricas)

Cada dimensión se puntúa **1–5** con una etiqueta y una **justificación citada**. Las escalas son fijas y
deterministas para que dos corridas den lo mismo.

#### (1) Criticidad — `criticality` (qué se arriesga legalmente)
Mide la exposición ante la Ley 21.719 si el hallazgo NO se remedia. Se ancla en la clasificación de
infracciones (Art. 34) + montos (Art. 35) y en la sensibilidad del dato.

| Nivel | Etiqueta | Criterio (gatillo) | Referencia legal |
|---|---|---|---|
| 5 | **Gravísima / P0** | Exposición o brecha activa de datos sensibles/financieros/niños; datos personales accesibles sin control (bucket público, sin cifrado, sin auditoría) | Art. 34 gravísima · Art. 35 hasta 20.000 UTM · Art. 14 sexies |
| 4 | **Grave / P1** | Falta un control de seguridad **obligatorio** sobre datos personales (sin TDE, sin MFA admin, sin registro de brechas, sin auditoría) | Art. 34 grave · Art. 35 hasta 10.000 UTM · Art. 14 quinquies |
| 3 | **Media / P2** | Control **parcial** o degradado; medida existe pero incompleta (auditoría sin retención, TLS débil) | Art. 34 leve · Art. 35 hasta 5.000 UTM |
| 2 | **Baja / P3** | Higiene/hardening sin exposición directa de datos personales | buena práctica |
| 1 | **Informativa** | Observación sin impacto de cumplimiento (nota de inventario) | — |

Modificadores: **+1 nivel** si el dato es sensible (Art. 16) o hay usuarios en la UE (GDPR futuro);
**tope 5**. En empresa de menor tamaño con reincidencia, anotar el riesgo **2%/4% de ingresos** (Art. 35).

#### (2) Esfuerzo de implementación — `effort` (cuánto cuesta hacerlo, en trabajo)
Mide el trabajo técnico/organizacional de aplicar la `remediation_candidate` elegida.

| Nivel | Etiqueta | Criterio | Ejemplo |
|---|---|---|---|
| 1 | **XS — toggle** | Cambio de config, horas, sin licencia nueva | Cerrar bucket público; activar OCI Audit; forzar HTTP→HTTPS en LB |
| 2 | **S — habilitar servicio** | Habilitar/registrar un servicio gestionado ya disponible | Registrar DB en Data Safe; activar Cloud Guard; MFA en IAM |
| 3 | **M — feature/integración** | Días–semana; endpoint, política o integración | Endpoints ARCO; políticas WAF; unified audit + retención; NSGs |
| 4 | **L — producto con licencia** | Instalar/licenciar y operar una opción DB | Advanced Security (TDE) on-prem; Database Vault; Audit Vault & DB Firewall |
| 5 | **XL — arquitectura/hardware** | Proyecto; cambio de topología o hardware | ZDLRA; Exadata; Data Guard cross-región; RAC; Full Stack DR |

#### (3) Costo — `cost` (cuánto cuesta en dinero)
Mide el costo económico recurrente/CapEx de la remediación. Se contrasta **contra la multa evitada**
(un control $$ es barato frente a una infracción de 10.000 UTM).

| Nivel | Etiqueta | Criterio | Ejemplo |
|---|---|---|---|
| 1 | **$0 — incluido** | Gratis o ya licenciado; feature nativa | Cerrar bucket; OCI Audit (base); Cloud Guard (base); cifrado at-rest por defecto |
| 2 | **$ — bajo variable** | Costo OCI por uso/target, bajo | Data Safe por target; Logging; Vault/KMS |
| 3 | **$$ — opción/licencia** | Licencia de opción DB o servicio recurrente | Advanced Security; Database Vault; WAF; Logging Analytics |
| 4 | **$$$ — plataforma** | Servicio mayor o edición superior | ExaCS/DBCS Extreme Performance; Autonomous Recovery; AVDF |
| 5 | **$$$$ — CapEx/hardware** | Hardware o rediseño multi-región | ZDLRA appliance; Exadata; DR cross-región |

> El GPT estima el nivel de costo por el **tipo de producto** (no un monto exacto): usa `deployment`
> (onprem/oci) del `remediation_candidate`. Si hay varias candidatas, **elige la de menor costo/esfuerzo
> que cierre la brecha** y anota las alternativas. No inventa precios; expresa banda + "confirmar con
> Oracle/cuenta OCI".

### 11.4 Prioridad derivada (quick-wins primero)
La prioridad ordena el plan: **máximo impacto legal al menor costo/esfuerzo**.

```
priority_score = (criticality * 2) - effort - cost     # rango -8 .. +10
```
- `priority_score ≥ 6` → **P0 / Quick win** (crítico y barato/rápido: hacer ya).
- `3 … 5` → **P1** (importante; planificar en el trimestre).
- `0 … 2` → **P2** (hardening; backlog).
- `< 0` → **P3** (costo/esfuerzo alto vs. impacto; decidir con criterio de negocio, posible aceptación de riesgo documentada).

El peso `×2` a criticidad refleja que **evitar la sanción manda**; empates se rompen por `criticality`
desc, luego `cost` asc. El GPT ordena `assessments[]` por `priority_score` desc.

### 11.5 Esquema de salida del GPT (`assessment.json`)
Extiende `state.json` de [`output-model.md`](../references/output-model.md) con el bloque de priorización.
```json
{
  "schema": 1,
  "generated_at": "2026-07-03T12:30:00Z",
  "input_bundle": "evidence-bundle.json@<sha256>",
  "disclaimer": "No constituye asesoría legal. Borrador fundado en la normativa chilena.",

  "controls": {
    "sec-rest": { "status": "pass", "evidence": "ev-0007", "remediation": "" },
    "inc-brechas": { "status": "fail", "evidence": "ev-0031",
                     "remediation": "Cerrar bucket + CMK + detector Cloud Guard" }
  },
  "frameworks": {
    "ley-21719": { "score": 0.61, "controls_required": 23, "pass": 12, "partial": 4, "fail": 7 }
  },

  "assessments": [
    {
      "id": "as-0031",
      "evidence_id": "ev-0031",
      "control_ids": ["sec-rest", "inc-brechas"],
      "finding": "Bucket 'clientes-export' es público y puede contener datos personales de clientes.",
      "status": "fail",
      "law_ref": { "ley": "21.719", "articulo": "Art. 14 quinquies + Art. 14 sexies",
                   "fuente": "sources/ley-21719-texto.txt", "verificado": true },

      "criticality": { "level": 5, "label": "Gravísima / P0",
                       "rationale": "Datos personales expuestos públicamente; potencial infracción gravísima (hasta 20.000 UTM, Art. 35).",
                       "data_sensitivity": ["financiero"] },
      "effort":      { "level": 1, "label": "XS — toggle",
                       "rationale": "Cambiar visibilidad a privada y activar CMK es configuración; horas." },
      "cost":        { "level": 1, "label": "$0 — incluido",
                       "rationale": "Cerrar el bucket es gratis; CMK vía Vault es costo marginal." },
      "priority_score": 8,
      "priority": "P0",

      "recommended_action": {
        "product": "Object Storage privado + CMK (OCI Vault)",
        "deployment": "oci",
        "steps": ["Set bucket visibility=private", "Habilitar CMK", "Crear detector Cloud Guard para buckets públicos"],
        "alternatives": [{ "product": "Bucket policy restrictiva", "why_not_primary": "no cifra con CMK" }]
      }
    }
  ],

  "plan": {
    "p0_quick_wins": ["as-0031"],
    "p1": [], "p2": [], "p3": [],
    "risk_accepted": []
  },

  "coverage_notes": "Servicios saltados en el bundle (goldengate) → controles marcados ❓, no ❌."
}
```

### 11.6 Plantilla del prompt (system + user)
**System:**
```
Eres analista de cumplimiento de la Ley 21.719 (Chile). Analizas un evidence-bundle.json (evidencia
técnica read-only de un ambiente Oracle on-prem + OCI) y produces un assessment.json.
REGLAS:
- Para CADA evidence con signal ∈ {absent, misconfigured, unknown}, emite un assessment.
- Puntúa SIEMPRE las 3 dimensiones con las rúbricas fijas §11.3: criticality, effort, cost (1–5) + rationale.
- Calcula priority_score = criticality*2 - effort - cost y asigna P0..P3 (§11.4).
- Elige la remediación de menor costo/esfuerzo que cierre la brecha, de remediation_candidates/remediation_catalog.
- Cita ley+artículo+archivo de sources/. Lo no verificable: [verificar contra fuente oficial]. No inventes.
- signal 'unknown' o servicio saltado (coverage.services_skipped) → status ❓, NO ❌.
- No prometas cumplimiento garantizado. Incluye el disclaimer legal.
- Devuelve SOLO el JSON del esquema §11.5.
```
**User:** `<evidence-bundle.json>` + extractos de `controls.md`, `pack.md`, `mapa-articulos-21719.md`,
`remediation_catalog`, y respuestas del cuestionario (sensibilidad, tamaño, ingresos, rol).

### 11.7 Guardrails
- **Determinismo:** rúbricas y fórmula fijas; ante duda, el nivel **más conservador** (mayor criticidad,
  menor certeza de costo). `temperature` baja.
- **No alucinar montos ni artículos:** costo en bandas (§11.3-3), no CLP exactos; artículos solo desde
  `mapa-articulos-21719.md`/`sources/`.
- **Honestidad de cobertura:** lo no observado (servicio saltado, sin permiso) es ❓, nunca ❌ ni ✅.
- **Separación de capas:** el GPT no re-recolecta ni asume datos fuera del bundle + cuestionario.
- **Trazabilidad:** cada assessment referencia su `evidence_id` (→ `source.ref` → `raw/`), cerrando la
  cadena dato técnico → veredicto legal.

---

## Fuentes

- [`specs/ldp.pdf`](ldp.pdf) — mapeo Art. 14 / 14 quinquies ↔ productos Oracle (on-prem + OCI), tiers de resiliencia.
- [`references/controls.md`](../references/controls.md), [`references/mapa-articulos-21719.md`](../references/mapa-articulos-21719.md), [`references/output-model.md`](../references/output-model.md), [`references/build/seguridad.md`](../references/build/seguridad.md), [`packs/ley-21719/pack.md`](../packs/ley-21719/pack.md), [`sources/`](../sources/).
- Oracle DBSAT: [User Guide](https://docs.oracle.com/cd/E93129_01/SATUG/toc.htm) · [DBSAT 4.0 / STIG + JSON output](https://blogs.oracle.com/database/dbsat40) · [ORACLE-BASE DBSAT](https://oracle-base.com/articles/misc/database-security-assessment-tool-dbsat).
- OCI Python SDK: [GitHub oracle/oci-python-sdk](https://github.com/oracle/oci-python-sdk) · [SDK for Python docs](https://docs.oracle.com/en-us/iaas/Content/API/SDKDocs/pythonsdk.htm) · [ShowOCI (inventario multi-servicio)](https://github.com/oracle/oci-python-sdk/blob/master/examples/showoci/README.md) · [CloudGuardClient](https://oracle-cloud-infrastructure-python-sdk.readthedocs.io/en/latest/api/cloud_guard/client/oci.cloud_guard.CloudGuardClient.html).
</content>
</invoke>
