# Pack: Ley 21.719 — Protección de Datos Personales

> Vigencia **1-dic-2026** (publicada 13-dic-2024). Aplica a todos sin umbral. Gracia MIPYME:
> amonestación en vez de multa los primeros 12 meses (dic-2026 → dic-2027).

## Controles que exige (ver `references/controls.md`)
`gov-responsable` (DPO si aplica), `gov-registro` (RAT), `gov-politicas`, `gov-denuncias`
(canal de contacto/derechos), `data-licitud`, `data-derechos`, `data-info`, `data-minimizacion`,
`data-dpa`, `data-transfer`, `sec-tls`, `sec-rest`, `sec-passwords`, `sec-mfa`, `sec-logs`,
`sec-tenant`, `sec-secrets`, `sec-backups`, `inc-brechas`.

## Obligaciones clave (resumen)
- **Roles:** responsable (decide fines) vs encargado (procesa por cuenta de otro). Un SaaS suele
  ser encargado de los datos de sus clientes y responsable de sus propios leads/usuarios. El
  encargado NO usa los datos para fines propios sin consentimiento aparte.
- **Bases de licitud:** consentimiento opt-in, contrato, obligación legal, interés legítimo.
- **Derechos del titular:** acceso, rectificación, cancelación, oposición, **portabilidad**,
  **bloqueo** — responder en **30 días**, gratis.
- **Deber de información** al captar datos.
- **Seguridad** proporcional: TLS, cifrado en reposo, MFA, logs, segregación por tenant.
- **Brechas (Art. 14 sexies):** reportar **"sin dilaciones indebidas"** (la ley NO fija 72h literal —
  eso es estándar GDPR); **deber de registrar** las vulneraciones; avisar a titulares si afecta datos
  sensibles o de niños/niñas. Si la brecha es de un proveedor, igual notifica el responsable → el DPA
  debe obligar al proveedor a avisar.
- **DPO:** obligatorio solo para organismos públicos o tratamiento de datos sensibles a gran escala.
- **RAT:** registro interno obligatorio (la Agencia puede exigirlo).
- **Transferencias internacionales** (AWS/Railway/Cloudflare/Resend/Google/etc. fuera de Chile):
  requieren mecanismo — adecuación, cláusulas contractuales modelo, RCV, o consentimiento. NOTA: el
  **Ministerio de Economía aprobó cláusulas contractuales modelo en dic-2025** (basadas en RIPD),
  transitorias hasta que la Agencia dicte las suyas. NO basta el DPA del proveedor solo: incorporar
  las cláusulas modelo al contrato + declarar la transferencia en la política.
- **EIPD** ante tratamientos de alto riesgo.

## Sanciones (Art. 34 clasificación + Art. 35 montos — verificado contra el texto)
Leve: amonestación o hasta 5.000 UTM · grave hasta 10.000 UTM · gravísima hasta 20.000 UTM.
Reincidencia (Art. 35): empresas de menor tamaño (Ley 20.416) → 2% o 4% de ingresos anuales del último
año. Gracia MIPYME 12 meses = Art. sexto transitorio. Fiscaliza la Agencia de Protección de Datos.
Ver mapa verificado en `references/mapa-articulos-21719.md`.

## Atenuante
**MPI** (Modelo de Prevención de Infracciones), voluntario, lo certifica la Agencia (no requiere
abogado ni tercero acreditado). Reduce sanciones.

## Documentos a generar (templates/)
- `rat.md` → Registro de Actividades de Tratamiento.
- `politica-privacidad.md` → política para publicar (tras revisión legal).
- `dpa.md` → contrato de tratamiento con clientes/proveedores.
- `plan-respuesta-brechas.md` → procedimiento de notificación 72h.
Se escriben en `<repo>/.compliance/docs/` con prefijo `21719-`.
