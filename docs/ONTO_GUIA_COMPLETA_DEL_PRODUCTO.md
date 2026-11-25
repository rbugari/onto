# ONTO: guía completa del producto

Qué es, para qué sirve, cómo piensa, cómo trabaja y cómo se integra con lo que ya tenés.

Estado: 2026-11-25. Pensada para leerse de corrido o por perfil. Fuente de verdad del producto: esta carpeta `docs/`.

## Cómo leer esta guía

| Si sos... | Leé... |
| --- | --- |
| Dirección o negocio | 1, 2, 3, 4, 8 y 10. |
| Responsable de datos o arquitectura | 1 al 9 y 11. |
| Equipo técnico que va a operarlo | 5, 6, 7, 9, 11 y 12 (y el anexo de documentos). |
| Alguien que evalúa el mercado | 2, 7, 10 y 11. |

---

## 1. ONTO en un minuto

> **ONTO prepara el conocimiento de negocio que las plataformas necesitan y no pueden generar solas: llega a Silver, cruza varios sistemas y lo entrega aprobado, listo para cargar.**

Una ontología es el "manual de significados" de una empresa: qué es un cliente activo, qué tabla lo representa, cómo se cruza entre sistemas, quién lo aprobó y qué no se debe responder. Los agentes de IA fallan menos por falta de datos que por falta de ese significado confiable.

ONTO es una herramienta que toma lo que ya existe (la estructura de las bases de datos, los modelos de BI, la documentación) y produce ese manual **con evidencia, revisado por personas y listo para cargar** en Microsoft Fabric, Databricks u otra herramienta.

**Lo que ONTO es:**

- Un acelerador del trabajo previo: relevar, cruzar sistemas, proponer, validar y entregar.
- Un formato de trabajo portable que se traduce a cada plataforma.
- Un banco de prueba para comprobar que el conocimiento aprobado responde bien.

**Lo que ONTO no es:**

- No reemplaza la ontología de Fabric ni la de Databricks, ni el catálogo, ni el gobierno de datos del cliente.
- No es un agente de preguntas de negocio en producción.
- No aprueba nada por su cuenta: una inferencia de IA es una propuesta, nunca un hecho.

---

## 2. El problema

### 2.1 Datos sí, significado no

Casi toda organización tiene datos. Lo que falta es el significado compartido. Ese conocimiento existe, pero está:

- **Distribuido** en varios sistemas (ERP, lakehouse, CRM, modelos de BI, planillas).
- **Implícito** en nombres de columnas, modelos y documentos desiguales.
- **Sin dueño ni aprobación** explícitos.
- **Sin puntos de cruce declarados**: la misma entidad tiene nombres y claves distintas en cada sistema.

### 2.2 Qué hacen hoy las plataformas y dónde dejan huecos

Fabric IQ (Microsoft) y Databricks avanzan rápido en capas semánticas y ontologías. Estado verificado en su documentación oficial el 2026-11-24:

| | Microsoft | Databricks |
| --- | --- | --- |
| Modelo semántico / métricas | Modelos semánticos de Power BI; *semantic views* (preview) | Metric views, dominios, Pages |
| Ontología | **Ontology (preview)**: entidades, propiedades, relaciones, reglas, métricas; la genera desde modelos semánticos y con un agente que propone y espera revisión | **Genie Ontology**: conocimiento *modelado* (Pages, metric views, certificación) más conocimiento *aprendido* de consultas y dashboards |
| Formatos abiertos | Importa y exporta RDF/Turtle/OWL (solo en una ontología vacía); alineado con Apache Ossie | Servidor MCP; fuentes externas (Power BI) en Beta |

Pero esas herramientas tienen tres límites que ONTO cubre:

1. **Parten de la capa Gold y de su propio ecosistema.** Cuando hay que bajar a Silver o Bronze, o hay datos en un ERP, un CRM o un legacy fuera de la plataforma, no ven ese significado.
2. **Alguien tiene que escribir el contenido.** Definiciones, sinónimos, reglas, descripciones de tablas y columnas no aparecen de la nada.
3. **Cada una ve solo su mundo.** Ninguna puede declarar que "Cliente" en el ERP es "Cuenta" en el CRM y "DimCustomer" en el lakehouse.

Por eso ONTO **no compite**: hace el trabajo previo que esas plataformas necesitan y se integra con ellas.

---

## 3. Qué valor agrega

| Valor | Qué significa en la práctica |
| --- | --- |
| **Visión completa del dominio** | Un solo lugar donde se ven todos los sistemas del dominio, qué entidades comparten, con qué clave se cruzan y qué falta. |
| **Llega donde las plataformas no llegan** | Silver, Bronze y sistemas externos quedan relevados, no solo Gold. |
| **Contenido listo para cargar** | Definiciones, sinónimos, propiedades con tipo, relaciones, reglas y joins, propuestos con evidencia y aprobados por personas. |
| **Confianza** | Cada elemento aprobado se rastrea hasta su fuente (archivo, hash, fragmento) o a una decisión humana. |
| **Decisión informada sobre dónde implementar** | Dice qué parte puede implementar cada plataforma hoy y qué puente hace falta (ruta A, B o C). |
| **Portabilidad** | El conocimiento aprobado no queda atado a una plataforma: se entrega a Fabric, Databricks o en formatos abiertos (OWL, Ossie). |
| **Prueba antes de implementar** | Un banco de prueba con preguntas reales (y preguntas que debe negarse a contestar) valida el contexto antes de cargarlo. |

**Para quién:** equipos de datos, consultoras y áreas de gobierno que tienen que preparar un dominio para agentes de IA, sobre todo cuando está repartido en varias plataformas o hay mucho conocimiento sin documentar.

**Cuándo agrega menos:** si todo vive en una sola plataforma y ya está en Gold con modelos semánticos bien definidos, las herramientas nativas alcanzan. ONTO no intenta competir ahí.

---

## 4. Cómo piensa ONTO: los principios

1. **Evidencia antes que inferencia.** Todo elemento conserva su fuente. Una hipótesis basada solo en nombres no cuenta como explicación.
2. **Una persona aprueba.** La IA propone; solo una persona aprueba. Nunca hay aprobación automática de conocimiento.
3. **La plataforma del cliente primero.** Lo aprobado se implementa en la plataforma del cliente siempre que sea viable. ONTO solo sostiene lo que la plataforma no puede.
4. **Dominio completo, no una plataforma.** Se inventarian todos los sistemas del dominio en un mismo proyecto.
5. **Abstención como capacidad.** Es mejor decir "no sé" que inventar. El banco de prueba se niega a responder fuera de lo aprobado y nunca ejecuta SQL libre.
6. **Reproducible.** Cada diagnóstico y cada release se pueden reconstruir desde sus manifiestos, con identificadores y hashes.
7. **Mínimo privilegio.** Se trabaja con metadata por defecto. No modifica sistemas fuente, no copia datos de negocio si alcanza con metadata o una referencia autorizada, y no guarda secretos.
8. **Simple de operar.** Una sola aplicación local, sin infraestructura adicional, pensada para equipos chicos y consultoría.

---

## 5. Cómo trabaja: el recorrido

```text
Sistemas + documentación
        |
        v
  ATLAS  (¿cómo estamos?)        diagnóstico: qué sistemas, qué evidencia, qué falta,
        |                         cómo se conectan, qué puede implementar cada plataforma
        v
  NEXO   (¿qué aprobamos?)       revisión humana, modelo canónico, release aprobada
        |
        +--> PAQUETE para Fabric / Databricks / formatos abiertos   (entrega preferida)
        |
        +--> ARGOS (¿funciona de verdad?)   banco de prueba con preguntas reales
```

### 5.1 La entrada simple

En la aplicación, el recorrido más corto es:

1. Crear un proyecto e indicar un **ámbito** (por ejemplo, "Pedidos y deuda de clientes").
2. Subir los archivos disponibles: estructura de bases (SQL, CSV de `information_schema`, `model.bim`, TMDL, PBIP) y documentación (Markdown, PDF, Word, Excel, HTML...).
3. Pulsar **Generar borrador de ontología**.
4. Revisar la propuesta en **Nexo**, aprobar o rechazar, emitir la **release** y generar el **paquete** para la plataforma.

El detalle avanzado (alcance, casos de uso, fuentes por sistema, diagnóstico) sigue disponible dentro de "Detalle avanzado".

### 5.2 Atlas: preparar la evidencia

Atlas responde "¿cómo estamos?". No aprueba nada ni consulta filas de negocio.

- **Inventaria sistemas** (cada uno con plataforma, responsable, formato y hash) y sus objetos.
- **Lee la documentación** y extrae términos, definiciones, reglas y KPI, siempre con el fragmento de origen.
- **Cruza sistemas:** detecta entidades presentes en más de un sistema y la clave común (`cliente_id`, `CustomerKey`...), o la falta de ella.
- **Clasifica por capa:** Bronze, Silver o Gold, por declaración o por nombres.
- **Evalúa alcance por plataforma:** qué sistemas puede alcanzar Fabric y cuáles Databricks, con el puente sugerido (Mirroring, shortcut, Lakehouse Federation, ingesta), y calcula la ruta A, B o C.
- **Mide:** un puntaje basal de 0 a 5 por dimensión, brechas priorizadas por caso de uso y cuánto del alcance se puede explicar con evidencia.
- **Entrega** un paquete de diagnóstico reproducible y un informe.

Sus resultados son heurísticos y orientativos: las equivalencias entre sistemas, la capa y el alcance los confirman los responsables.

### 5.3 Nexo: validar el conocimiento

Nexo responde "¿qué aprobamos?".

- Convierte la evidencia en **candidatos**: conceptos, reglas, KPI, propiedades, relaciones, sinónimos.
- Una persona **aprueba, rechaza o deja pendiente**, con su motivo. La decisión queda registrada.
- **Consolida duplicados** (por ejemplo `Prepedido`, `Pre-pedido`, `Pre pedido`) como sugerencias pendientes de revisión; nunca fusiona solo.
- Emite una **release**: una versión aprobada, inmutable y reconstruible. No se puede emitir con pendientes.
- Permite **actualizar sin perder** lo ya decidido: las aprobaciones y rechazos se conservan, los cambios se muestran y se puede empezar de cero de forma explícita.
- Genera el **paquete de entrega** para la plataforma.

### 5.4 Argos: el banco de prueba

Argos responde "¿funciona de verdad?". Es una IA que contesta **solo** con lo aprobado:

- Responde con evidencia y la muestra.
- Se **abstiene** cuando falta evidencia, permisos o granularidad.
- Ejecuta únicamente consultas nombradas, parametrizadas y de solo lectura; nunca SQL libre.
- Evalúa una batería de preguntas esperadas (debe responder) y de preguntas fuera de alcance (debe negarse).

Argos **no es el destino**: sirve para probar el contexto antes de implementarlo. Su uso como servidor permanente para lo que una plataforma no pueda cubrir (plan B) existe para los casos ya validados, pero está **congelado**: no recibe inversión nueva.

### 5.5 La entrega

Desde una release aprobada, Nexo genera un **paquete de archivos** que la plataforma importa. No publica nada, no usa credenciales y no transporta datos de negocio. Incluye un **reporte de cobertura** que dice, elemento por elemento, qué se implementa en la plataforma, qué falta completar y qué queda fuera.

---

## 6. Qué entra y qué sale

### 6.1 Entradas

| Tipo | Formatos |
| --- | --- |
| Estructura de sistemas | DDL SQL (MariaDB/MySQL, SQL Server, PostgreSQL, Oracle, Snowflake, Databricks), CSV de `information_schema.columns`, `model.bim`, TMDL, PBIP, conexión de solo lectura a metadata de Fabric |
| Documentación | Markdown, texto, PDF, Word, Excel, HTML, CSV, JSON, YAML |
| Contexto | Alcance, casos de uso con su pregunta de negocio, responsables |

### 6.2 Salidas

| Salida | Contenido |
| --- | --- |
| **Diagnóstico de Atlas** | Inventario por sistema, mapa entre sistemas, capas y alcance por plataforma, brechas, puntaje, informe en Markdown |
| **Release de Nexo** | Ontología canónica aprobada (conceptos, reglas, KPI, propiedades, relaciones, sinónimos, activos técnicos y bindings), índice de evidencia y context pack para agentes |
| **Paquete para Microsoft Fabric** | Item Ontology en el formato nuevo (TMDL): entidades con descripción y sinónimos, propiedades tipadas, relaciones y reglas; cuerpo listo para la API REST; Data Agent con instrucciones |
| **Paquete para Databricks** | Pages (una por concepto), metric views YAML, SQL de Unity Catalog (comentarios y tags), cuerpo para crear un Genie Agent con sus joins |
| **Estándares abiertos** (en ambos paquetes) | `ontology.ttl` (OWL/Turtle, que Fabric importa) y un modelo Apache Ossie *experimental* |
| **Reporte de cobertura** | Por elemento: nativo, completar en la plataforma, instrucción del agente o fuera de alcance; ruta recomendada y pendientes |

---

## 7. Cómo se integra con lo que ya tenés

ONTO se conecta en dos planos distintos y los mantiene separados:

- **Plano de datos:** de dónde se lee metadata y datos (Fabric, Databricks, SQL Server, MariaDB, Snowflake, Power BI, planillas...).
- **Plano ontológico:** dónde se conserva o implementa el conocimiento aprobado (Fabric IQ Ontology, Databricks Genie Ontology u otra herramienta).

Una plataforma puede estar en ambos planos, pero son cosas distintas.

### 7.1 Las tres rutas

| Ruta | Cuándo | Qué hace ONTO |
| --- | --- | --- |
| **A. Nativa (preferida)** | La plataforma alcanza las fuentes y puede representar el conocimiento | Entrega el paquete; la plataforma queda como sistema de registro |
| **B. Mixta** | La plataforma cubre una parte y otra queda afuera (fuentes que no ve, reglas que no soporta) | La plataforma implementa lo que puede; el resto se resuelve con un puente o queda en ONTO |
| **C. Plan B (excepción)** | Ninguna plataforma puede implementarlo de forma viable | ONTO conserva la release (funcionalidad congelada) |

Que los datos estén fuera de la plataforma **no obliga** a la ruta C: se puede construir un puente.

| Plataforma | Puente a una base externa |
| --- | --- |
| Fabric | Mirroring (si el origen es compatible), shortcut o Copy job/pipeline hacia un Lakehouse; bases on-premises mediante gateway |
| Databricks | Lakehouse Federation (MySQL, PostgreSQL, SQL Server, entre otras) o ingesta a Delta |

Cuando se construye el puente, la ruta pasa de C a B o A **sin rehacer el trabajo**: la release aprobada es la misma.

### 7.2 Escenarios típicos

| Escenario | Qué conviene |
| --- | --- |
| Todo en Databricks, en Gold | Las herramientas nativas alcanzan (Genie Ontology aprende sola). ONTO aporta, a lo sumo, la aprobación humana de los conceptos críticos. **No competimos.** |
| Todo en Fabric con modelos semánticos | Ontology se genera desde los modelos. Mismo criterio. |
| Dominio repartido en varias plataformas y sistemas legacy | **Valor alto.** Atlas arma la vista completa, Nexo aprueba y el paquete va a cada plataforma. |
| Mucha lógica en Silver/Bronze sin documentar | **Valor alto.** ONTO propone y documenta lo que las plataformas no infieren. |
| Sin plataforma de datos moderna (PYME con una base legacy) | Se entrega la release y el banco de prueba; el plan B queda como excepción justificada. |

### 7.3 Cómo se carga lo entregado

| Plataforma | Pasos |
| --- | --- |
| **Fabric** | Copiar la carpeta de la ontología al repositorio Git del workspace o enviar el cuerpo a la API REST; o crear una ontología vacía e importar el `.ttl`. Agregar los data bindings (tabla y columna) y crear el Data Agent con las instrucciones ya redactadas. |
| **Databricks** | Ejecutar el SQL de Unity Catalog; cargar las Pages (importación masiva); crear las metric views completando la expresión; crear el Genie Agent con el cuerpo generado. |

Detalle técnico, formatos y limitaciones: [Integración con Fabric y Databricks](15_INTEGRACION_FABRIC_DATABRICKS.md).

---

## 8. Cómo piensa con IA y sin IA

El **diagnóstico de Atlas es determinista** (sin IA). Para extraer conocimiento de documentos y proponer la ontología, ONTO usa un modelo de lenguaje configurable (Azure OpenAI, OpenAI u Ollama local) bajo una política de datos (`approved_external` o `local_only`).

Reglas de la IA en ONTO:

- Solo **propone**. Todo lo inferido queda como pendiente de revisión, con sus supuestos y las fuentes que lo motivaron.
- Las fuentes son datos no confiables: nunca se ejecutan instrucciones contenidas en un documento.
- Una cita contextual no es prueba del significado.
- No se inventan fórmulas, columnas ni valores como hechos.

### La IA siempre debe aportar más

Medido sobre un caso real (sistema Nalub Pedidos: 35 tablas, 269 columnas y su documentación técnica):

| | Sin IA (heurístico) | Con IA |
| --- | --- | --- |
| Entidades propuestas | 188, casi todas ruido (`Charset`, `Motor`, `Version`...) | 12 conceptos de negocio (Cliente, Pedido, Pago, Aplicación de pago, Prepedido, Oferta...) |
| Reglas de negocio | 2 | 9 |
| Propiedades | 0 (solo una por defecto) | 59, con tipo derivado de la columna que las respalda |
| Relaciones | 0 | 16 entre conceptos |
| Joins en los paquetes | 0 | 8 reales (por ejemplo `pagos.clienteId` → `clientes.id`) |

Por eso la aplicación advierte cuando no hay IA habilitada: el resultado heurístico sirve para una primera mirada, no como propuesta de negocio.

---

## 9. Casos validados

Todos se pueden regenerar con los scripts de `scripts/` y las fuentes de `docs/casos/`.

| Caso | Qué valida | Resultado |
| --- | --- | --- |
| Comercial con Power BI (sintético) | Flujo completo con fuente en la plataforma | Ruta A en Fabric (13/13 elementos) |
| Ventas distribuidas (sintético: ERP MariaDB, lakehouse Databricks, Power BI, CRM SQL Server, planillas) | Cruce entre sistemas | 3 entidades compartidas (2 con clave común), 4 brechas priorizadas; ruta B en ambas plataformas |
| Nalub legacy (MariaDB real, solo estructura) | Dominio sin plataforma moderna | 33 tablas, 255 columnas, 25 relaciones; ruta C |
| Nalub legacy + Nalub Pedidos (repositorios reales) | Dos sistemas del mismo negocio | 31 entidades compartidas entre sistemas; con IA, ontología de 12 entidades, 9 reglas y 59 propiedades tipadas |
| TestData DW (SQL Server/Fabric, repositorio real) | Metadata sin documentación | Ruta A en Fabric; el reporte advierte que la ontología sale sin entidades |
| Fabric SIC riesgo (piloto) | Metadata y consultas de solo lectura en Fabric | Consultas validadas sobre datos reales |

Las pruebas automáticas (185 en esta fecha) cubren servicio, interfaz, formatos de entrega y estos casos.

---

## 10. Seguridad, gobierno y confianza

- **No modifica sistemas fuente** ni publica en plataformas externas. El paquete se importa en la plataforma.
- **Mínimo dato:** metadata y documentación; no copia datos de negocio si basta una referencia autorizada.
- **Sin secretos en artefactos:** las conexiones viven en perfiles locales por proyecto (`.env`), nunca en una release.
- **Política de datos para la IA:** `local_only` bloquea cualquier proveedor externo y solo admite un modelo local.
- **Trazabilidad:** cada elemento conserva su evidencia (documento, hash, fragmento) y quién lo decidió y cuándo.
- **Sin SQL libre:** el banco de prueba ejecuta solo consultas nombradas, parametrizadas y de solo lectura.
- **Versionado inmutable:** una release aprobada no se edita; se emite una nueva.

Fuera de alcance hoy: usuarios y roles técnicos (SSO), multiusuario, hosting en la nube y garantía de calidad de datos a nivel de fila.

---

## 11. Madurez del mercado y de ONTO

### 11.1 Estado del mercado (verificado el 2026-11-24)

| Capacidad | Estado |
| --- | --- |
| Fabric IQ Ontology | **Preview.** La experiencia anterior (JSON por entity type) se retira el 2027-01-31; la nueva usa TMDL |
| Fabric semantic views | Preview, YAML basado en Apache Ossie |
| Databricks metric views, dominios y Pages | Documentadas sin etiqueta Beta |
| Databricks Wikis, relaciones entre metric views, fuentes externas de Genie Ontology | Beta |
| Genie Ontology | Sin precio definido por ahora; confirmar el estado GA antes de afirmarlo a un cliente |
| Apache Ossie | Estándar abierto en incubación (versión 0.3 de desarrollo) |

**Implicación:** los formatos pueden cambiar. Por eso ONTO mantiene un modelo propio portable y aísla cada generador por plataforma.

### 11.2 Estado de ONTO

- **Hecho y probado:** Atlas con capas y alcance por plataforma; Nexo con revisión, consolidación y release; paquetes para Fabric (formato nuevo) y Databricks; OWL/Turtle y Ossie; banco de prueba; flujo simple con IA.
- **Pendiente de validar:** la carga real de los paquetes en workspaces de Fabric y Databricks (hay una plantilla de piloto en [`pilotos/`](pilotos/PILOTO_VALIDACION_PLATAFORMAS.md)).

---

## 12. Límites y cosas a saber

- El puntaje de Atlas es basal y determinista: orienta el trabajo, no certifica que un dominio esté listo para producción.
- El mapa entre sistemas, la capa y el alcance son heurísticos: las equivalencias las confirman los responsables.
- Las definiciones extraídas son candidatas hasta que una persona las aprueba.
- Los paquetes no están verificados contra una plataforma real; el export a Ossie es experimental y el de OWL no representa reglas, KPI ni restricciones.
- Las expresiones de KPI no se inventan: salen como "completar", con el DAX del modelo semántico como propuesta cuando existe.
- No se generan ejemplos pregunta-SQL ni benchmarks para Genie, porque la release no guarda SQL aprobado.
- Generar un borrador con IA tarda minutos (unos 5 con cuatro documentos) y no muestra progreso.
- Las claves foráneas del esquema todavía no viajan a la release; los joins salen del modelo de IA o de relaciones curadas.
- Sin IA, el scanner heurístico es ruidoso con documentación técnica.
- ONTO se importa por archivo: no descubre metadata de Databricks ni de otras plataformas en vivo (sí de Fabric, en solo lectura).

---

## 13. Qué viene

Prioridad alta:

1. **Piloto en workspaces reales** de Fabric y Databricks para confirmar los formatos y fijar la versión probada.
2. **Integrar y ordenar el flujo "Ontología inicial"** (propiedades, relaciones y tablas desde la IA) y subir la versión del prompt.

Prioridad media:

3. **Progreso y límites de la IA:** indicador de avance, tope de llamadas y estimación de costo.
4. **Claves foráneas del esquema en la release,** para generar joins sin depender de la IA.
5. **Consolidar propiedades y relaciones,** no solo candidatos.
6. **Recomendar la IA como camino normal** en la guía de uso.

Después del piloto:

7. **Importar lo que la plataforma ya tiene** (modelos semánticos, metric views, Pages, ontologías exportadas) como evidencia, para cruzarlo con los sistemas que la plataforma no ve y marcar contradicciones.
8. **Ejemplos SQL y benchmarks** de Genie, si la release llega a guardar SQL aprobado.
9. **Confirmar el estado GA** de Pages y Genie Ontology.

Decisiones tomadas de **no hacer**: conectores de publicación directa (las APIs están en preview y el paquete por archivo alcanza), nuevas capacidades de Argos como servidor, sincronización bidireccional y competir cuando todo vive en una sola plataforma en Gold.

El plan completo y su estado: [Plan de reposicionamiento](18_PLAN_REPOSICIONAMIENTO.md).

---

## 14. Cómo empezar

```text
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run streamlit_app.py
```

- **Para una demo:** `python scripts/run_distributed_demo.py` (dominio distribuido) o `python scripts/run_commercial_sales_demo.py` (flujo completo).
- **Con repositorios reales:** `python scripts/run_local_repos_case.py` (Nalub legacy y Pedidos, y el DW de prueba); agregar `--allow-llm` para usar el proveedor de IA configurado.
- **Para habilitar la IA:** configurar `ONTO_LLM_PROVIDER` y sus credenciales en `.env` (ver [README](../README.md)).
- **Para verificar:** `.\.venv\Scripts\python.exe -m unittest discover -s tests`.

La guía para personas no técnicas, paso a paso: [Guía paso a paso](GUIA_PASO_A_PASO_NO_TECNICA.md).

---

## 15. Glosario

| Término | Significado |
| --- | --- |
| **Ontología** | Manual de significados del negocio: entidades, propiedades, relaciones, reglas y métricas, con sus fuentes. |
| **Entidad / concepto** | Una cosa del negocio (Cliente, Pedido). |
| **Capa Bronze / Silver / Gold** | Datos crudos, depurados y listos para consumo analítico. |
| **Atlas, Nexo, Argos** | Las tres áreas de ONTO: diagnóstico, validación y banco de prueba. |
| **Candidato** | Concepto, regla, KPI o activo propuesto, pendiente de decisión. |
| **Release** | Versión aprobada e inmutable del conocimiento. |
| **Binding** | Vínculo entre un concepto y la tabla o columna que lo respalda. |
| **Context pack** | Subconjunto de la release preparado para un agente, con instrucción de abstención. |
| **Paquete de entrega** | Archivos que una plataforma importa, más el reporte de cobertura. |
| **Ruta A / B / C** | Dónde se implementa el conocimiento: en la plataforma, repartido, o en ONTO como plan B. |
| **Puente** | Forma de que una plataforma alcance un sistema externo (Mirroring, shortcut, federación, ingesta). |
| **Abstención** | Respuesta "no sé" cuando falta evidencia, permisos o granularidad. |
| **TMDL** | Formato de texto de la ontología nueva de Fabric. |
| **OWL / Turtle** | Estándar abierto de ontologías y su sintaxis de texto. |
| **Apache Ossie** | Estándar abierto (en incubación) para intercambiar modelos semánticos entre herramientas. |
| **Metric view / Page / Genie** | Piezas de la capa semántica de Databricks: métricas gobernadas, definiciones de conceptos y agente conversacional. |

---

## Anexo: mapa de documentación

| Documento | Para qué |
| --- | --- |
| [Objetivo, alcance y foco](OBJETIVO_ALCANCE_Y_FOCO.md) | Objetivo, problema, foco y métricas de éxito |
| [Guía paso a paso no técnica](GUIA_PASO_A_PASO_NO_TECNICA.md) | ONTO sin tecnicismos |
| [MVP operativo](00_MVP_OPERATIVO.md) | Qué incluye hoy, qué está congelado y cómo verificar |
| [Atlas](05_ATLAS_ASSESSMENT_MVP.md), [Nexo](06_NEXO_REGISTRY_MVP.md), [Argos](07_ARGOS_RUNTIME_MVP.md) | Contrato y alcance de cada área |
| [Integración con Fabric y Databricks](15_INTEGRACION_FABRIC_DATABRICKS.md) | Formatos, mapeo de elementos, rutas e importación |
| [Posicionamiento y límites](10_POSITIONING_AND_BOUNDARIES.md) | Mensaje, límites y anti-promesas |
| [Plan de reposicionamiento](18_PLAN_REPOSICIONAMIENTO.md) | Estado y pasos futuros |
| [Método de trabajo iterativo](17_METODO_DE_TRABAJO_ITERATIVO.md) | Actualizar sin perder decisiones |
| [Casos de prueba](casos/README.md) | Fuentes y resultados esperados por caso |
| [Piloto de validación en plataformas](pilotos/PILOTO_VALIDACION_PLATAFORMAS.md) | Plantilla para probar en workspaces reales |
