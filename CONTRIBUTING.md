# Contribuir a compliance-cl

¡Gracias por aportar! Este proyecto ayuda a empresas chilenas a preparar su cumplimiento legal.

## Principio rector: todo citado a la ley

Toda afirmación legal **debe** poder contrastarse contra el texto oficial en `sources/` y citar
**ley + artículo + archivo**. Lo que no se pueda confirmar ahí se marca `[verificar contra fuente
oficial]`. No se aceptan afirmaciones normativas basadas solo en blogs o resúmenes secundarios.

## Cómo aportar

- **Corregir un artículo/dato:** cita la fuente oficial (BCN/Diario Oficial) y, si corresponde,
  actualiza `references/mapa-articulos-*.md` con la línea del texto.
- **Agregar un marco nuevo (pack):** crea `packs/<ley>/pack.md` (obligaciones + controles que exige +
  plantillas) y mapea sus controles en `references/controls.md` (crosswalk). Agrega su texto oficial a
  `sources/` con su entrada en `sources/FUENTES.md` (idNorma, URL, SHA-256, comando de re-descarga).
- **Mejorar runbooks/plantillas:** mantén el disclaimer "no es asesoría legal" y marca `[ABOGADO]`
  donde se requiera intervención profesional.

## Estilo

- Contenido en español chileno (el dominio es derecho chileno).
- Documentos generados deben llevar placeholders `[COMPLETAR: ...]` para lo que no se sabe; no inventar
  datos de la empresa.

## Aviso

Este software genera borradores y diagnósticos; **no constituye asesoría legal**. Las contribuciones se
publican bajo la licencia [MIT](LICENSE).
