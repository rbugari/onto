# Caso: ventas en un dominio distribuido (cinco sistemas)

| | |
| --- | --- |
| Tipo | Sintetico (sin datos reales) |
| Objetivo | Probar el inventario multi-sistema, el mapa de entidades compartidas y la ruta mixta |
| Ruta esperada | **B** en Fabric (26/39) y en Databricks (33/45): ERP y CRM no son alcanzables sin puente |
| Regenerar | `python scripts/run_distributed_demo.py` (agregar `--keep` para no borrar lo anterior) |

## Origenes

| Sistema | Plataforma | Archivo en `input/` | Responsable |
| --- | --- | --- | --- |
| ERP operativo | MariaDB | `erp_mariadb.sql` | Jefe de Sistemas |
| Lakehouse analitico | Databricks | `lakehouse_databricks_columns.csv` | Lider de Datos |
| Modelo Power BI Ventas | Power BI | `powerbi_ventas.bim` | Analista BI |
| CRM comercial | SQL Server | `crm_sqlserver.sql` | **sin responsable** (a proposito) |
| Planillas de presupuesto | Planillas | **sin archivo** (a proposito) | Control de Gestion |

`input/scope.json` declara los sistemas y tres casos de uso. `input/documentation/` tiene glosario, equivalencias entre sistemas y KPIs.

## Que cargar en Atlas (UI)

1. **Alcance**: cliente `demo-distribuidora`, dominio `comercial`, producto `ventas-distribuidas`, responsable Gerencia Comercial. Casos de uso de `scope.json`:
   - Rentabilidad por cliente (alta): ERP, lakehouse, Power BI.
   - Pipeline vs ventas reales (media): CRM, ERP.
   - Cumplimiento de presupuesto (alta): lakehouse, planillas.
2. **Fuentes**: registrar los cinco sistemas con la plataforma y responsable de la tabla; importar el archivo de cada uno (las planillas quedan declaradas sin archivo).
3. **Contexto**: subir los 3 documentos y analizar.
4. **Diagnostico**: generar.

## Resultado esperado

**4,0 partial_foundation** (la brecha alta impide `strong`).

| Dimension | Puntaje | Lectura |
| --- | --- | --- |
| Metadata tecnica | 5 | Cubierto |
| Contexto de negocio | 5 | Cubierto |
| Cruce tecnico-negocio | 3 | Casi |
| Gobierno y trazabilidad | 5 | Cubierto |
| Alineacion entre sistemas | 2 | Falta |

Entidades compartidas: Cliente y Producto (ERP, lakehouse, Power BI) con clave comun; Venta (lakehouse, Power BI) **sin** clave comun.

Brechas (todas intencionales):

- alta / fuentes: planillas de presupuesto sin metadata;
- media / gobierno: CRM sin responsable;
- media / entre_sistemas: Venta sin clave comun;
- media / negocio: revision funcional pendiente.

## Despues de Atlas

El script aprueba todo (solo para la demo), emite la release y genera los paquetes para Fabric y Databricks con ruta B.

## Validacion manual desde cero: 2026-10-07

Este recorrido usa el mismo caso y los mismos archivos, pero un **proyecto nuevo**: `Distribuidora - Validacion manual 2026-10-07`. No crear ese proyecto ni ejecutar otro ciclo hasta la sesion manual. Conservar el proyecto `distribuidora-ventas-distribuidas`, su historial, el draft pendiente y la release anterior como referencia de lo ejecutado el 2026-10-06.

No ejecutar los scripts de regeneracion o ciclo completo durante esta validacion: pueden reiniciar el caso o automatizar etapas que queremos revisar. No importar el proyecto ya procesado ni copiar sus assessments, drafts o releases. Empezar desde los archivos de entrada evita heredar resultados y permite comprobar un contraste nuevo, sin cache previa de este proyecto. No hace falta borrar datos ni cambiar la configuracion del modelo.

### Preparacion

- Abrir http://127.0.0.1:8601/?lang=es. Si el servidor no esta disponible, desde la raiz del repo iniciar `.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py --server.port 8601` usando la carpeta de datos del repositorio, no datos temporales de pruebas.
- Confirmar en la configuracion tecnica del contexto/contraste: proveedor `azure_openai`, deployment `gpt-6.1-sol`, politica autorizada. La clave permanece en la configuracion local: no copiarla al registro de validacion.
- Usar exclusivamente los archivos de la tabla Origenes y los tres documentos de [input/documentation](input/documentation). Mantener intencionalmente CRM sin responsable y planillas sin metadata; completar esas brechas seria una segunda iteracion, no el caso inicial.
- Completar nombre y rol del revisor de la sesion. Registrar IDs y observaciones en la plantilla al final; una captura o una salida plausible no equivale a aprobacion.

### Recorrido y puntos de control

Avanzar una etapa por vez, detenerse para revisar su resultado y registrar observaciones antes de la siguiente. Los resultados del LLM pueden variar: los numeros de la ejecucion anterior son referencia, no valores que debamos forzar.

| Paso | Accion manual | Comprobar antes de avanzar |
| --- | --- | --- |
| 1. Proyecto | Crear el proyecto nuevo y abrirlo. | ID distinto del proyecto anterior; sin diagnosticos, drafts ni releases heredados. |
| 2. Alcance | Completar cliente, dominio, producto y responsable indicados arriba; registrar los tres casos de uso de [scope.json](input/scope.json#L1). Vincular sus sistemas despues de registrarlos. | Mismo alcance comercial, prioridades y sistemas del caso. |
| 3. Fuentes | Registrar los cinco sistemas e importar sus cuatro archivos de metadata. | 4/5 sistemas inventariados; CRM sin responsable y planillas declaradas sin archivo. Revisar tablas, columnas, medidas, relaciones y mapa entre sistemas. |
| 4. Documentos | En Contexto de negocio, subir los tres documentos y revisar sus textos. | Glosario, equivalencias y KPIs correctos, sin duplicados ni documentos ajenos. |
| 5. Scanner | Accionar Analizar contexto de negocio. | Estado del scanner y modo Azure real, no fallback heuristico; revisar conceptos, reglas, KPIs y citas propuestos. Si falla, registrar y detenerse. |
| 6. Basal | En Diagnostico, accionar Generar diagnostico. | Registrar run_id, score, gaps y universo. El score basal no es cobertura explicativa; todavia no confundir elementos sin evaluar con falta documental. |
| 7. Contraste | Abrir Contraste semantico, fijar Limite de llamadas en 12 y accionar Evaluar cobertura con LLM. | Nuevo assessment seleccionado; analisis completo, sin fallos ni pendientes; Reutilizado: No. Si aparece cache, fallo o presupuesto insuficiente, investigar antes de avanzar. |
| 8. Cobertura | Abrir Cobertura explicativa; recorrer grupos, sistemas, aspectos y pedidos. | Denominadores y fuentes incompletas visibles. Revisar al menos una entidad, relacion, KPI y propiedad, y elementos de los distintos sistemas. Cada respaldo debe tener cita literal y ser semanticamente pertinente; buscar falsos respaldos y falsos negativos. |
| 9. Inferencias | Abrir las explicaciones inferidas de los elementos seleccionados. | Advertencia de aporte importante del modelo, fundamento, supuestos y validaciones pendientes. Las citas contextuales no son prueba. No aumentan cobertura ni cierran pedidos. Comprobar hipotesis de historia de DimCustomer, claves y agregacion de Margen % si aparecen. |
| 10. Nexo | Crear draft desde el assessment semantico seleccionado; revisar autoridad de fuentes, candidatos, evidencias, conflictos y el modelo. | Registrar draft_id. Las inferencias Atlas y los candidatos Nexo son colecciones distintas; no esperar igualdad de cantidades. Aprobar solo lo validado, rechazar lo no aceptado con motivo o dejarlo pendiente. No usar aprobacion masiva de demo. |
| 11. Release | Solo cuando no queden decisiones pendientes y el contenido aprobado sea suficiente, emitir una release con revisor y nota. | Registrar release_id y revisar exactamente lo incluido. Si quedan pendientes, detenerse aqui: no aprobarlos para habilitar Argos. La release anterior no valida el nuevo draft. |
| 12. Argos | Seleccionar explicitamente la release manual nueva. Preguntar Que es Cliente? si ese concepto esta aprobado, y Que planeta es mas grande?. En Analistas, preparar y revisar la bateria base antes de ejecutarla. | Respuesta de dominio con evidencia aprobada y abstencion fuera de evidencia. Registrar release usada y casos/resultados; ni draft ni hipotesis pendientes deben fundamentar respuestas. Si no hay bindings/catalogo aprobados, no esperar consultas operativas. |
| 13. Entrega | Desde Release y entrega a la plataforma, preparar paquetes locales de Fabric y Databricks y revisar cobertura, ruta, archivos y pendientes. | Misma release manual aprobada en ambos paquetes. Ruta depende de alcance y puentes disponibles, no de la etiqueta MariaDB por si sola. No publicar en plataformas durante esta validacion. |

### Referencia del ciclo real anterior

El 2026-10-06, el proyecto original tuvo scanner Azure real, 107 elementos disponibles evaluados y 9 llamadas Atlas: 0 completamente explicados, 22 parciales, 85 sin explicar y 114 hipotesis separadas. Se creo un draft con 120 candidatos pendientes. No se aprobo ni publico nuevo conocimiento. Argos paso 6/6 casos sobre la **release anterior** y los paquetes locales se generaron de esa misma release; esos resultados no validan el nuevo draft.

Estos resultados no sustituyen la referencia basal determinista de arriba ni obligan al modelo a repetir cantidades o redaccion. El universo sigue incompleto por las planillas sin metadata. Ver [registro del ciclo real](../../16_PLAN_ATLAS_COBERTURA_EXPLICATIVA.md) para el resumen persistido y las verificaciones tecnicas.

### Registro de la sesion manual

Completar durante la sesion, sin marcar pasos anticipadamente:

| Dato | Valor u observacion |
| --- | --- |
| Fecha, revisor y rol | |
| project_id nuevo | |
| Archivos cargados, sistemas y casos de uso | |
| Scanner: modo, estado y observaciones | |
| run_id basal y score | |
| run_id semantico, estado, llamadas, cache y universo | |
| Cobertura por grupo, fallos y pendientes | |
| Muestra revisada: elemento/aspecto/cita, veredicto y motivo | |
| Hipotesis aceptadas para investigar, supuestos y validaciones | |
| Pedidos pendientes y responsables por confirmar | |
| draft_id y decisiones pendientes/aprobadas/rechazadas | |
| release_id manual, o motivo para detenerse antes de emitirla | |
| Argos: release usada, preguntas, evidencias, abstencion y bateria | |
| Paquetes locales: release, destinos, rutas y pendientes | |
| Defectos, dudas y siguiente iteracion | |
