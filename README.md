# compliance-cl

Skill de Claude Code para **auditar y preparar el cumplimiento legal de un SaaS/empresa en Chile**,
contrastado contra el **texto oficial de las leyes** (nada inventado).

> ⚠️ **No es asesoría legal.** Genera borradores y diagnósticos para que un abogado valide el tramo
> que de verdad lo requiere. Estado: **alpha**, en dogfooding.

## Qué hace

Corres `/compliance-cl` sobre un repo y la skill:
1. Te **guía** (encuadre: empresa, rol responsable/encargado, packs a activar).
2. **Lee el código** y mapea qué datos personales toca y a qué proveedores viajan (transferencias).
3. **Evalúa controles** con un catálogo común que mapea a varias leyes a la vez (crosswalk).
4. **Genera la documentación** (RAT, política de privacidad, DPA, plan de brechas, MPD, código de
   ética, matriz de riesgos).
5. Deja un **estado de compliance versionado** en `<repo>/.compliance/` (`state.json` + `docs/` +
   `RESUMEN.md` + `INSTRUCTIVO.md`), re-corrible para ver avance/drift.
6. Te dice **qué llevar a abogado y qué no**, y trae **instructivos por situación** (derecho ARCO,
   brecha, fiscalización).

## Marcos cubiertos (packs)

- **Ley 21.719** — Protección de Datos Personales (vigencia 1-dic-2026).
- **Ley 21.595** — Delitos Económicos / Modelo de Prevención de Delitos (ya vigente).
- Arquitectura extensible: agregar un marco = agregar un `pack` (GDPR, ISO 27001, SOC 2…).

## Fuentes (verdad)

`sources/` contiene el **corpus legal oficial descargado** (PDF del Diario Oficial + XML de Ley Chile),
con `FUENTES.md` (URLs, idNorma, SHA-256, re-descarga) y `mapa-articulos-21719.md` (artículos
verificados línea por línea). Toda afirmación legal cita **ley + artículo + archivo**; lo no verificable
se marca `[verificar contra fuente oficial]`.

## Estructura

```
SKILL.md                      # motor (multi-pack, grounding contra sources/)
references/
  controls.md                 # catálogo de controles + crosswalk
  output-model.md             # formato de .compliance/ (estado versionado)
  cuando-acudir-a-abogado.md  # qué solo vs qué con abogado
  instructivo-situaciones.md  # runbooks (ARCO, brecha, fiscalización)
  mapa-articulos-21719.md     # artículos verificados contra el texto
packs/ley-21719/ , packs/ley-21595/   # obligaciones + plantillas por ley
sources/                      # textos oficiales (PDF/XML/TXT) + FUENTES.md
```

## Instalación

Copiar la carpeta a `~/.claude/skills/compliance-cl/` e invocar con `/compliance-cl`.

---
© 2026 Lelemon SpA. Repositorio privado.
