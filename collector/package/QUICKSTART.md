# Inicio rápido para clientes

Este paquete no requiere instalar el collector globalmente. Crea un entorno Python privado dentro de `.runtime/` durante la primera validación.

## 1. Verificar la entrega

```bash
./collector.sh verify
./collector.sh version
```

## 2. Elegir y copiar un perfil

```bash
./collector.sh list-profiles
./collector.sh init --profile oci/database-data-safe --environment production
```

El segundo comando crea `customer-config/production.yaml` con permisos `0600`. Las plantillas originales de `profiles/` nunca se modifican.

## 3. Completar la configuración

Edite `customer-config/production.yaml` y reemplace todos los valores `[REPLACE_...]`. No agregue contraseñas, tokens ni llaves privadas al YAML. Use las fuentes de credenciales indicadas en `CONFIGURATION.md`.

## 4. Ejecutar diagnóstico

```bash
./collector.sh doctor --config customer-config/production.yaml
```

`doctor` verifica checksums, placeholders, Python 3.9+, dependencias y configuración del collector. El modo `offline` nunca consulta un índice de paquetes; usa sólo el wheelhouse entregado.

## 5. Recolectar evidencia

```bash
./collector.sh run --config customer-config/production.yaml --out out
```

Opciones útiles:

```bash
./collector.sh run --config customer-config/production.yaml --dry-run
./collector.sh run --config customer-config/production.yaml --only oci
./collector.sh run --config customer-config/production.yaml --skip dbsat
```

La evidencia queda bajo `out/<run.name>/`. Entregue sólo esa carpeta al equipo evaluador; no entregue `.runtime/` ni configs personalizados.
