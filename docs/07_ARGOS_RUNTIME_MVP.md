# Argos - Runtime & Evaluation MVP

Estado: primer corte vertical implementado  
Producto: 3 de 3 de ONTO

## Qué es Argos

Argos es el investigador de ONTO. Consulta una release Nexo aprobada, no los documentos crudos ni un modelo libre. Su función es responder dentro del contexto aprobado y declarar una abstención cuando la release no contiene evidencia suficiente.

El context pack puede incluir activos técnicos Fabric y `data_bindings` aprobados. Las preguntas de negocio que coinciden con una operación nombrada ejecutan consultas Fabric parametrizadas de solo lectura; nunca se acepta SQL libre. Por ejemplo, `¿Cuál es el riesgo de la regla 1003 en el SIC12?` se traduce a la operación allowlisted `risk_rule_sic` con los parámetros `id_risc=1003` y `sic=12`.

## Flujo implementado

1. La persona selecciona una release local de Nexo.
2. Argos recupera conceptos, reglas, KPIs y estructuras canónicas del `agent_context_pack`.
3. Si corresponde, ejecuta una consulta Fabric nombrada y devuelve sus filas; también devuelve elementos recuperados y bindings de evidencia, o `abstained` si no hay coincidencias. La ruta LLM aplica la misma recuperación previa y no acepta como respuesta una afirmación sin evidencia contextual o resultado live.
4. Cada consulta queda guardada bajo `data/runtime/<project>/<release>/<investigation>/`.

## Batería de evaluación

La pantalla de Argos puede proponer una batería editable a partir de los elementos de la release. Cada línea declara:

```text
pregunta | expected_status (answered/abstained) | elemento de evidencia esperado opcional
```

Una evaluación valida el estado esperado y, cuando se indica, que se haya recuperado el elemento de evidencia esperado. El paquete resultante contiene manifest, resumen y resultados detallados bajo:

```text
data/runtime/<project>/<release>/evaluations/<evaluation-id>/
```

Validacion ejecutada sobre la release documentation-first del piloto Fabric:

- Release: `release-2026-08-11T07-54-06-00-00-afcfe679c7b9`.
- Casos: 6 (`5` respondibles y `1` fuera de alcance).
- Resultado: `6 passed`, `0 failed`.
- Paquete: `data/runtime/fabric-gold-sic-risk-pilot/release-2026-08-11t07-54-06-00-00-afcfe679c7b9/evaluations/`.

## Límites actuales

- Las operaciones live están limitadas a las plantillas allowlisted disponibles; todavía no cubren todo el catálogo de preguntas de negocio del piloto.
- No hay autenticación, autorización por usuario ni allowlists de plataforma.
- La suite aún debe ampliar pruebas de granularidad, permisos y cobertura del catálogo ACU del dominio piloto.
- Los casos sugeridos filtran nombres tecnicos genericos; aun requieren curacion humana para representar preguntas de negocio reales.

## Criterio de avance

Antes de habilitar conectores externos, un dominio piloto debe demostrar que sus casos respondibles recuperan evidencia correcta y que sus casos fuera de alcance producen abstención consistente.
