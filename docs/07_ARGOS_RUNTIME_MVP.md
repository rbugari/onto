# Argos - Runtime & Evaluation MVP

Estado: primer corte vertical implementado  
Producto: 3 de 3 de ONTO

## Qué es Argos

Argos es el investigador de ONTO. Consulta una release Nexo aprobada, no los documentos crudos ni un modelo libre. Su función es responder dentro del contexto aprobado y declarar una abstención cuando la release no contiene evidencia suficiente.

El context pack puede incluir activos técnicos Fabric y `data_bindings` aprobados. El contrato actual indica que cualquier evolución hacia datos operativos deberá ser de solo lectura, con `SELECT` y bindings explícitos; Argos aún no ejecuta consultas Fabric desde una pregunta libre.

## Flujo implementado

1. La persona selecciona una release local de Nexo.
2. Argos recupera conceptos, reglas, KPIs y estructuras canónicas del `agent_context_pack`.
3. Devuelve respuesta, elementos recuperados y bindings de evidencia, o `abstained` si no hay coincidencias.
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

## Límites actuales

- La recuperación es determinista sobre el context pack local; aún no usa un gateway read-only hacia una fuente del cliente.
- No hay autenticación, autorización por usuario ni allowlists de plataforma.
- La suite aún no incorpora pruebas de granularidad, permisos o datos operativos reales de un dominio piloto.

## Criterio de avance

Antes de habilitar conectores externos, un dominio piloto debe demostrar que sus casos respondibles recuperan evidencia correcta y que sus casos fuera de alcance producen abstención consistente.
