# Entrega y administración de configuraciones

## Modelo de entrega

- `profiles/onprem/`: plantillas para Oracle Database y Middleware on-premises.
- `profiles/oci/`: plantillas para stacks y servicios OCI.
- `profiles/hybrid/`: plantilla combinada on-premises + OCI.
- `customer-config/`: copias editables propiedad del cliente.

Las 19 plantillas son parte del manifiesto `SHA256SUMS`. No deben editarse. `customer-config/` queda fuera del manifiesto para permitir valores específicos por ambiente y sobrevivir actualizaciones del ejecutable.

## Crear un config por ambiente

```bash
./collector.sh init --profile onprem/middleware/weblogic --environment development
./collector.sh init --profile onprem/middleware/weblogic --environment qa
./collector.sh init --profile onprem/middleware/weblogic --environment production
```

Para elegir otra ubicación:

```bash
./collector.sh init \
  --profile hybrid/onprem-oci-full \
  --config /ruta/segura/collector.production.yaml
```

El launcher rechaza sobrescrituras. Use `--force` sólo cuando haya respaldado y revisado el config actual.

## Datos permitidos

El YAML puede contener OCIDs, regiones, endpoints, aliases y rutas locales requeridas por el collector. No debe contener contraseñas, tokens, claves API, PEM privados ni wallets.

- OCI: preferir instance principal; si se usa un perfil OCI, la clave queda en la ubicación estándar de OCI y sólo se referencia el nombre del perfil.
- Oracle Database: usar variables de entorno o mecanismos externos admitidos por `python-oracledb`; la identidad debe ser de sólo lectura.
- DBSAT y Middleware: referenciar exportaciones o ejecutables locales; no copiar credenciales al perfil.
- Cifrado de salida: entregar la llave por archivo separado y usar `--encryption-key-file`; nunca incorporarla al bundle.

## Control previo

```bash
./collector.sh doctor --config customer-config/production.yaml
```

La ejecución queda bloqueada mientras exista cualquier marcador `[REPLACE_...]` o el esquema del config sea inválido.
