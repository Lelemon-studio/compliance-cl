# Pack: Ley 21.595 — Delitos Económicos (Modelo de Prevención de Delitos)

> **Ya vigente** (desde 1-sep-2024). Amplía la Ley 20.393: la empresa tiene responsabilidad
> penal autónoma. Aplica a **toda empresa**, sin umbral de tamaño. El **Modelo de Prevención de
> Delitos (MPD)** efectivamente implementado es la defensa (eximente/atenuante) de esa
> responsabilidad. Debe ser **idóneo, eficaz y proporcional** al tamaño — para una startup, un
> documento simple bien hecho basta; no requiere burocracia ni abogado para implementarlo.

## Controles que exige (ver `references/controls.md`)
`gov-responsable` (oficial de cumplimiento), `gov-registro` (matriz de riesgos de delitos),
`gov-politicas` (código de ética), `gov-denuncias` (canal anónimo), `gov-capacitacion`,
`gov-auditoria`, `gov-disciplinario`, `ctrl-interno` (segregación de funciones / autorizaciones).

## Componentes mínimos del MPD
1. **Código de ética y conducta.**
2. **Identificación de riesgos** de delitos por área/proceso (matriz de riesgos).
3. **Controles internos**: procedimientos, autorizaciones, **segregación de funciones**,
   controles financieros (esp. pagos, compras, facturación).
4. **Canal de denuncias anónimo** y protección al denunciante.
5. **Capacitación** periódica al personal.
6. **Oficial/encargado de prevención** designado, con autonomía.
7. **Régimen disciplinario** ante incumplimientos.
8. **Supervisión externa periódica (anual) por un tercero independiente** — la Ley 21.595
   **reemplazó la antigua certificación** por esta supervisión; sin ella el modelo no se considera
   "adecuado" para eximir. Para una micro puede ser un consultor/abogado competente (~UF 3-5).

## Catálogo de riesgo relevante para un SaaS
Foco práctico: **cohecho/soborno** (a funcionarios, en licitaciones), **lavado de activos**
(pagos de origen dudoso), **delitos tributarios** (facturación, IVA), **fraude/administración
desleal**, **delitos informáticos** (acceso indebido a sistemas/datos de terceros), **infracción
a normas de datos** (cruce con Ley 21.719).

## Documentos a generar (templates/)
- `modelo-prevencion-delitos.md` → el MPD maestro (proporcional al tamaño).
- `codigo-etica.md` → código de ética y conducta.
- `matriz-riesgos.md` → identificación de riesgos por proceso + controles.
Se escriben en `<repo>/.compliance/docs/` con prefijo `21595-`.

## Nota
La parte central de la 21.595 es **organizacional**, no de código. Esta skill genera los
documentos base y mapea los controles técnicos relevantes (control de acceso, logs, segregación),
pero la implementación real (designar oficial, operar el canal, capacitar) es del usuario.
