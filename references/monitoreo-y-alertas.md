# Monitoreo y alertas (setup self-service)

La skill **no es** un servicio de monitoreo 24/7. Lo que hace: **recomendar el stack, generar las reglas
de alerta y ayudar a desplegarlas** sobre herramientas que ya usas o un servicio existente. Así el founder
queda con detección/alertas sin que la skill tenga que "vigilar en vivo".

> Esto cubre la parte de "verificación de filtraciones" que la skill no hace por sí sola, de forma honesta:
> te deja el monitoreo instalado, no lo corre la skill.

## Stack recomendado (favorece lo que ya tienes)
| Necesidad | Recomendación | Nota |
|---|---|---|
| Alertas sobre logs / eventos sensibles | **BetterStack** (Telemetry/Logs) | Ya en uso en las apps → solo agregar reglas + canal Slack/email |
| Secretos filtrados en el repo | **GitHub secret scanning + push protection** (gratis) + Gitleaks/GitGuardian (free tier) | Bloquea commits con secretos |
| Errores en runtime | **Sentry** (free tier) | Captura excepciones |
| Uptime / incidentes | **BetterStack Uptime** | Página de estado + on-call |
| Credenciales/datos filtrados (HIBP) | **Have I Been Pwned** (domain monitoring) | Avisa si aparece tu dominio en una filtración |

Para una startup chica: **BetterStack (alertas) + GitHub secret scanning** cubren el 80% sin costo extra.

## Reglas de alerta sobre el audit log (lo más cercano a "detección" self-service)
Emitir los eventos sensibles del `audit_log` al logger (BetterStack) con un tag, y crear alertas:
- **Borrado masivo** de documentos/comprobantes en poco tiempo.
- **MFA desactivado** en una cuenta.
- **Export masivo** de datos.
- **Acceso/uso de la clave SII** fuera del flujo normal.
- Registro de una **brecha** (`inc-brechas`).
→ Cada alerta dispara a Slack/email del responsable.

## Setup (checklist self-service)
1. [ ] Conectar el logger a BetterStack (si no lo está).
2. [ ] Emitir los eventos sensibles del audit log con un campo `alert: true` o un tag.
3. [ ] Crear las reglas de alerta arriba en BetterStack + canal de aviso.
4. [ ] Activar GitHub secret scanning + push protection en el repo.
5. [ ] (Opcional) Sentry para errores; HIBP para tu dominio.
6. [ ] Documentar quién recibe las alertas y qué hace (enlaza con el plan de respuesta a brechas).

## Límite honesto
Esto es **detección y alerta**, no DLP completo ni un SOC. Para vigilancia avanzada (exfiltración,
correlación, respuesta automática) hay productos dedicados; esto te deja una primera línea real y barata.
