# Argos - Runtime & Evaluation MVP

Estado: MVP operativo implementado con adapters local_synthetic, Fabric y MariaDB
Producto: 3 de 3 de ONTO

## Qué es Argos

Argos es el investigador de negocio de ONTO. Consulta una release Nexo aprobada, no los documentos crudos ni un modelo libre. Su funcion es responder dentro del contexto aprobado y declarar una abstencion cuando la release no contiene evidencia suficiente.

Argos cumple dos roles y ninguno compite con la plataforma del cliente:

1. **Banco de prueba:** demuestra con preguntas reales que el contexto aprobado funciona antes de implementarlo en Fabric, Databricks u otra plataforma.
2. **Runtime de plan B:** sirve la parte del conocimiento que la plataforma no puede implementar de forma viable (ruta mixta o plan B).

Argos separa dos dependencias:

1. **Contexto ontologico:** conceptos, reglas, KPIs, relaciones, bindings y limites aprobados por Nexo.
2. **Datos operativos:** filas o agregados recuperados desde Fabric, MariaDB u otro repositorio mediante operaciones nombradas y autorizadas. `local_synthetic` permite la demo comercial.

El repositorio de datos no se convierte por ello en el repositorio ontologico. Una plataforma puede participar en ambos planos, pero cada acceso queda registrado con su contrato y finalidad.

El context pack puede incluir activos técnicos y `data_bindings` aprobados. Las preguntas de negocio que coinciden con una operación nombrada ejecutan consultas parametrizadas de solo lectura; nunca se acepta SQL libre. En Risk, `¿Cual es el riesgo de la regla 1 en el SIC 12?` se traduce a `risk_rule_sic` y devolvio una fila real. En Ventas, una pregunta por cliente se traduce a `sales_by_customer` con datos sinteticos. En Nalub, la pregunta por los 10 productos mas demandados de 2025 se traduce a `product_demand_by_year`.

La configuración LLM declara `ONTO_LLM_DATA_POLICY`: `approved_external` permite usar el proveedor configurado bajo la autorización del piloto; `local_only` bloquea proveedores externos y solo permite Ollama local. El valor se valida al cargar la configuración y no se envían prompts a un proveedor externo cuando la política es `local_only`.

La retención local dispone de un informe manual por proyecto y release: conserva las últimas `N` investigaciones y marca las anteriores como candidatas. El informe no borra archivos; cualquier purga requiere revisión explícita.

## Pantalla de Argos

La pantalla (`onto_ui/argos.py`) usa la release aprobada mas reciente y tiene dos pestanas:

- **Conversacion:** chat en orden cronologico. Si no hay historial, ofrece preguntas iniciales; cada respuesta muestra el resultado (metricas, grafico o tabla), las preguntas sugeridas y un desplegable de evidencia y trazabilidad. Las abstenciones se muestran como advertencia. "Limpiar conversacion" solo afecta la vista; las investigaciones quedan persistidas.
- **Analistas:** catalogo de consultas autorizadas de la release y bateria de evaluacion.

Las preguntas iniciales y las visualizaciones se declaran en el catalogo de cada consulta, no en el codigo:

```json
{
  "query_name": "risk_levels",
  "example_question": "¿Cómo se distribuyen los riesgos por nivel?",
  "visualization": {"type": "bar", "x": "riesgo_final_texto", "y": "total_rows"}
}
```

`visualization` admite `bar` (`x`, `y`) o `metrics` (`fields`). Sin declaracion, una fila se muestra como metricas y varias filas con una categoria y un valor numerico como barras. Las releases anteriores sin `example_question` usan un conjunto conocido de preguntas por nombre de consulta.

## Flujo implementado

1. La persona selecciona una release local de Nexo.
2. Argos recupera conceptos, reglas, KPIs y estructuras canónicas del `agent_context_pack`.
3. Si corresponde, ejecuta una consulta nombrada en el adapter indicado y devuelve sus filas; también devuelve elementos recuperados y bindings de evidencia, o `abstained` si no hay coincidencias. La ruta LLM interpreta la pregunta y redacta sobre el mismo contexto aprobado y resultado live.
4. Cada investigacion queda guardada bajo `data/runtime/<project>/<release>/<investigation>/` con manifest, request, retrieval, traceability, `audit.json` y answer. La auditoria registra proyecto, release, estado, actor local, hash de la pregunta, LLM utilizado, consulta/adaptador, operación, estado del adapter y cantidad de filas; no persiste secretos ni la pregunta en claro dentro de `audit.json`. La UI reconstruye el historial persistido después de una recarga.

## Batería de evaluación

La pantalla de Argos puede proponer una batería editable a partir de los elementos de la release. Cada línea declara:

```text
pregunta | expected_status (answered/abstained) | elemento de evidencia esperado opcional
```

Una evaluación valida el estado esperado y, cuando se indica, que se haya recuperado el elemento de evidencia esperado. Las lineas con un estado distinto de `answered` o `abstained` se rechazan antes de ejecutar. El paquete resultante contiene manifest, resumen y resultados detallados bajo:

```text
data/runtime/<project>/<release>/evaluations/<evaluation-id>/
```

Validacion historica ejecutada sobre la release documentation-first del piloto Fabric:

- Release: `release-2026-08-11T07-54-06-00-00-afcfe679c7b9`.
- Casos: 6 (`5` respondibles y `1` fuera de alcance).
- Resultado: `6 passed`, `0 failed`.
- Paquete: `data/runtime/fabric-gold-sic-risk-pilot/release-2026-08-11t07-54-06-00-00-afcfe679c7b9/evaluations/`.

Validacion live del caso Nalub:

- Proyecto: `nalub-case`.
- Catalogo: `order_status_summary`, `sales_summary`, `product_demand_by_year`, `customer_debt`, `product_availability`.
- `product_demand_by_year`: 10 filas reales de 2025, con codigo, unidades solicitadas y cantidad de pedidos.
- Seguridad: templates allowlisted, parametros validados, `SELECT`, sesion MariaDB read-only y perfil aislado por proyecto.

## Límites actuales

- Las operaciones live están limitadas a las plantillas allowlisted disponibles; todavía no cubren todo el catálogo de preguntas de negocio del piloto.
- Cada release recibe routing, parametros, binding requerido, limites, adapter y `connection_profile` desde su catalogo. El adapter local sintetico ejecuta `sales_by_customer`; Fabric mantiene el piloto SIC; MariaDB ejecuta las capacidades de Nalub.
- No hay autenticación ni autorización por usuario; la auditoria actual identifica la ejecución como `local-user` y es una base técnica, no un control multiusuario.
- La suite debe ampliar pruebas de granularidad, permisos, latencia y cobertura de los catálogos de cada dominio.
- Los casos sugeridos filtran nombres tecnicos genericos; aun requieren curacion humana para representar preguntas de negocio reales.

## Criterio de avance

Antes de sumar nuevos conectores o dominios, cada dominio piloto debe demostrar que sus casos respondibles recuperan evidencia correcta y que sus casos fuera de alcance producen abstención consistente.
