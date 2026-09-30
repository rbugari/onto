# Caso Nalub real

Estado: caso tecnico secundario del MVP operativo; no es el flujo principal de la demo.

## Fuentes

- Schema local: `doc _base/backNalub02042026.sql`.
- Contexto funcional y tecnico: `doc _base/ONTOLOGIA_FUNCIONAL_TECNICA_NALUB.md`.
- Sistema de registro de datos: MariaDB legacy Nalub.
- Sistema de registro ontologico: release Nexo local de ONTO.

El backup se usa para extraer DDL. El runner no importa filas `INSERT` como conceptos ni las publica.

## Ejecucion schema-first

```powershell
python scripts/run_nalub_case.py
```

El caso genera Atlas, Nexo y una release local con bindings tecnicos y un catalogo de cinco consultas:

- `order_status_summary`: pedidos por estado;
- `sales_summary`: ventas mensuales y evolucion, excluyendo pedidos cancelados;
- `product_demand_by_year`: ranking de productos por unidades solicitadas y cantidad de pedidos en un año;
- `customer_debt`: deuda y saldo pendiente de un cliente;
- `product_availability`: stock actual, reservado y disponible.

La ejecucion validada sobre el backup produjo 33 tablas, 255 columnas, 25 relaciones, 451 candidatos y 5 entradas de catalogo.

## Activacion live

Antes de activar datos operativos:

1. Rotar la contraseña que haya sido expuesta fuera del entorno seguro.
2. Crear desde **Administrar proyecto > Conexiones del proyecto** un perfil, por ejemplo `nalub-test`.
3. Confirmar que el usuario MariaDB solo tenga permisos `SELECT`.
4. Ejecutar:

```powershell
python scripts/run_nalub_case.py --live --project-id nalub-case --connection-profile nalub-test
```

El adapter solo ejecuta templates allowlisted, usa consultas `SELECT`, establece la transaccion como read-only, valida parametros y aplica limite de filas. No acepta SQL recibido desde la pregunta del usuario.

La validacion live actual responde estas cinco capacidades:

- pedidos por estado;
- ventas por mes;
- top 10 de productos demandados en 2025, con codigo, unidades y pedidos.
- deuda y saldo pendiente por cliente;
- stock actual, reservado y disponible por producto.

En el dataset validado, el cliente `12` no devolvio filas; esto indica que no existe ese
identificador en la base consultada y no se interpreta como deuda cero. La disponibilidad
devolvio 50 filas, respetando el limite declarado por el catalogo.

El mismo gate verifica que una pregunta fuera de catalogo se abstiene y que una instruccion
SQL directa, por ejemplo `DELETE FROM clientes`, se bloquea antes del routing y no produce
ninguna ejecucion live.

La pregunta de productos se puede probar desde Argos con:

```text
Quiero saber durante el 2025 cuales fueron los 10 productos mas demandados, dame las unidades y los pedidos.
```

La investigacion queda persistida bajo `data/runtime/nalub-case/<release>/<investigation>/` y puede recuperarse desde la UI. La consulta agrupa por id/codigo/nombre de producto; nombres comerciales repetidos corresponden a productos distintos cuando sus codigos son distintos.

Los perfiles se guardan fuera del JSON de Nexo, en `data/connections/<project_id>/<profile_id>.env`. Un proyecto puede tener varios perfiles y el catalogo de cada release declara cual usar.

## Ruta de implementacion

Nalub es un caso de **ruta C** (ONTO como plan B). Los datos viven solo en la MariaDB legacy; Nalub no usa Fabric ni Databricks y la base no se modifica porque la operacion trabaja asi. El paquete de entrega de Nexo lo confirma: para ambas plataformas marca las 33 tablas como fuera de alcance y recomienda la ruta C.

Si en el futuro Nalub adopta una plataforma, la release sirve igual: se agrega un puente a los datos (Copy job con gateway hacia un Lakehouse en Fabric, o Lakehouse Federation en Databricks) y se pasa a la ruta B o A. Ver [Integracion con Fabric y Databricks](15_INTEGRACION_FABRIC_DATABRICKS.md#31-cuando-los-datos-viven-fuera-de-la-plataforma).

## Limites conocidos

- La release inicial aprueba los candidatos del baseline para facilitar la demostracion; en un dominio productivo la aprobacion debe ser humana y selectiva.
- El perfil live debe seguir validando permisos, latencia y nombres fisicos cada vez que cambie el entorno; el backup es una referencia de schema, no una garantia de identidad del servidor.
- La ontologia conserva las inconsistencias documentadas entre `pedidoItems` y `prepedidos_items`, y entre camelCase y snake_case; no las fusiona por inferencia.
