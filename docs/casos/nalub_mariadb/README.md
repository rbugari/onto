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
| `input/documentation/NALUB_CONTEXTO_FUNCIONAL_BREVE.md` | Descripcion funcional breve para el discovery simple; no contiene una ontologia prediseñada |
| `input/documentation/ONTOLOGIA_FUNCIONAL_TECNICA_NALUB.md` | Ontologia funcional y tecnica del negocio |

No incluido a proposito:

- el backup completo con datos (`doc _base/backNalub02042026.sql`, fuera de git);
- el perfil de conexion con credenciales: se crea en **Administrar proyecto > Conexiones del proyecto** y queda en `data/connections/nalub-case/` (fuera de git; los scripts no lo borran). Usuario MariaDB con permisos `SELECT` solamente.

## Primer test recomendado: discovery simple

Objetivo: observar que propone ONTO a partir de estructura SQL y una descripcion de para que sirve el sistema, sin darle la ontologia ya resuelta. La sintesis usa todo el inventario disponible, con identificadores cortos solo durante la llamada; al guardar se recuperan las referencias originales. El limite de 90.000 caracteres no se aumenta ni se omiten columnas para entrar en el presupuesto.

1. Crear un proyecto nuevo, por ejemplo **Nalub - Discovery simple**, y abrirlo. No reutilizar ni regenerar `nalub-case`.
2. En Atlas, indicar el ambito **Nalub - gestion comercial**.
3. En Informacion disponible, cargar solamente estos dos archivos:
   - [Esquema SQL sin datos](input/nalub_schema.sql).
   - [Contexto funcional breve](input/documentation/NALUB_CONTEXTO_FUNCIONAL_BREVE.md).
4. Pulsar **Generar borrador de ontologia**. No hace falta registrar sistemas, casos de uso, responsables ni conexiones. La extraccion documental y la sintesis usan el proveedor LLM habilitado; sin proveedor solo se obtienen candidatos locales, no una prueba de respuesta del modelo.
5. Revisar y descargar el borrador. No aprobar candidatos, emitir releases ni abrir conexiones en esta primera prueba.

No cargar el backup con filas ni el documento ontologico completo. Este ultimo queda como referencia del revisor para comparar despues, no como entrada de esta prueba. El documento breve resume un relevamiento de agosto y el SQL es de abril; las diferencias deben quedar como dudas, no corregirse por suposicion.

### Que evaluar en la respuesta

- Inventario completo: 33 tablas, 255 columnas y 25 relaciones fisicas declaradas. Estos numeros describen el SQL, no una cantidad esperada de entidades de negocio.
- Un modelo entendible que represente clientes, pedidos y sus renglones, productos, ingresos de mercaderia y cobros, sin transformar automaticamente cada tabla auxiliar o de respaldo en un concepto principal.
- Diferenciar stock fisico, reservado y disponible; deuda del cliente y saldo de cada pedido; confirmar, procesar y entregar.
- No afirmar que ofertas ya se aplican al pedido ni fusionar pedidos con prepedidos sin confirmacion.
- Preguntas prioritarias sobre ambiguedades relevantes y referencias inspeccionables. Las referencias del modelo son contexto, no evidencia de que su interpretacion sea correcta.
- Todo sigue pendiente de revision. Registrar el draft_id, descargar el JSON y anotar propuestas utiles, errores y preguntas antes de una segunda iteracion.

El ajuste tecnico se valida con respuestas simuladas y datos aislados; no equivale a una validacion semantica del modelo real. No ejecutar el runner de demostracion para este test: automatiza etapas que queremos observar manualmente.

## Recorrido avanzado de referencia (UI)

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
