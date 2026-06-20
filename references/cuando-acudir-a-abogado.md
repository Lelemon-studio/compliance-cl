# Qué puedes hacer solo vs. qué necesita abogado

La skill genera el 80%. Esta guía separa, en simple, qué resuelves tú y qué reservas para un abogado,
y por qué. La skill DEBE incluir esta separación en el output, marcando cada documento/acción.

## ✅ Lo puedes hacer SOLO (con la skill)
| Acción | Por qué solo |
|---|---|
| Inventario de datos + **RAT** | Es mapear tu propia operación; tú tienes la info. |
| **Borrador** de política de privacidad, DPA, MPD, plan de brechas | Document automation; lícito sin abogado. |
| **Diagnóstico de brechas técnicas** (ARCO, cifrado, MFA, logs, transferencias) | Se audita leyendo el código. |
| **Implementar controles técnicos** (opt-in, endpoints export/delete, MFA, audit log, retención) | Es ingeniería, no derecho. |
| **Llevar los registros** (consentimientos, brechas, accesos) y versionarlos en git | Es disciplina operativa. |
| Designar un **responsable interno** de datos | No requiere título. |

## ⚖️ Necesitas ABOGADO (no lo dejes a la IA)
| Acción | Por qué abogado |
|---|---|
| **Firmar/validar** los documentos finales | Pone responsabilidad profesional → te baja el riesgo y los vuelve defendibles. |
| **Criterio en zonas grises** | Ej.: ¿tu consentimiento *post-hoc* sirve o necesitas opt-in? ¿datos sensibles incidentales? ¿interés legítimo? Son juicios, no datos. |
| **Adaptar el DPA / MPD a tu caso** y a tus contratos con clientes | Redacción contractual con efectos legales. |
| **Defensa en una fiscalización** ante la Agencia o tribunales | Reservado por ley a abogados (patrocinio). La skill NO te representa. |
| **Certificación del MPI** (21.719) / **supervisión externa del MPD** (21.595) | Requiere tercero/abogado; es la pieza que da valor de eximente/atenuante. |
| Confirmar la **numeración exacta de artículos y plazos** contra el texto vigente | Verificación legal formal. |

## Regla de oro
Lo que es **mecánico, técnico y reversible** → tú. Lo que implica **firma, criterio legal, o defensa**
→ abogado. Tener un abogado que **revisó y aprobó** también cuenta como **debida diligencia** (atenuante)
si te fiscalizan.

> Disclaimer: esta skill NO es asesoría legal. Genera borradores y diagnósticos para que un abogado
> valide el tramo que de verdad lo requiere.
