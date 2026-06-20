---
name: compliance-cl
description: |
  Motor de cumplimiento legal para empresas/SaaS en Chile. Audita un repo contra
  uno o varios marcos (packs) — Ley 21.719 de Datos Personales, Ley 21.595 de
  Delitos Económicos (Modelo de Prevención de Delitos), y extensible a GDPR/ISO
  27001/SOC 2 — usando un catálogo de CONTROLES comunes que mapean a varias leyes a
  la vez. Genera la documentación, evalúa los controles y guarda un ESTADO de
  compliance versionado en el repo (`.compliance/`) que se re-corre en el tiempo y
  muestra avance/drift. Usar cuando el usuario quiera auditar o preparar el
  cumplimiento legal de una app, SaaS o sitio web en Chile.
license: MIT
user-invocable: true
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - Bash
  - AskUserQuestion
---

# compliance-cl — Motor de cumplimiento (Chile), multi-marco y vivo

Auditas una aplicación contra uno o varios **packs** de cumplimiento usando un catálogo
de **controles comunes**, y dejas un **estado de compliance versionado en el repo** que se
re-evalúa en el tiempo (no documentos muertos).

> **DISCLAIMER OBLIGATORIO** — Esta skill NO constituye asesoría legal (un software no asume la
> responsabilidad legal del usuario). Genera borradores y diagnósticos basados en la normativa chilena
> para que un founder cumpla **solo**; un abogado es un plus opcional, no un requisito. Incluye este
> disclaimer al pie de cada documento legal generado.

## Modelo mental (léelo antes de operar)

- **Controles** = unidades reutilizables de cumplimiento (ej. "MFA", "cifrado en reposo",
  "canal de denuncias", "oficial designado"). Un mismo control **satisface varios marcos a
  la vez**. Catálogo + crosswalk: `references/controls.md`.
- **Packs** = una ley/marco cada uno (`packs/<id>/pack.md`): qué obligaciones tiene, qué
  controles exige y qué documentos genera (sus `templates/`).
- **Estado** = el resultado vive en `<repo>/.compliance/` versionado por git. Re-correr la
  skill compara contra el estado anterior y reporta avance/**drift**. Formato: `references/output-model.md`.
- **Fuentes (verdad)** = los textos OFICIALES de las leyes están en `sources/` (ver `sources/FUENTES.md`).
  Toda afirmación legal se contrasta contra ellos y cita **ley + artículo + archivo**; lo no verificable
  se marca `[verificar contra fuente oficial]`. **NADA inventado ni basado en blogs.**

Packs disponibles hoy: `ley-21719` (Datos Personales), `ley-21595` (Delitos Económicos / MPD).

## Flujo

### Fase 0 — Encuadre
1. Muestra el disclaimer.
2. Pregunta/confirma:
   - Repo a auditar (ruta).
   - Qué **packs** activar (por defecto: `ley-21595` + `ley-21719`, los dos obligatorios; `21595`
     ya está vigente).
   - Datos de la empresa: razón social, RUT, domicilio, correo de contacto, tamaño (para
     proporcionalidad y para llenar documentos).
   - Para cada flujo de datos: rol **responsable** vs **encargado** (clave en `ley-21719`).
   Lo que falte queda `[COMPLETAR]`; no inventes datos legales ni de la empresa.
3. Si ya existe `<repo>/.compliance/state.json`, **léelo**: esta corrida es una re-evaluación,
   no un arranque desde cero.

### Fase 1 — Descubrimiento (lee el código, no asumas)
Recorre el repo con Grep/Glob para levantar **evidencia** de cada control del catálogo:
- Datos personales: esquemas/migraciones/modelos, formularios y endpoints de captura
  (`email|phone|telefono|rut|address|direccion|nombre|name|ip|lat|lng|password`).
- Proveedores externos y transferencias internacionales: `.env*`, `package.json`, configs
  (AWS, Railway, Cloudflare, Resend, Google, Vercel, Stripe, Meta, OpenAI/Anthropic...).
- Medidas técnicas: TLS, cifrado en reposo, hashing de password, MFA, logs/auditoría,
  segregación por tenant (`organizationId`/`tenant_id`), secretos fuera del código.
- Gobernanza/organizacional (no está en el código): pregúntalo (oficial designado, canal de
  denuncias, código de ética, capacitación) — marca `❓` lo no verificable por código.

### Fase 2 — Evaluar controles
Para cada control en `references/controls.md`: estado (✅ cumple / ⚠️ parcial / ❌ falta /
❓ no verificable), evidencia (`archivo:línea` o "declarado por el usuario") y remediación.
Un control evaluado se propaga a TODOS los marcos a los que mapea.

### Fase 3 — Generar documentación (por pack activo)
Para cada pack activo, lee su `pack.md` y genera/rellena sus `templates/` con los hallazgos.
Reemplaza todos los placeholders; lo que falte queda `[COMPLETAR: ...]`.

### Fase 4 — Escribir el estado versionado
Escribe en `<repo>/.compliance/` según `references/output-model.md`:
- `state.json` — controles + score por marco + timestamp + commit.
- `docs/` — documentos generados.
- `RESUMEN.md` — postura, top brechas por prioridad, plan, **diff vs la corrida anterior**, y una
  sección **"El abogado es opcional"** (desde `references/cuando-acudir-a-abogado.md`): qué dejó resuelto
  el founder solo y qué es lo único que requeriría abogado (representación si lo fiscalizan).
- `INSTRUCTIVO.md` — runbooks por situación (derecho ARCO, brecha 72h, fiscalización, calendario de
  revisión) desde `references/instructivo-situaciones.md`, para que el founder los consulte.
Sugiere al usuario commitear `.compliance/` (git = audit trail y versionado).

### Fase 5 — Cierre
Reporta la postura por marco y cierra con UN siguiente paso (no un menú). Recuerda que la
revisión de un abogado y la parte organizacional (no-código) siguen siendo del usuario.

## Reglas
- **Fuente de verdad = `sources/` (textos oficiales).** Antes de afirmar algo legal, búscalo ahí;
  cita ley + artículo + archivo. Si no se verifica contra el corpus, marca `[verificar contra fuente
  oficial]`. Nunca uses una fuente secundaria (blog) como base de una afirmación normativa.
- No inventes normativa ni datos de la empresa. `[COMPLETAR]` para lo desconocido, `❓` para
  lo no verificable por código.
- Distingue responsable vs encargado en cada flujo (eje de la 21.719).
- Proporcionalidad: para una startup chica, el MPI/MPD puede ser documento simple bien hecho,
  no burocracia.
- No prometas "cumplimiento garantizado/certificado". Es un borrador técnico + diagnóstico.
- Lo pesado (integraciones que recolectan evidencia sola, OPA en CI, monitoreo continuo) está
  FUERA de alcance hasta que se decida productizar.
