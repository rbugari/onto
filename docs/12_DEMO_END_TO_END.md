# ONTO: guion de demo ante público

**Caso:** ventas de una distribuidora repartidas entre cinco sistemas. Datos y documentos sintéticos. **Edición:** 2026-10-08.

**Uso:** guía del presentador, con relato, acciones en pantalla, motivos, resultados esperados y controles antes de avanzar. No es un folleto comercial ni una certificación de conocimiento.

**Duración orientativa:** 40 a 55 minutos con explicación y revisión; el tiempo del proveedor LLM no es fijo. Para una versión de 15 minutos, preparar resultados con anticipación y declarar qué se ejecuta en vivo y qué se muestra ya calculado.

**Recorrido:** proyecto y alcance; cinco sistemas; tres documentos; contexto; diagnóstico; contraste LLM; cobertura e inferencias; pedidos; revisión Nexo; release; Argos; paquetes de plataforma; segunda iteración.

La fuente editable es este documento. El PDF se genera localmente, sin enviar el guion a ningún modelo:

```powershell
.\.venv\Scripts\python.exe scripts/build_demo_pdf.py
```

Resultado: `deliverables/ONTO_Guion_Demo_Ventas_Distribuidas.pdf`. Para la guía corta de operación consultar la [guía del caso](casos/ventas_distribuidas/README.md). Los contratos y hechos históricos están en el [plan de cobertura](16_PLAN_ATLAS_COBERTURA_EXPLICATIVA.md).

## 1. La idea que debe recordar el público

Tener tablas, un modelo de BI y documentos no significa tener un significado compartido y gobernado. ONTO ayuda a mostrar lo que sabemos, identificar lo que falta, pedirlo de forma concreta y preparar conocimiento aprobado para su plataforma destino.

> Apertura: "La empresa no tiene cinco versiones de la realidad por capricho. Tiene sistemas diseñados para tareas distintas. Hoy vamos a ver qué sabemos sobre ventas, qué solo suponemos y qué todavía tenemos que preguntarle a alguien."

La demo usa Atlas, Nexo y Argos. Atlas inventaría y contrasta explicaciones; Nexo registra decisiones y produce releases; Argos prueba el conocimiento aprobado. El destino preferido de implementación son Fabric, Databricks u otras plataformas adecuadas. Argos es banco de pruebas y runtime de respaldo, no el objetivo único del producto.

**No prometemos:** reconciliar filas que no se cargaron, inventar claves ausentes, cerrar preguntas mediante conocimiento general del modelo, certificar una ontología ni publicar sin una acción posterior. La demo usa metadata y documentos, no registros reales de ventas.

El público debería terminar pudiendo responder: qué falta del presupuesto, por qué Cliente no equivale a Cuenta y qué hay que confirmar para interpretar Margen %. Si esas respuestas no están claras, mostrar de nuevo las fuentes, el glosario y los pedidos antes de cerrar.

## 2. Preparación antes de entrar en escena

### Aplicación y seguridad

Abrir la aplicación en español y verificar la carpeta de datos del repositorio. La configuración LLM vive en el entorno local; el bloque técnico de la interfaz es una referencia, no un formulario editable. No proyectar claves, perfiles de conexión ni el contenido del archivo de entorno.

Si la app no está iniciada, desde la raíz del repositorio:

```powershell
$env:ONTO_DATA_DIR = Join-Path (Get-Location) 'data'
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py --server.port 8601
```

Abrir http://127.0.0.1:8601/?lang=es. Verificar la leyenda del motor en Contexto de negocio. La configuración local probada fue Azure OpenAI, deployment `gpt-6.1-sol`; otra instalación necesita su propio entorno autorizado. Preparar una alternativa si no hay conectividad.

### Materiales y respaldo

Abrir `docs/casos/ventas_distribuidas/input/` en el explorador de archivos. Los SQL son DDL sintético: se importan como metadata, **no se ejecutan contra una base**. El CSV no contiene ventas y el BIM no concede acceso a filas.

| Material | Archivo | Intención |
| --- | --- | --- |
| ERP | erp_mariadb.sql | Ver la estructura transaccional. |
| Lakehouse | lakehouse_databricks_columns.csv | Inventariar la capa analítica. |
| Power BI | powerbi_ventas.bim | Incorporar semántica y medidas existentes. |
| CRM | crm_sqlserver.sql | Identificar cuentas y oportunidades. |
| Alcance | scope.json | Mantener preguntas, prioridades y sistemas. |
| Glosario | documentation/01_glosario_comercial.md | Definiciones y reglas. |
| Equivalencias | documentation/02_equivalencias_sistemas.md | Cruces parciales y dudas abiertas. |
| KPIs | documentation/03_kpis_comerciales.md | Indicadores y fórmulas declaradas. |

Tener una release previamente revisada como respaldo, junto con su ID y resultados. Una captura puede explicar una contingencia, pero no debe presentarse como una ejecución en vivo. No ejecutar runners para una demo anunciada "desde cero": algunos aprueban candidatos y crean releases automáticamente.

## 3. Escena inicial: el problema de negocio

**Pantalla:** inicio y selección de proyecto. **Objetivo:** explicar el dominio antes de hablar de formatos o modelos.

> "La gerencia quiere saber qué clientes dejan margen, qué oportunidades del CRM se convierten en ventas y cómo vamos contra el presupuesto. Ninguna de esas preguntas vive en un solo sistema. El ERP registra pedidos; el CRM conoce oportunidades; el lakehouse prepara datos analíticos; Power BI presenta indicadores; el presupuesto sigue en planillas."

Este caso mezcla fuentes técnicas, una plataforma analítica, un modelo semántico y documentación funcional. Permite mostrar preparación y gobierno sin acceso a bases productivas y sin hacer depender el relato de un caso específico de riesgo o SIC.

Antes de crear nada, anunciar los huecos deliberados: no se entregará metadata de las planillas; el CRM no tendrá responsable formal; las equivalencias serán parciales; y los documentos no explicarán cada columna, granularidad o exclusión.

> "No voy a completar todos los casilleros para que el resultado salga verde. Voy a dejar visibles los huecos con los que trabaja un equipo real de datos y negocio."

**Control:** el público entiende que una falta de metadata, una definición incompleta y una llamada fallida son problemas distintos. No presentar ninguno como prueba de que el dominio no existe o no puede analizarse.

## 4. Crear proyecto y definir alcance

**Pantalla:** barra lateral, Crear proyecto; después Atlas, Alcance. Crear `test2` si está libre. Si existe, usar un nombre nuevo de presentación. No importar el JSON de un proyecto procesado, ni copiar sus diagnósticos, drafts o releases.

Completar nombre y rol del revisor de la sesión. Si es un revisor de prueba, decirlo: no presentarlo como aprobación efectiva de los dueños del negocio.

| Campo | Valor | Por qué |
| --- | --- | --- |
| Cliente | demo-distribuidora | Identifica el caso organizacional. |
| Dominio | comercial | Delimita el problema de negocio. |
| Producto de datos | ventas-distribuidas-test2 | Separa estos resultados de los anteriores. |
| Responsable del dominio | Gerencia Comercial | Propone quién responde por el significado del dominio. |

Guardar alcance. Registrar los sistemas antes de vincularlos a los casos de uso, o completar los vínculos al volver a Alcance. Copiar las preguntas completas de `scope.json`.

> "El alcance no es solo un rótulo administrativo. Me permite saber para qué estoy interpretando la información y qué preguntas justifican revisar cada sistema."

**Control:** proyecto nuevo, valores guardados, sin resultados heredados. Registrar su `project_id`. No borrar el caso anterior para obtener una pantalla limpia.

## 5. Registrar e inventariar cinco sistemas

**Pantalla:** Atlas, Fuentes. Completar Nombre, Plataforma, Responsable y descripción; pulsar Agregar sistema. Después seleccionar cada fuente en Cargar metadata de un sistema, subir su archivo y pulsar Inventariar sistema.

| Sistema | Plataforma | Responsable | Archivo |
| --- | --- | --- | --- |
| ERP operativo | MariaDB | Jefe de Sistemas | erp_mariadb.sql |
| Lakehouse analitico | Databricks | Lider de Datos | lakehouse_databricks_columns.csv |
| Modelo Power BI Ventas | Power BI | Analista BI | powerbi_ventas.bim |
| CRM comercial | SQL Server | Vacío deliberadamente | crm_sqlserver.sql |
| Planillas de presupuesto | Archivos / planillas | Control de Gestion | Sin archivo |

### ERP: estructura transaccional

> "Cargo el DDL del ERP. Obtengo tablas, columnas y relaciones declaradas, no una prueba del significado de cada dato. Una clave técnica puede ayudar a unir registros, pero no explica cuándo un pedido cuenta como venta."

Importar con el ERP seleccionado. No conectar MariaDB ni ejecutar las sentencias. Revisar que aparezcan objetos con procedencia. Si la carga falla, detenerse antes de usar los objetos como evidencia.

### Lakehouse: representación analítica

> "El CSV es una exportación de columnas de la capa gold. Le dice a Atlas qué estructura existe. No estoy cargando importes de ventas ni autorizando acceso a todas las filas."

Mostrar que nombres y estructuras difieren de los del ERP. La equivalencia de nombres no garantiza igualdad de claves, de valores o de granularidad.

### Power BI: semántica existente

> "No empezamos como si la empresa no hubiera construido nada. Este BIM trae un modelo con medidas y relaciones. Lo incorporamos como fuente, pero las fórmulas técnicas todavía necesitan interpretación de negocio."

Revisar tablas, medidas y relaciones. Que una medida exista no confirma sus exclusiones ni explica sus totales. ONTO complementa ese modelo, no lo sustituye automáticamente.

### CRM y planillas: dos faltas diferentes

El CRM sí tiene DDL, pero no responsable. Las planillas tienen responsable y existencia declarada, pero no estructura entregada. No inventar columnas de presupuesto para terminar el inventario.

> "En CRM falta gobierno, no toda la estructura. En presupuesto falta metadata, no la existencia de la fuente. Necesitamos acciones diferentes para resolver esos huecos."

**Control:** cinco sistemas declarados, cuatro inventariados. Mostrar que una reimportación reemplaza los objetos del sistema elegido, no todo el dominio. No confundir una carga de archivos con conectividad productiva.

## 6. Vincular preguntas a sistemas

**Pantalla:** Alcance, Agregar caso de uso. Registrar preguntas completas, responsables, prioridades y fuentes vinculadas.

| Caso | Pregunta | Prioridad y responsable | Sistemas |
| --- | --- | --- | --- |
| Rentabilidad por cliente | Que clientes generan mas margen y como evoluciona mes a mes? | Alta; Gerencia Comercial | ERP, lakehouse, Power BI |
| Pipeline vs ventas reales | Que oportunidades del CRM terminan en pedidos facturados? | Media; Jefe de Ventas | CRM, ERP |
| Cumplimiento de presupuesto | Como vamos contra el presupuesto mensual por zona? | Alta; Control de Gestion | Lakehouse, planillas |

> "No pido un catálogo indiscriminado. Para rentabilidad necesito explicar cliente y margen en varios sistemas. Para presupuesto sabemos que falta una fuente. Para conversión debemos distinguir oportunidad de venta facturada."

Los vínculos a los casos son por sistemas; delimitan y priorizan. No prueban que cada objeto del sistema sea semánticamente relevante para cada pregunta. Explicar el límite cuando se muestren filtros por caso.

**Control:** tres preguntas y fuentes correctas. La pregunta de presupuesto sigue en alcance aunque su fuente esté incompleta: esconderla mejoraría la apariencia, no la preparación del dominio.

## 7. Cargar documentos con intención

**Pantalla:** Contexto de negocio. Subir los tres documentos desde `input/documentation/`. Elegir Documentación funcional para glosario/equivalencias y, si se desea, Definiciones de KPI para indicadores. Pulsar Subir y revisar la tabla.

### Glosario: vocabulario y algunas reglas

Cliente es una empresa con al menos un pedido facturado en el ERP, identificada por `id_cliente`. Cliente activo requiere un pedido facturado en los últimos doce meses. Una Cuenta CRM puede representar cliente o prospecto y no existir en el ERP.

> "Estas palabras no son sinónimos. Si el agente llama cliente a todo prospecto, puede responder de forma convincente y equivocada. El glosario da una fuente identificable para distinguirlas."

El documento excluye pedidos ANULADOS de ventas y margen, exige pedido FACTURADO para que una oportunidad ganada cuente como venta y usa el corte diario de stock del lakehouse salvo reservas en línea. No describe todos los detalles necesarios para ejecutar esas reglas como consultas.

### Equivalencias: cruces parciales y dudas

El segundo documento vincula Cliente entre ERP, lakehouse, Power BI y el código ERP parcial del CRM; vincula Producto entre las tres primeras fuentes. Para Venta declara estructuras distintas y dudas de conciliación.

> "No disfrazo un borrador como contrato perfecto. El documento declara correspondencias parciales y preguntas abiertas. El sistema debe preservar esas dudas, no completar la relación por parecido de nombres."

Mantener las preguntas sobre cuentas CRM sin código ERP, conciliación de `venta_id` con un FactSales sin clave propia y responsables. No corregirlas antes del primer análisis: queremos ver qué brechas y pedidos aparecen.

### KPIs: fórmulas que siguen incompletas

Ventas netas suma importe neto de pedidos facturados sin anulados. Margen % divide margen bruto por ventas netas. Presupuesto compara ventas del mes y objetivo por zona. Conversión usa oportunidades ganadas con pedido facturado y oportunidades cerradas. Cobertura de stock usa venta promedio diaria de noventa días.

> "Una fórmula de una línea puede servir y seguir incompleta. Para Margen % quiero confirmar cómo se agregan sus componentes, qué filtros aplican y qué pasa con denominador cero. No quiero que el modelo transforme una frase breve en una especificación completa por su cuenta."

**Control:** tres documentos, textos extraídos, nombres correctos, sin duplicados ni contenido ajeno. Cargar todavía no es aprobar ni evaluar el significado.

## 8. Extraer contexto de negocio

**Pantalla:** Contexto de negocio. Mostrar la leyenda del motor antes de pulsar Analizar contexto de negocio. Confirmar proveedor y declarar el envío autorizado de documentos sintéticos.

> "Paso de documentos a propuestas estructuradas: conceptos, reglas y KPIs con referencias. El modelo organiza el material. Este botón no decide que las propuestas sean correctas."

Pulsar una vez y esperar. Después revisar el modo registrado del scanner, resultados y citas. Si usó reglas locales o hubo fallback, decirlo: no presentarlo como éxito LLM.

Mostrar un concepto Cliente/Cuenta, una regla de pedido facturado/anulado y un KPI de margen. Leer el texto original junto a la propuesta y buscar ampliaciones no respaldadas. Un JSON válido no equivale a semántica correcta.

**Si falla:** registrar estado y detener la etapa o pasar a material previo identificado como previo. No repetir cargas ni cambiar claves en pantalla. El contador de llamadas de la etapa siguiente pertenece al contraste de cobertura con presupuesto explícito, no a este scanner.

## 9. Diagnóstico basal y mapa entre sistemas

**Pantalla:** Diagnóstico. Pulsar Generar diagnóstico y registrar el ID. Es determinista; no realiza el contraste LLM de cobertura.

> "Miro preparación general: metadata, documentos, trazabilidad y alineación inicial. El score no autoriza a afirmar que entiendo cada elemento. Después veremos qué aspectos están respaldados por documentos."

Recorrer Brechas, Fuentes y Mapa entre sistemas. Cliente y Producto tienen correspondencias conocidas; Venta conserva dificultades de clave/conciliación. Se mantienen una fuente sin metadata, responsable CRM ausente y revisión funcional pendiente.

El score puede variar con las propuestas disponibles. La referencia determinista fue 4,0 con base parcial; una ejecución LLM histórica mostró 4,2. No forzar esas cifras. Explicar las dimensiones, no solo la nota global.

> "Atlas no dice que el presupuesto no exista. Dice que declaré el sistema, pero no le entregué estructura. El universo disponible no representa toda esa fuente."

**Control:** diagnóstico del proyecto nuevo, gaps visibles. Una disponibilidad alta de documentos no equivale a cobertura semántica alta.

## 10. Contraste LLM con progreso visible

**Pantalla:** Diagnóstico, Contraste semántico. Mostrar proveedor, modelo y política. Fijar Límite de llamadas en 12; pulsar Evaluar cobertura con LLM.

> "Doce es un techo de solicitudes, no una promesa de hacer doce. Atlas divide elementos y documentos en grupos. En una ejecución anterior de este caso planificó nueve. Con más contexto podría necesitar más; con cuarenta el mecanismo es el mismo."

El panel muestra llamada actual, solicitudes previstas y límite, por ejemplo `Llamada 1/9 · limite 12`. La descripción indica contraste documental o consolidación, número de elementos y algunos nombres. La barra avanza cuando termina cada solicitud.

> "Veo qué trabajo está en curso, no un porcentaje inventado del pensamiento del modelo. Mientras espera respuesta, sigue en esa llamada. No sé cuánto tiempo exacto le falta al proveedor."

El contador representa solicitudes de aplicación. Los reintentos internos del SDK pueden ocurrir dentro de una solicitud y no se enumeran como pasos nuevos. La barra indica llamadas finalizadas sobre previstas, no porcentaje de conocimiento aprobado ni confianza.

Si se muestra resultado reutilizado con cero llamadas nuevas, decir que hubo caché compatible. No relatar llamadas que no ocurrieron. En un proyecto nuevo no copiar assessments para fingir una ejecución limpia.

El presupuesto agotado, una cita/esquema inválido o un error del proveedor pueden dejar un contraste incompleto. Los fallos no demuestran ausencia documental. No tomar decisiones semánticas a partir de un error técnico.

**Control:** estado completo, llamadas, caché, fallos y pendientes. Registrar el ID semántico: será el origen del draft, distinto del basal anterior.

## 11. Leer cobertura sin maquillar incertidumbre

**Pantalla:** Cobertura explicativa. Mostrar entidades, relaciones, KPIs y propiedades. Elegir una muestra de las cuatro familias en diferentes sistemas.

| Estado | Interpretación |
| --- | --- |
| Explicado | Aspectos requeridos con respaldo validado técnicamente; semántica por revisar humanamente. |
| Parcial | Algunos aspectos respaldados; otros faltan. |
| Sin explicación | No se encontró respaldo suficiente; revisar posibles falsos negativos. |
| Contradictorio | Hay conflicto material de evidencia; no resolver automáticamente. |
| Sin evaluar / fallo | La evaluación no se completó; no contar como ausencia documental. |

> "No alcanza con encontrar un nombre en un documento. Una entidad necesita significado, granularidad e identificación. Un KPI necesita definición, fórmula, granularidad y filtros/exclusiones. Una descripción breve puede dejar muchos elementos parciales."

Abrir citas y leerlas literalmente. Comprobar que respaldan el aspecto atribuido. La herramienta verifica IDs, requisitos y citas; no reemplaza la lectura humana del significado.

La ejecución real del 2026-10-06 evaluó 107 elementos disponibles: 17 entidades, 9 relaciones, 2 KPIs técnicos y 79 propiedades. Ninguno quedó completamente explicado: 22 parciales y 85 sin explicación, sin contradicciones detectadas. Es historia, no un resultado prometido. Los KPIs extraídos del texto no tienen por qué coincidir en cantidad con los KPIs técnicos de este universo.

> "Cero completamente explicados no significa que no se evaluó nada. Terminó de procesar el universo disponible y faltan aspectos para dar cada elemento por explicado. Ahora puedo ver qué pedir, en lugar de esconderlo detrás de una nota alta."

Cambiar filtros y observar que no cambian el denominador. Recordar las planillas sin metadata: el universo disponible sigue incompleto.

## 12. Mostrar hipótesis útiles del modelo

**Pantalla:** detalle de elemento, explicación inferida. Leer advertencia, fundamento, supuestos y validaciones pendientes. Las citas motivadoras no son pruebas del aspecto.

> "Le dimos libertad para proponer posibilidades desde el contexto y su conocimiento general. Esa libertad está separada del respaldo documental. No lo presenta como una regla de la empresa ni inventa un porcentaje de certeza."

Ejemplos históricos para explicar, no respuestas que debamos forzar:

1. **DimCustomer:** una fila por cliente actual o por versión histórica. El modelo conoce ambas formas; los documentos no permiten elegir. Confirmar con BI y revisar transformación.
2. **CustomerKey:** identificador ERP reutilizado o clave sustituta. Una equivalencia no demuestra igualdad de valores. Revisar generación, correspondencias y valores especiales.
3. **Margen %:** cociente de sumas o promedio de porcentajes de líneas. El conocimiento financiero/BI explica la diferencia; medida y totales deben revisarse para decidir.

La ejecución histórica produjo 114 hipótesis. No son 114 aspectos documentados, aprobaciones o necesariamente candidatos Nexo. Puede haber varias por elemento y las cantidades pueden variar.

**Control:** no elevan cobertura, resuelven contradicciones ni cierran pedidos. Si preguntan cuál es correcta, explicar qué fuente o persona falta, no elegir la opción más plausible.

## 13. Convertir faltantes en pedidos

**Pantalla:** Pedidos de información en Cobertura explicativa. Mostrar elemento, información requerida, responsable propuesto, prioridad y criterio de cierre.

> "No termino en 'falta información'. Para DimCustomer pido qué representa una fila y qué la identifica. Para Margen % pido nivel de cálculo, filtros y tratamiento del denominador cero. Es un trabajo concreto que puede asignarse y verificarse después."

El responsable está por confirmar, no aceptó una tarea automáticamente. La prioridad no prueba urgencia negociada. Cerrar requiere nueva evidencia pertinente y reevaluación, no una hipótesis convincente.

Distinguir fuente sin estructura, definición incompleta y análisis fallido. Requieren respectivamente inventario, explicación de negocio y completar el contraste. No solicitar documentos para disimular una llamada fallida.

**Pendientes deliberados:** estructura de planillas, responsable CRM, cuentas sin código ERP, conciliación de Venta y aspectos no documentados. El público debe poder reconocerlos al cerrar la primera iteración.

## 14. Nexo: de propuestas a decisiones

**Pantalla:** Nexo, Crear draft desde un diagnóstico Atlas. Elegir el assessment semántico recién revisado; seleccionar alcance híbrido para combinar documentación y metadata. Crear draft y registrar su ID.

> "Cambio de responsabilidad. Atlas ayudó a ver y contrastar. Nexo pide decidir qué aceptamos. Tener una propuesta del modelo o una tabla importada no equivale a tener conocimiento aprobado."

En Revisión de candidatos, mostrar concepto, regla y KPI; leer definiciones y evidencias, buscar conflictos y registrar decisiones con revisor/rol/nota. En Modelo canónico revisar propiedades, relaciones, KPIs y pendientes que se incorporarán.

Las inferencias Atlas no se transforman automáticamente en una colección equivalente de candidatos Nexo. El draft usa el assessment y el inventario/contexto. No decir que una hipótesis pasó a la release por aprobar otro candidato de nombre parecido.

### Aprobación por lote ante el público

Primero tomar decisiones individuales y explicar evidencia. Si se usa lote para completar la demo sintética, mostrar el conjunto y declarar qué se revisó y qué no. La herramienta registra la decisión humana; no certifica lectura de cada elemento.

> "Para el ritmo de esta demo registro decisiones por lote sobre el conjunto mostrado. Esto prueba el flujo de gobierno, no sustituye la revisión individual que pediría en un uso real."

No aprobar incertidumbres solo para habilitar el siguiente botón. Rechazar con motivo o dejar pendiente; si hay pendientes, detener emisión. No confundir revisor de demo con dueño efectivo del significado del dominio.

## 15. Emitir una release reconstruible

**Pantalla:** Release y entrega a la plataforma. Confirmar que no queden decisiones pendientes, revisar lo aprobado y completar revisor/rol/nota. Emitir release; guardar su ID.

> "La release es una fotografía de lo decidido, con procedencia y revisión. Argos y los paquetes deben apuntar a ese ID, no al borrador mutable ni a hipótesis pendientes."

Nota propuesta: "Demo sintética; decisiones individuales y por lote; muestra revisada y limitaciones registradas". No escribir "validado por negocio" si no ocurrió.

Revisar conceptos, reglas, KPIs y bindings. Emitir no concede acceso a filas, crea conexiones ERP ni publica en plataformas. Sin catálogo/bindings aprobados, Argos probará conocimiento, no calculará ventas operativas.

**Control:** release del proyecto nuevo, solo contenido decidido, límites visibles. La revisión del diagnóstico Atlas y la aprobación Nexo son decisiones distintas.

## 16. Argos: responder y abstenerse

**Pantalla:** Argos, Conversación. Seleccionar explícitamente la release nueva y verificar ID. No usar una release anterior para validar el draft nuevo.

Preguntar `¿Qué es Cliente?` si se aprobó el concepto. Leer respuesta y evidencias: debe conservar condición de pedido facturado y no confundir cliente, prospecto y cuenta.

> "No celebro que el modelo conozca la palabra cliente. Compruebo que use la definición de esta distribuidora y la evidencia aprobada."

Preguntar `¿Qué planeta es más grande?`. Esperar abstención por falta de evidencia autorizada en la release.

> "Es fácil para un modelo general. Por eso sirve: este investigador no debe salirse del caso solo porque sabe algo por fuera."

No esperar cifras de ventas de ayer si no hay consulta declarada, parámetros y binding aprobado. Cargar el BIM no concede esos accesos. La abstención ante ese límite puede ser correcta.

En Analistas, preparar batería base, revisar preguntas, estados y evidencias esperadas, y ejecutarla. Mostrar total, OK y fallidos; revisar cada fallo. La batería prueba criterios declarados, no toda la verdad semántica.

El caso original pasó 6/6 históricamente sobre una release anterior aprobada. No atribuirlos a una nueva sin ejecutarla. Con otro contenido, cambian batería y cantidades.

## 17. Entrega a Fabric y Databricks

**Pantalla:** Nexo, Release y entrega a la plataforma. Preparar paquetes de ambos destinos para la release validada; revisar cobertura, archivos y pendientes. Descargar para inspección, sin publicar.

> "ONTO no compite con la ontología nativa. Prepara conocimiento gobernado y artefactos para que la plataforma implemente lo viable. Argos prueba y sostiene un respaldo cuando parte del escenario no se puede implementar allí."

| Ruta | Explicación |
| --- | --- |
| A | Alcance implementable en la plataforma destino. |
| B | Mixta: parte alcanzable y parte que requiere puentes o resolución adicional. |
| C | Runtime de respaldo cuando el alcance no es viable en el destino. |

El alcance original recomendó B: hay fuentes analíticas y otras con trabajo de integración. Mirroring, shortcuts o federación pueden cambiar la viabilidad. MariaDB por sí sola no obliga a C ni prueba que un puente exista.

Mostrar exclusiones, bindings por resolver y modelo/artefactos propuestos. No prometer conteos del runner si la release aprobada es distinta.

**Límite:** generar un ZIP local no es desplegar, validar en una plataforma real ni conceder permisos. La publicación nativa requiere otra acción explícita y autorizaciones propias.

## 18. Segunda iteración: mejorar con evidencia

Escena opcional para sesión larga. No consiste en pedir más seguridad al modelo, sino entregar la explicación faltante y comparar conservando el assessment inicial.

**Escenario sintético:** BI confirma cómo se modeló DimCustomer en esta demo. Declarar que es información construida para el ejemplo, no una comprobación de una empresa real. Agregar un documento funcional; no cambiar la base legacy ni el BIM para esconder la carencia.

```markdown
# Definicion de DimCustomer para esta demo sintetica
DimCustomer representa los clientes definidos en el glosario comercial.
Cada fila representa un cliente actual; no conserva versiones historicas.
CustomerKey identifica de forma unica cada fila de DimCustomer.
La correspondencia con id_cliente del ERP debe revisarse por separado.
```

> "No le doy permiso para inventar. Le doy granularidad e identificación explícitas. La correspondencia entre claves sigue siendo una pregunta separada."

Subir, revisar procedencia, reanalizar contexto si quedó invalidado y generar otro contraste. En Comparación elegir inicial y final. Leer aspectos/citas antes y después; no garantizar mejora sin mirar evidencia.

Con mismo alcance y criterios, el delta es comparable. Si agregamos fuentes, excluimos elementos o cambiamos criterios, mostrar denominadores y no venderlo como avance semántico puro. Una evidencia nueva puede introducir contradicciones y bajar cobertura. Un cierre propuesto sigue sin ser cierre humano confirmado.

## 19. Contingencias en vivo

| Situación | Qué hacer | Qué evitar |
| --- | --- | --- |
| Proveedor no habilitado | Revisar entorno antes o mostrar resultado previo identificado. | Atribuir reglas locales al LLM. |
| Llamada lenta | Mostrar llamada/tarea; esperar sin repetir botón. | Inventar duración restante. |
| Presupuesto insuficiente | Registrar incompleto y decidir si repetir. | Contar no evaluados como falta documental. |
| Cita/esquema inválido | Conservar fallo y revisarlo. | Aprobar porque parece convincente. |
| Caché | Declarar reutilización y cero llamadas nuevas. | Simular un análisis fresco. |
| Cero completos | Leer parciales, aspectos y fuente faltante. | Confundirlo con cero procesamiento. |
| Candidato dudoso | Pendiente o rechazo con motivo; detener release. | Aprobar para habilitar Argos. |
| Argos sin límite esperado | Guardar pregunta, release y evidencia; investigar. | Ignorar un fallo porque otros pasaron. |
| Destino incompleto | Revisar ruta, puentes y exclusiones. | Llamar publicación a un ZIP local. |

En versión corta, preparar una release revisada y paquetes con IDs. Separar material precomputado de ejecución en vivo. No esconder espera mediante atribuciones falsas.

## 20. Cierre y registro

> "Empezamos con estructuras y documentos separados. Terminamos con un universo conocido pero incompleto, explicaciones con evidencia, hipótesis etiquetadas, pedidos concretos, decisiones humanas y una release que podemos probar y preparar para la plataforma. El valor no es pintar todo de verde: es saber qué podemos afirmar y qué falta antes de confiar en una respuesta."

Completar durante la presentación; no marcar pasos por anticipado:

| Dato | Registro |
| --- | --- |
| Fecha, revisor y naturaleza de validación | |
| Proyecto y archivos | |
| Scanner: proveedor, modo y estado | |
| Assessment basal y semántico | |
| Llamadas previstas/realizadas, límite, caché y fallos | |
| Universo y cobertura por familia | |
| Muestra leída: aspectos, citas y veredicto | |
| Hipótesis y pendientes no confirmados | |
| Draft: decisiones individuales y lote | |
| Release probada | |
| Argos: preguntas, batería, aciertos y fallos | |
| Paquetes: destinos, release, rutas y exclusiones | |
| Segunda iteración y comparabilidad, si hubo | |
| Próxima acción y responsable por confirmar | |

## 21. Apéndice: otros casos y reproducibilidad

La demo principal es ventas distribuidas. No mezclar silenciosamente otros inventarios o releases en el mismo relato.

**Comercial sintética:** el runner `scripts/run_commercial_sales_demo.py` usa otro caso con datos sintéticos operativos y `sales_by_customer` mediante adapter `local_synthetic`, binding aprobado y parámetros. Esa capacidad no aparece en `test2` por cargar el BIM del caso distribuido.

**Fabric SIC/riesgo:** cambia inventario, reglas y alcance. El patrón Atlas/Nexo/Argos aplica, pero ese dominio no es la única razón de existir de ONTO. No trasladar sus conteos o conexiones a ventas.

**Runner distribuido:** `scripts/run_distributed_demo.py` puede regenerar el caso, aprobar candidatos de demo y emitir paquetes. Revisar `--keep` y efectos de reinicio; no usarlo para reparar en silencio una presentación manual.

**Runner LLM:** `scripts/run_onto_demo.py --full-cycle --max-calls 12` requiere una release previa. Scanner/Atlas generan un draft pendiente, pero Argos y exportación usan la release anterior aprobada. No verifica el contenido nuevo. El recorrido manual revisa, emite y prueba una release nueva.

Claves y datos locales no se versionan. Los resultados históricos se narran en documentación; el JSON completo queda en el paquete local. Clonar GitHub exige instalar dependencias y configurar un entorno autorizado para repetir llamadas reales.
