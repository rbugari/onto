# Plan Atlas: cobertura explicativa del dominio

Fecha: 2026-10-06
Estado: Partes 1 a 5 implementadas y verificadas tecnicamente. Azure OpenAI conectado y probado. El contraste admite hipotesis del modelo separadas de la cobertura documental; la validacion de calidad semantica con muestra humana sigue pendiente.

## Objetivo

Atlas debe responder: **cuanto del alcance inventariado podemos explicar con evidencia, que no entendemos y que informacion necesitamos para avanzar hacia una ontologia**.

El ciclo es: cargar evidencia, evaluar cobertura, solicitar informacion, incorporar nueva evidencia y volver a evaluar. Por ahora se usan solo documentacion y metadata: no se habilitan muestreo de filas ni exploracion de bases.

El score basal actual mide disponibilidad de estructura y contexto. No equivale a un porcentaje de conocimiento explicado y se mantiene como indicador secundario. Nexo sigue siendo quien gestiona la aprobacion: explicado no significa aprobado.

## Punto de partida verificado

- Atlas inventaria sistemas, objetos tecnicos, documentos y casos de uso.
- El scanner extrae definiciones, reglas, KPIs, relaciones, ambiguedades y preguntas; conserva referencias a fragmentos.
- La extraccion de contexto existente recibe los primeros 80 conceptos tecnicos. El nuevo contraste semantico es independiente de esa extraccion: recorre todo el universo incluido y contrasta bloques documentales, sin ese limite de 80.
- Una referencia existente a un fragmento no comprueba que el texto respalde la afirmacion.
- Se guardan assessments independientes con universo, matriz explicativa y pedidos. El contraste semantico se ejecuta explicitamente desde Atlas; se pueden comparar dos assessments por identidad logica.

## Reglas del indicador

1. El denominador es una lista visible y versionada de elementos en alcance, no "todo el negocio".
2. La primera version informa cobertura de entidades, relaciones y KPIs por separado. Las propiedades/columnas tienen su propio detalle; no se mezclan miles de columnas en un unico porcentaje.
3. Cuando hay evaluaciones, el porcentaje explicado de cada grupo es `100 * elementos explicados / elementos en alcance`. Los otros tres estados se muestran por separado, sin darles puntos parciales. Si no hay evaluaciones validas, se informa sin evaluar y no se publica un porcentaje; si el procesamiento es parcial, se mantiene el denominador completo y se informa cuantos elementos siguen sin evaluar o fallaron.
4. Si el grupo esta vacio, la cobertura es "no evaluable", no 0% ni 100%.
5. Si una fuente esta declarada sin metadata, el universo es incompleto. El porcentaje se presenta como cobertura del inventario disponible, junto con esa limitacion.
6. Con documentacion solamente, el universo es provisional: lo desconocido que aun no se inventario no se puede medir.
7. Cada elemento evaluado tiene uno de cuatro estados: explicado con evidencia, parcialmente explicado, sin explicacion o contradictorio. Ademas registra si fue evaluado y con que metodo; los pendientes y fallos conservan estado nulo, no demuestran ausencia de explicacion y se cuentan por separado.
8. Cada clasificacion conserva aspectos requeridos, aspectos respaldados, evidencia, motivo y faltantes. Para una entidad: significado, granularidad e identificacion; para una relacion: extremos y significado, cardinalidad cuando aplique; para un KPI: definicion, formula, granularidad y filtros/exclusiones.
9. Una hipotesis basada en nombres no cuenta como explicacion. La confianza declarada por un LLM tampoco es un porcentaje de cobertura.
10. Los documentos son evidencia no confiable como instrucciones: su contenido no puede cambiar las reglas del analisis ni autorizar herramientas.
11. El modelo puede proponer explicaciones inferidas a partir de documentos, metadata y conocimiento general. Se etiquetan como inferidas en grado importante, con supuestos, fundamento y validaciones pendientes. Sus citas contextuales no son respaldo documental: se conservan en una lista separada, no cambian estados ni porcentajes, no resuelven contradicciones ni aprueban conocimiento.

## Etapas y pruebas de salida

### Parte 1. Contrato y universo evaluable

Estado: implementada. El assessment persiste `explanatory_scope.json` y Atlas lo muestra en Diagnostico > Universo evaluable. Los controles permiten incluir/excluir con motivo y generan un nuevo assessment; los anteriores no se modifican. Los vinculos a casos de uso son por sistema, no una confirmacion de relevancia semantica. Los documentos solos todavia no generan entidades del universo: se informa el limite provisional.

Entregable: inventario explicativo con identificadores estables, sistema, tipo, casos de uso y aspectos a explicar. Poder incluir/excluir elementos con motivo. Versionar alcance y criterios; conservar objetos tecnicos no vinculados como pendientes, no descartarlos silenciosamente.

Pruebas:

- Una fixture pequena con pedidos, entregas, stock y un KPI produce exactamente el universo acordado.
- Reimportar la misma metadata no duplica elementos ni cambia su identidad logica.
- Fuente sin metadata y grupos vacios muestran las limitaciones del denominador.

Gate: podemos listar y revisar todo lo que el indicador va a contar, sin llamar al LLM.

Verificacion web realizada sobre datos temporales: abrir proyecto, navegar a Diagnostico > Universo evaluable, rechazar exclusion sin motivo, guardar exclusion (5 a 4 entidades), reincorporar (4 a 5) y comprobar grupo KPI vacio no evaluable. La prueba encontro que el selector conservaba el assessment anterior; se corrigio para mostrar el nuevo al guardar y mantenerlo al cambiar de grupo. Un universo historico distinto del proyecto actual queda consultable, pero sin controles de edicion.

Cierre verificado: 87 tests de servicio e interfaz pasan, incluida la recarga en la misma sesion y la consulta del historico. La discrepancia de seleccion se debia a etiquetas identicas (fecha con precision de minutos, score y estado iguales) para IDs distintos; cada opcion ahora incluye su ID de ejecucion. Prueba web final: opciones unicas, reincorporacion de 4 a 5 entidades, mismo ID seleccionado despues de cambiar a KPIs, historico distinto sin controles de edicion y regreso al diagnostico actual. El plan exige AppTest y uso real de la web en las partes siguientes.

### Parte 2. Matriz y calculo reproducible

Estado: implementada y verificada. `explanatory_coverage.json` se persiste en cada assessment y se consulta en Diagnostico > Cobertura explicativa. Se conservan los inputs estructurados y los fragmentos citados completos, con hash de texto, para reconstruir resultados. La vista muestra contadores por tipo, elementos, aspectos faltantes, citas y contradicciones; permite descargar la matriz.

Entregable: motor de estados y porcentajes sobre evidencia estructurada; artefacto propuesto `explanatory_coverage.json` dentro del assessment. Mantener lectura de assessments anteriores sin el nuevo artefacto.

Las pruebas usan evidencias y clasificaciones controladas, no resultados variables de un proveedor. El motor valida referencias y requisitos; no pretende entender texto por coincidencia de palabras.

Contrato del motor: [explanatory_coverage.py](../src/ontology_workbench/explanatory_coverage.py), `build_explanatory_coverage(scope, chunks, evaluations=None)`. Cada clasificacion identifica `element_id`, `method` y `evaluation_status`; los respaldos (`supports`) indican `aspect`, `chunk_id` y `quote`. Las contradicciones indican `chunk_id`, `quote`, `reason`, `material` y `resolved` (por defecto material y sin resolver). El estado lo calcula el motor, no se acepta un estado explicado declarado por el productor. Solo se cuenta explicado si todos los aspectos tienen citas validas y no hay contradiccion material pendiente ni errores de validacion.

El generador normal de assessments conserva su comportamiento determinista y produce una matriz sin evaluar. La accion de Parte 3 genera otro assessment con propuestas semanticas. Verificar una cita literal no demuestra que respalde semanticamente el aspecto. Explicado tampoco significa aprobado en Nexo.

Pruebas:

- Cuatro elementos, uno en cada estado: 25% explicado y reparto 25/25/25/25.
- Referencia inexistente o evidencia insuficiente no permite estado explicado.
- Una contradiccion material sin resolver impide estado explicado.
- Evidencia duplicada no cambia el denominador ni aumenta la cobertura.
- Nexo y el scoring basal siguen funcionando con paquetes nuevos y antiguos.

Gate: cada porcentaje se puede reconstruir abriendo sus elementos y evidencias.

Cierre: 92 tests de servicio e interfaz pasan. Cubren 25% explicado y reparto 25/25/25/25, cita inexistente o inventada, evidencia insuficiente, contradiccion material, duplicados, reproduccion desde snapshots, persistencia y lectura de paquetes anteriores. Una regresion legacy revelo IDs de documento repetidos: los fragmentos ambiguos ahora fallan al ser citados sin abortar el assessment; las copias identicas no aumentan la cobertura. Las variantes ambiguas tambien se conservan para reproducir el fallo.

Prueba web con datos temporales: abrir el caso controlado, consultar 25%, seleccionar el elemento contradictorio y leer su cita; luego abrir ventas distribuidas, comprobar entidades/relaciones/propiedades sin evaluar, KPIs no evaluables y advertencia de fuente sin metadata. Sin acceso a filas, conexiones live ni cambios en los proyectos reales.

### Parte 3. Contraste semantico con LLM

Estado: implementada y verificada tecnicamente. En Diagnostico > Contraste semantico, la accion **Evaluar cobertura con LLM** crea un assessment nuevo y selecciona su cobertura. La extraccion de contexto mantiene su flujo anterior; el contraste utiliza directamente el inventario completo y los fragmentos actuales, con proveedor y politica existentes.

Entregable: despues de la extraccion, analizar cada bloque del universo contra evidencia relevante y consolidar resultados entre documentos. No limitar el analisis a los primeros 80 conceptos.

Implementacion: [explanatory_analysis.py](../src/ontology_workbench/explanatory_analysis.py), [prompt](../prompts/atlas_explanatory_coverage.md) y `WorkbenchService.create_semantic_atlas_assessment`. Procesa bloques de hasta 12 elementos contra todos los bloques documentales deduplicados; si hay varios bloques de evidencia, hace una llamada de consolidacion para comparar sus hallazgos. Los extremos de relaciones incluyen nombres y referencias tecnicas. Los IDs, aspectos, citas y esquema se validan; las contradicciones materiales detectadas no se pueden resolver ni eliminar silenciosamente en la consolidacion. El motor de Parte 2 sigue calculando los estados y porcentajes.

Limites operativos: presupuesto predeterminado de 40 solicitudes logicas, ajustable de 1 a 200; se usa el transporte y los reintentos del cliente existente. Un contexto o una consolidacion demasiado grandes, un presupuesto agotado, un fallo del proveedor o una respuesta invalida dejan los elementos afectados como fallidos. No se trunca el inventario a los primeros 80 ni se transforma un resultado incompleto en sin explicacion. Los proveedores deshabilitados, desconocidos o bloqueados por politica no se invocan. Sin evidencia documental no se llama al LLM.

`explanatory_coverage.analysis` conserva configuracion no secreta, modelo efectivo, version/hash de prompt, huella de evidencia/alcance/configuracion/presupuesto, llamadas realizadas, fases y errores, modo efectivo, reutilizacion y muestra para revision humana. Los errores de transporte se registran por clase sin copiar detalles potencialmente sensibles. Se reutiliza un analisis completo solo con huella identica; antes de evaluar se reconstruyen los fragmentos desde los documentos actuales.

El LLM propone vinculos, aspectos respaldados, citas y contradicciones. El codigo valida esquema, IDs y fragmentos; comprueba la correspondencia de las citas con el texto y calcula los porcentajes. La presencia literal de una cita no garantiza respaldo semantico: se revisa una muestra humana de resultados.

Registrar proveedor/modelo, version de prompt, modo efectivo, fallos y cobertura del procesamiento. Si falla el proveedor, no presentar una heuristica como evaluacion semantica equivalente. Respetar la politica existente `local_only`/`approved_external`, limitar llamadas y reutilizar analisis solo si evidencia, alcance y configuracion no cambiaron.

Pruebas:

- Respuestas simuladas: IDs inventados, citas incorrectas e instrucciones incrustadas no generan elementos explicados.
- Documentos distintos con definiciones incompatibles producen contradiccion.
- El elemento 81 y siguientes tambien se evaluan.
- Texto irrelevante o copias del mismo documento no mejoran el resultado.
- Una prueba opcional con proveedor real contrasta sus clasificaciones con una muestra revisada por una persona; no exige un porcentaje exacto de un LLM.

Gate: las clasificaciones son trazables y sus errores observados quedan registrados; no hay fallback silencioso.

Cierre tecnico: 100 tests pasan. Incluyen 90 elementos evaluados, IDs inventados, citas incorrectas, estado impuesto por instrucciones incrustadas, contradiccion entre dos documentos, duplicados, politica local_only, presupuesto, fallo del proveedor, cache y evidencia nueva. Se encontro y corrigio que los fragmentos guardados no incorporaban un documento nuevo antes de validar la cache.

Verificacion web: proyecto temporal, transporte HTTP real hacia un proveedor local simulado compatible con Ollama, modelo `simulated-web-test`, sin credenciales ni conexiones externas. Se probo la accion desde el navegador: respuesta controlada completa con citas y muestra humana, segundo assessment reutilizado con cero llamadas, y evidencia nueva que provoco HTTP 503. El error se mostro como analisis con fallos, sin convertir el elemento en sin explicacion ni usar heuristicas. La simulacion se retiro despues de verificar el flujo.

Pendiente de calidad: no se invoco un modelo real ni se reviso humanamente una muestra de sus respuestas. El prompt separa evidencia no confiable de instrucciones y el codigo rechaza cambios al contrato; estas defensas no prueban respaldo semantico ni eliminan todo riesgo de prompt injection. La muestra incluye resultados explicados, parciales, sin explicacion y contradictorios para revisar tambien falsos negativos. No presentar el porcentaje como verdad de negocio validada hasta esa revision.

### Parte 4. Diagnostico visible y pedidos de informacion

Estado: implementada y verificada. El guardado deriva `explanatory_diagnosis.json` desde la matriz y sus snapshots de alcance/sistemas; actualiza la seccion explicativa de `execution_summary.md` sin duplicarla. Los assessments antiguos siguen siendo legibles.

En Cobertura explicativa se muestran contadores por grupo, sistema y caso de uso. Los filtros por sistema, caso, estado y aspecto faltante no cambian el denominador. Los vinculos por caso siguen siendo por sistema, no relevancia semantica confirmada. Cada pedido expone informacion requerida, motivo, responsable propuesto (siempre por confirmar), prioridad y criterio de cierre; se descarga la seleccion en JSON. Los elementos fallidos o no evaluados generan pedidos de completar/reintentar analisis, no pruebas de falta documental.

Entregable: en Atlas, cobertura por grupo, sistema y caso de uso; tabla filtrable con estado, motivo y evidencia; backlog de pedidos con informacion requerida, responsable propuesto, prioridad y criterio de cierre. Incluirlo en el resumen exportable.

Ejemplo de pedido: "Stock disponible: falta confirmar si descuenta reservas; solicitar la definicion al responsable de inventario. Se cierra cuando una fuente explica la formula y las exclusiones".

Pruebas: AppTest muestra denominador, estados, faltantes y limitaciones; el resumen coincide con el artefacto persistido. No se oculta el estado no evaluable ni se confunde explicado con aprobado.

Gate: una persona puede identificar que documento pedir y por que, sin leer JSON.

Cierre tecnico: pruebas de denominadores, fuente vacia, pedidos, fallos, prioridad, exclusiones, persistencia y resumen sin duplicados. AppTest verifica filtros, resultados vacios y 25% intacto. Navegador sobre datos temporales: ERP, Ventas, pedidos/cierre, contradiccion y faltantes, informe por sistema/caso. Detecto etiquetas obsoletas en los selectores al filtrar; se corrigio asignando explicitamente una opcion visible al estado del widget. No se invoco un LLM ni se modificaron proyectos reales.

### Parte 5. Iteraciones y comparacion

Estado: implementada y verificada. Diagnostico > Comparacion permite elegir un assessment inicial y comparar con el seleccionado como final. El calculo es puro sobre paquetes persistidos, con descarga JSON; no modifica assessments, pedidos ni Nexo.

Las transiciones distinguen agregado/retirado, incluido/excluido, analisis completado, cambio de clasificacion, aspectos y evidencia. Las citas iniciales y finales son inspeccionables; los respaldos se comparan por contenido, aspecto y cita, no solo por ID de fragmento. Solo con mismo alcance/criterios se calcula diferencia en puntos porcentuales; con fuentes, elementos o criterios distintos se muestran los denominadores y se advierte que no son bases comparables.

Los pedidos anteriores se vinculan al estado final y los pedidos actuales. Completar/reintentar un analisis es distinto de resolver un faltante; retirar un elemento del alcance no resuelve su pedido. Un resultado compatible con el cierre queda como Revisar cierre, nunca cerrado o aprobado automaticamente. Se comparan las evidencias citadas, no se atribuye causalidad a cualquier documento agregado.

Entregable: comparar dos assessments por identidad logica, mostrando transiciones, nuevas evidencias, elementos agregados/retirados y cambios de alcance. Diferenciar resolver un faltante de evaluar una tarea antes fallida. Vincular pedidos con sus resultados.

Pruebas:

- Documentacion relevante explica un elemento pendiente y el cambio queda trazado.
- Documentacion irrelevante o duplicada no mejora cobertura.
- Nueva contradiccion puede reducir cobertura: el avance no es necesariamente monotono.
- Agregar una fuente cambia el denominador y se informa; no se muestra como retroceso sobre el mismo alcance.

Gate: podemos demostrar dos rondas de assessment y explicar cada cambio.

Cierre tecnico conjunto: 104 tests de servicio e interfaz pasan. Incluyen duplicados con IDs distintos, nueva fuente y denominador, retiro, contradiccion que reduce cobertura, analisis antes fallido y cierre no confirmado. AppTest recorre evidencia y cambios de alcance. Navegador: evidencia nueva controlada mejora 25% a 50% (+25 pp) con citas antes/despues; una exclusion cambia 4 a 3 y 50% a 33.33%, sin delta de avance y con advertencia de bases distintas. Sin LLM real: esta prueba verifica mecanismos y trazabilidad, no calidad semantica.

Revision visual de escritorio y movil: las cifras iniciales/finales ahora usan lineas compactas, sin truncar porcentajes ni No evaluable; la prueba UI focalizada pasa despues del ajuste. Se acciono Descargar comparacion, pero el navegador integrado no devolvio el evento de descarga: la recepcion del archivo en un navegador normal queda sin verificar.

## Orden de ejecucion

Implementar una parte por vez, ejecutar sus pruebas y revisar su salida antes de seguir. La primera entrega util termina en la Parte 4; la Parte 5 completa el ciclo iterativo.

Reutilizar los tests de servicio y AppTest existentes y los origenes de [casos](casos/README.md). Crear fixtures pequenas solo cuando los casos grandes no permitan aislar una regla. Las pruebas no modifican `data/` actual ni requieren conexiones live.

Cada parte que agregue o modifique comportamiento visible requiere **AppTest y una prueba usando la web en navegador** con datos aislados: navegar, accionar controles, comprobar persistencia y resultado visible. Registrar resultado y defectos encontrados; no dar por terminado el gate con tests de backend solamente. Repetir este control en la Parte 2 (contadores), Parte 3 (modo y fallos de analisis), Parte 4 (filtros y pedidos) y Parte 5 (comparacion).

| Momento | Caso | Que verificar |
| --- | --- | --- |
| Partes 1-2 | Fixture pequena y ventas distribuidas | Denominador, estados y fuentes sin metadata |
| Partes 3-4 | Nalub y ventas distribuidas | Explicaciones reales, faltantes y contradicciones con revision humana |
| Parte 5 | Dos versiones del mismo caso | Documento nuevo, duplicado, contradiccion y cambio de alcance |

## Limites y siguientes pasos

No promete una ontologia completa, validacion de datos ni certeza absoluta del significado. No abre acceso a filas, no aprueba conocimiento automaticamente y no publica en Fabric o Databricks.

### Ciclo real del 2026-10-06

Caso `distribuidora-ventas-distribuidas`, con Azure OpenAI `gpt-6.1-sol`: scanner real completado; Atlas completo con 9 de 12 llamadas disponibles, sobre 3 documentos y 107 elementos (17 entidades, 9 relaciones, 2 KPIs y 79 propiedades). Sin fallos ni elementos disponibles sin evaluar. Uno de los cinco sistemas declarados carece de metadata, por lo que el universo sigue siendo incompleto.

La cobertura documental tiene 0 elementos completamente explicados, 22 parciales y 85 sin explicacion; no se detectaron contradicciones. El modelo propuso 114 explicaciones inferidas, todas separadas del respaldo documental y pendientes de revision. La muestra tecnica distingue dimensiones de cliente actuales/historicas, claves de negocio/sustitutas y razon de sumas/promedio de porcentajes para margen; estas posibilidades no se confirmaron como reglas del caso.

Nexo genero un draft con 120 candidatos pendientes, ninguno aprobado. Argos respondio la pregunta de dominio, se abstuvo fuera de evidencia y paso 6/6 casos sobre la release anterior aprobada. Se generaron paquetes locales de Fabric y Databricks de esa release; no se publicaron en las plataformas ni se creo una nueva release.

El resumen JSON completo se conserva en el paquete local del assessment `atlas-2026-10-06T17-45-08-00-00-1a7b08fc209c`. La carpeta de datos de ejecucion esta excluida de Git; los resultados descritos arriba son el registro versionado, disponible tambien en GitHub. Suite: 113 tests OK sin llamadas externas durante pruebas. AppTest y navegador verificaron la advertencia en es/en, continuidad del assessment/elemento y texto sin desbordamiento en anchos amplio y estrecho. Esto verifica ejecucion, contratos y presentacion, no validacion semantica humana.

Siguiente accion: revisar una muestra humana con ventas distribuidas (tambien falsos respaldos, falsos negativos y contradicciones), confirmar supuestos y completar la metadata faltante antes de aprobar conocimiento. El perfilado de datos sera una evolucion separada del assessment documental.