# MVP operativo de ONTO

Fecha: 2026-09-30
Estado: fuente de verdad para trabajar con la release MVP local

## Decision

ONTO queda definido, para esta etapa, como un MVP operativo local. Se puede usar para preparar evidencia de dominios con uno o varios sistemas, validar conocimiento y hacer consultas controladas. No es todavía una plataforma productiva multiusuario ni un publicador externo.

La release MVP se entrega como una sola aplicacion Streamlit. Atlas, Nexo y Argos son tres productos separados por responsabilidad, flujo, pantallas (`onto_ui/`) y artefactos, pero comparten proyecto, persistencia local y configuracion. El objetivo y el foco del producto estan en [Objetivo, alcance y foco](OBJETIVO_ALCANCE_Y_FOCO.md).

## Para quien es

| Producto | Usuario principal | Pregunta que responde |
| --- | --- | --- |
| Atlas | Analista tecnico o funcional | Que sistemas y evidencia tenemos, como se conectan y que falta? |
| Nexo | Responsable de gobierno o referente de negocio | Que conocimiento aceptamos y podemos versionar? |
| Argos | Usuario de negocio o analista | Que puedo preguntar y que respuesta esta sustentada? |

## Flujo de trabajo

```text
Atlas: preparar evidencia
  -> Nexo: revisar y aprobar conocimiento
  -> Argos: consultar una release aprobada
```

Al entrar, se elige el proyecto en la barra lateral y se confirma en **Contexto de trabajo**. En la barra lateral se indica una vez el **revisor/a de la sesion** (nombre y rol); Atlas y Nexo lo usan en cada decision.

### Atlas: preparar evidencia

La pantalla muestra el avance en cinco pasos (Alcance, Fuentes, Contexto, Diagnostico, Revision) y el siguiente paso sugerido.

1. **Alcance:** cliente, dominio, producto de datos, responsable y casos de uso (pregunta de negocio, responsable, prioridad y sistemas que necesita).
2. **Fuentes:** registrar cada sistema del dominio y cargar su metadata. Formatos: DDL `.sql`, CSV de `information_schema.columns`, `model.bim`, TMDL, PBIP, o conexion directa de solo lectura a Fabric.
3. **Contexto de negocio:** subir glosarios, KPIs, procesos o diccionarios y analizarlos.
4. **Diagnostico:** generar el assessment y revisar puntaje por dimension, brechas, mapa entre sistemas, sistemas evaluados e informe.
5. **Revision:** registrar la decision humana sobre el diagnostico.

Atlas no aprueba una ontologia y no consulta filas de negocio durante el inventario.

### Nexo: validar conocimiento

1. Crear un draft desde un diagnostico Atlas y declarar que define el alcance (tecnica, documentacion o hibrida).
2. **Revision de candidatos:** filtrar, seleccionar en la tabla, ver la evidencia y aprobar, rechazar o volver a pendiente. Hay decision masiva con confirmacion.
3. **Modelo canonico:** proponer vinculos con fuentes, agregar y decidir propiedades, relaciones, sinonimos y restricciones.
4. **Consolidacion:** detectar duplicados, aceptarlos como plan y aplicarlos.
5. **Comparar:** draft contra release o dos releases.
6. **Release y entrega a la plataforma:** emitir la release cuando no quedan pendientes y preparar el paquete para implementarla en Fabric, Databricks u otra plataforma (ruta preferida).

Nexo conserva decisiones trazables. Una release no se emite con pendientes y no publica cambios externos.

### Argos: investigar el negocio

1. Argos usa la release aprobada mas reciente del proyecto.
2. **Conversacion:** escribir una pregunta o elegir una pregunta inicial del catalogo; seguir con las preguntas sugeridas.
3. Cuando existe un binding aprobado, se ejecuta una operacion nombrada y parametrizada; el resultado se muestra como metricas, grafico o tabla.
4. Revisar la evidencia y la trazabilidad de cada respuesta; aceptar la abstencion cuando la pregunta queda fuera del alcance.
5. **Analistas:** revisar el catalogo de consultas autorizadas y ejecutar la bateria de evaluacion.

Argos no acepta SQL libre, no consulta documentos crudos y no inventa una respuesta fuera del context pack aprobado.

## Proyectos validados

| Proyecto | Fuente de datos | Cobertura validada | Resultado |
| --- | --- | --- | --- |
| `fabric-gold-sic-risk-pilot` | Fabric Warehouse, solo lectura | Metadata real, consultas de resumen, riesgos por SIC y detalle `risk_rule_sic` | 4 filas para SIC 12 y 1 fila para regla 1 / SIC 12 |
| `commercial-sales-demo` | `local_synthetic` | `sales_by_customer`, bindings y preguntas respondibles/abstenciones | Demo completa, 5 documentos unicos y evaluacion Argos 2/2 |
| `distribuidora-ventas-distribuidas` | Archivos exportados de 4 sistemas + 1 declarado | Atlas multi-sistema: ERP MariaDB, lakehouse Databricks, Power BI, CRM SQL Server y planillas | 3 entidades compartidas (2 con clave comun), 4 brechas priorizadas |
| `nalub-case` | MariaDB legacy, opcional | Cinco operaciones read-only declaradas | Caso tecnico secundario validado con perfil aislado |

La deduplicacion documental por contenido conserva el primer archivo de cada contenido y se aplica a los runners Risk y Ventas. Los proyectos mantienen sus datos, releases y catalogos separados.

## Que incluye la release MVP

- Aplicacion web local Streamlit.
- Persistencia en JSON y directorios bajo `data/` (o `ONTO_DATA_DIR`).
- Proyectos, snapshots, importacion semantica y carga documental.
- Atlas con varios sistemas por proyecto, casos de uso, inventarios, mapa entre sistemas, evidencia por fragmentos, score y gaps.
- Nexo con drafts, decisiones, modelo canonico, consolidacion, comparacion, releases y context packs.
- Argos con conversacion, historial, abstenciones, trazabilidad y evaluacion.
- Catalogos de consultas allowlisted, parametros validados, limites de filas, preguntas de ejemplo y visualizaciones declaradas.
- Integracion Fabric de metadata y consultas read-only para Risk.
- Carga de metadata externa por archivo (Databricks, SQL Server, PostgreSQL, Snowflake, Oracle, planillas).
- Adapter sintetico para Ventas.
- Adapter MariaDB read-only para Nalub.
- Mappings locales para revision, sin publicacion externa.
- Pruebas automatizadas de servicio e interfaz.

## Que no incluye

- SSO, usuarios, roles tecnicos o autorizacion multiusuario.
- Hosting cloud, API separada, microservicios o base de datos gestionada.
- Descubrimiento remoto de Databricks u otras plataformas distintas de Fabric.
- Sincronizacion continua con Fabric, Databricks u otra plataforma.
- Publicacion o escritura en sistemas externos.
- SQL generado libremente desde una pregunta.
- Aprobacion automatica de conocimiento para uso productivo.
- Garantia de calidad ontologica fuera de la evidencia y las decisiones registradas.

## Criterio de trabajo

La release MVP se considera utilizable cuando se puede repetir el flujo completo de un proyecto, inspeccionar sus artefactos locales y explicar cada respuesta con evidencia o con el resultado de una consulta autorizada. La evolucion posterior se decide a partir del uso de estos flujos, no agregando infraestructura por anticipado.

## Comandos de verificacion

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe -m compileall -q streamlit_app.py onto_ui src tests scripts
.\.venv\Scripts\python.exe scripts\run_distributed_demo.py
.\.venv\Scripts\python.exe scripts\run_commercial_sales_demo.py
```

Para Risk, el flujo guiado conserva las confirmaciones humanas y usa el proveedor LLM `disabled` cuando se busca una ejecucion determinista local.
