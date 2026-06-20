# Fuentes oficiales (corpus primario)

Objetivo: que la auditoría sea **reproducible y contrastada contra la ley vigente, nada inventado**.
Toda afirmación legal de la skill debe poder rastrearse a uno de estos archivos + el artículo.
Si algo no se puede verificar contra estos textos, se marca `[verificar contra fuente oficial]`.

> Descargado: **2026-06-20**. Re-descargable con los comandos de abajo (User-Agent de navegador).

| Archivo | Norma | idNorma | Tipo | SHA-256 (trunc.) | Fuente oficial |
|---|---|---|---|---|---|
| `ley-21719-diariooficial.pdf` | Ley 21.719 Datos Personales | 1209272 | **PDF texto COMPLETO** | `a760962c…` | Diario Oficial 13-12-2024 |
| `ley-21719-datos.xml` | Ley 21.719 (estructura) | 1209272 | XML abreviado | `4b60e4c8…` | Ley Chile (BCN) |
| `ley-21595-delitos-economicos.xml` | Ley 21.595 Delitos Económicos | 1195119 | XML | `17cac690…` | Ley Chile (BCN) |
| `ley-20393-resp-penal-pj.xml` | Ley 20.393 Resp. Penal PJ | 1008668 | XML | `35d67a14…` | Ley Chile (BCN) |
| `ley-19628-consolidada.xml` | Ley 19.628 (texto base que la 21.719 modifica) | 141599 | XML | `4b4a6d85…` | Ley Chile (BCN) |
| `clausulas-modelo-transferencia-economia.pdf/.txt` | Cláusulas Contractuales Modelo (transferencia internacional) | RAEX202503748 | **PDF + texto** | `55f78aef…` | Diario Oficial 19-12-2025 |

## Notas de validez (IMPORTANTE)
- **La 21.719 MODIFICA la Ley 19.628**: el articulado sustantivo de datos (consentimiento,
  encargado, transferencias, Agencia, sanciones) entra en vigor **1-dic-2026** y se lee del **PDF del
  Diario Oficial** (`ley-21719-diariooficial.pdf`), que es el texto completo. El `ley-19628-consolidada.xml`
  aún NO integra esas modificaciones (vigencia futura) → no usarlo como operativo de la parte nueva.
- Los **XML de Ley Chile (opt=7) son ABREVIADOS** (encabezados/estructura). Para texto íntegro usar el
  PDF del Diario Oficial o el visor de BCN.
- La **21.595 ya está vigente** (modifica la 20.393; rige desde 1-sep-2024).

## Pendientes de incorporar (con URL, aún no descargados)
- **DS 662/2025** (reglamento del Modelo de Prevención de Infracciones, Min. Hacienda/Economía):
  estaba en toma de razón en Contraloría — verificar publicación en Diario Oficial.
- **Guía oficial de implementación**: https://wikiguias.digital.gob.cl/es/datos-personales/guia-datos-personales

> Cláusulas modelo de transferencia: ✅ ya descargadas
> (`clausulas-modelo-transferencia-economia.pdf`, Diario Oficial 19-12-2025).

## Cómo re-descargar (reproducibilidad)
```bash
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36"
# Texto completo Ley 21.719 (PDF Diario Oficial)
curl -L -A "$UA" "https://www.diariooficial.interior.gob.cl/publicaciones/2024/12/13/44023/01/2583630.pdf" -o ley-21719-diariooficial.pdf
# XML estructurado (cambiar idNorma): 21719=1209272, 21595=1195119, 20393=1008668, 19628=141599
curl -L -A "$UA" "https://www.leychile.cl/Consulta/obtxml?opt=7&idNorma=1209272" -o ley-21719-datos.xml
# Cláusulas contractuales modelo (transferencia internacional, Min. Economía)
curl -L -A "$UA" "https://www.diariooficial.interior.gob.cl/publicaciones/2025/12/19/44328/01/2742586.pdf" -o clausulas-modelo-transferencia-economia.pdf
# Verificar integridad
sha256sum *.pdf *.xml
```

## Regla de uso para la skill
1. Antes de afirmar algo legal, búscalo en estos archivos (PDF completo > XML).
2. Cita siempre **ley + artículo + archivo fuente**.
3. Si no está en el corpus o no es verificable, dilo: `[verificar contra fuente oficial / abogado]`.
4. Nunca uses un blog/fuente secundaria como base de una afirmación normativa en el output final.
