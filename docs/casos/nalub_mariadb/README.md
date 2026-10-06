# Caso: Nalub (MariaDB legacy real)

| | |
| --- | --- |
| Tipo | Real. Solo estructura y documentacion; **sin datos de filas** |
| Objetivo | Flujo schema-first sobre una base legacy y consultas en vivo de solo lectura desde Argos |
| Ruta esperada | **C** (ONTO como plan B): las 33 tablas viven en MariaDB y Nalub no usa Fabric ni Databricks |
| Regenerar | `python scripts/run_nalub_case.py` (agregar `--keep` para no borrar lo anterior; `--live --connection-profile <perfil>` para validar consultas en vivo) |

## Origenes

| Archivo | Que es |
| --- | --- |
| `input/nalub_schema.sql` | Esquema MariaDB (33 `CREATE TABLE`), extraido del backup del 2026-04-02 sin `INSERT`. Da el mismo resultado que el backup: 33 tablas, 255 columnas, 25 relaciones |
| `input/documentation/ONTOLOGIA_FUNCIONAL_TECNICA_NALUB.md` | Ontologia funcional y tecnica del negocio |

No incluido a proposito:

- el backup completo con datos (`doc _base/backNalub02042026.sql`, fuera de git);
- el perfil de conexion con credenciales: se crea en **Administrar proyecto > Conexiones del proyecto** y queda en `data/connections/nalub-case/` (fuera de git; los scripts no lo borran). Usuario MariaDB con permisos `SELECT` solamente.

## Que cargar en Atlas (UI)

1. **Alcance**: cliente `nalub`, dominio `commercial-operations`, producto `nalub-legacy-mariadb`, con responsable. Casos de uso (los que cubre el catalogo de Argos):
   - Pedidos por estado (alta).
   - Ventas por mes y evolucion (alta).
   - Productos mas demandados por año (media).
   - Deuda y saldo de un cliente (alta).
   - Stock disponible por producto (media).
2. **Fuentes**: sistema "MariaDB legacy Nalub", plataforma MariaDB, con responsable; importar `nalub_schema.sql`.
3. **Contexto**: subir el documento **una vez** y analizar.
4. **Diagnostico**: generar.

## Resultado esperado

Con el script (sin casos de uso ni responsables): **4,0 strong_foundation**.

| Dimension | Puntaje | Lectura |
| --- | --- | --- |
| Metadata tecnica | 4 | Cubierto (sin medidas: no hay modelo BI) |
| Contexto de negocio | 5 | Cubierto |
| Cruce tecnico-negocio | 3 | Casi |
| Gobierno y trazabilidad | 4 | Cubierto |

Brechas: faltan casos de uso (alcance), responsables (gobierno, dos brechas) y revision funcional (negocio). Cargando el caso completo desde la UI, las de alcance y responsable desaparecen.

## Despues de Atlas

- Nexo: 451 candidatos; el script los aprueba como baseline (en un caso productivo la aprobacion es humana y selectiva).
- Release con 5 consultas MariaDB allowlisted: `order_status_summary`, `sales_summary`, `product_demand_by_year`, `customer_debt`, `product_availability`.
- Entrega: el paquete recomienda ruta C para Fabric y Databricks. Detalle en [14_NALUB_REAL_CASE.md](../../14_NALUB_REAL_CASE.md).
