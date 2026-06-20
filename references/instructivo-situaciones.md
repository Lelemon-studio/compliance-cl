# Instructivo: qué hacer ante cada situación (runbooks)

Manual operativo para consultar cuando pase algo. La skill incluye este instructivo en el output
(`<repo>/.compliance/INSTRUCTIVO.md`) para que el founder lo tenga a mano. Cada runbook marca
**[ABOGADO]** donde entra el abogado.

---

## A. Llega un derecho del titular (acceso, rectificación, cancelación, oposición, portabilidad, bloqueo)
**Plazo: responder en 30 días, gratis.**
1. Registra la solicitud (fecha, quién, qué pide) → abre ticket.
2. Verifica identidad del solicitante.
3. Ubica sus datos (BD, backups, proveedores).
4. Ejecuta: **acceso/portabilidad** → exporta en formato estructurado (JSON/CSV);
   **cancelación** → borra o anonimiza (no solo soft-delete); **rectificación/oposición/bloqueo** → aplica.
5. Responde por escrito y **guarda evidencia** de la respuesta.
6. [ABOGADO] solo si la solicitud es dudosa (ej. choca con una obligación legal de conservar).

## B. Brecha de seguridad (acceso no autorizado, fuga, pérdida, alteración)
**Plazo: notificar a la Agencia dentro de 72h si hay riesgo para los titulares.**
1. **Contén** (0–4h): aísla, revoca accesos, rota credenciales. Abre bitácora.
2. **Evalúa** (4–24h): qué datos, cuántos titulares, nivel de riesgo. Si fue un proveedor, exígele info.
3. **Notifica** (antes de 72h): a la **Agencia** (naturaleza, datos, volumen, consecuencias, medidas) y a
   los **titulares** si riesgo alto. Si eres encargado, avisa también al **cliente responsable**.
4. **Cierra**: causa raíz + fix + actualiza RAT y este plan.
5. [ABOGADO] desde el paso 2 para calibrar "riesgo" y redactar las notificaciones. No notificar = gravísima.

## C. Te fiscaliza la Agencia de Protección de Datos
1. **No respondas ad-hoc.** Designa un contacto único + [ABOGADO]. Todo por escrito.
2. **Identifica la etapa:** ¿solicitud de información (preliminar) o **pliego de cargos** (formal)?
3. **Reúne antecedentes:** RAT, evidencia de consentimiento, medidas de seguridad, registro de brechas,
   DPA, evaluaciones de impacto → están en `<repo>/.compliance/`.
4. **Responde en plazo** (confirmar con abogado; estándar ~15 días hábiles), **cargo por cargo**.
5. **Atenuantes:** muestra debida diligencia, remediación, y MPI/MPD revisados por abogado.
6. **Nunca:** ocultar/destruir documentos, ignorar plazos, responder sin abogado.

## D. Cambia la ley o sale un reglamento (ej. DS 662, cláusulas modelo)
1. Actualiza el corpus en `sources/` (re-descarga, ver `sources/FUENTES.md`).
2. Ajusta el pack afectado (`packs/<ley>/pack.md`) y los controles.
3. Re-corre `/compliance-cl` → el `state.json` mostrará qué cambió.

## E. Calendario de revisión (para no quedar obsoleto)
| Cuándo | Qué | Quién |
|---|---|---|
| Anual (o ante cambios) | Revisar y actualizar el **RAT** | Responsable de datos |
| Anual | **Supervisión externa** del MPD (21.595, obligatoria) | [ABOGADO]/consultor externo |
| Anual | Capacitación del equipo | Responsable |
| Al firmar/renovar proveedor | DPA + cláusulas de transferencia | Responsable + [ABOGADO] |
| Cada release relevante | Re-correr `/compliance-cl` (drift) | Dev |

---
*Borradores y guía operativa de compliance-cl. No es asesoría legal; valida con un abogado lo marcado [ABOGADO].*
