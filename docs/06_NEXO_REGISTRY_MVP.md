# Nexo - Registry & Validation MVP

Estado: segundo corte vertical implementado (modelo canónico v0.2)  
Producto: 2 de 3 de ONTO

## Que es Nexo

Nexo toma un assessment de Atlas y lo transforma en una cola de conocimiento candidato. No edita el assessment, no aprueba candidatos automaticamente y no publica en Fabric, Databricks ni otra plataforma.

Su funcion es separar claramente tres cosas:

1. lo que Atlas encontro;
2. lo que una persona decide aceptar o rechazar;
3. la release local inmutable que puede ser consumida por el futuro Runtime.

## Primer corte implementado

Un draft se crea desde un `run_id` de Atlas y queda bajo:

```text
data/registry/<project>/
  drafts/<draft-id>/
    draft_manifest.json
    input/
    working/
      candidates.json
      model_elements.json
    review/
      review_decisions.json
      model_element_decisions.json
    output/
  releases/<release-id>/
    ontology-release/
      release_manifest.json
      canonical_ontology.json
      review_decisions.json
      evidence_index.json
      source_bindings.json
      agent_context_pack.json
      interoperability_mappings.json
      publication_packages/
```

El draft inicial materializa candidatos desde el inventario funcional de Atlas:

- `concept`: definiciones candidatas;
- `business_rule`: reglas candidatas;
- `kpi`: indicadores candidatos.

Cada candidato conserva confianza, documento, `source_chunk_id`, extracto y estado de evidencia. Los estados permitidos en esta etapa son `pending_review`, `approved` y `rejected`. Cada cambio agrega una decision con revisor, rol, nota y fecha.

## Modelo canónico v0.2

Además de los candidatos extraídos por Atlas, una persona puede agregar al draft elementos explícitos del modelo: `property`, `relationship`, `synonym` y `constraint`. Cada elemento tiene nombre, definición, responsable de negocio opcional y vínculos a uno o dos candidatos del mismo draft.

- una propiedad, sinónimo o restricción debe vincular un candidato;
- una relación debe vincular exactamente dos candidatos;
- todo elemento comienza en `pending_review` y tiene su propio registro de decisiones;
- una release solo incorpora elementos aprobados cuyos vínculos apuntan exclusivamente a candidatos aprobados.

La release v0.2 conserva `entities`/`concepts`, `business_rules`, `kpis`, `properties`, `relationships`, `synonyms`, `constraints` y `ownership`. No infiere estructuras: la persona responsable las declara y aprueba de forma explícita.

Cuando Atlas contiene metadata de Fabric, Nexo también materializa `technical_asset` como candidato trazable. Un elemento `source_binding` aprobado vincula exactamente un concepto o KPI de negocio con un activo técnico, sin dar acceso libre a la fuente. La release conserva esos `data_bindings` y un contrato que limita futuras consultas a operaciones `SELECT` y bindings aprobados.

## Consolidacion asistida

Nexo puede generar sugerencias de duplicados exactos de forma local y de casi duplicados semanticos mediante el proveedor LLM explicitamente configurado. Cada sugerencia identifica un candidato canonico existente, sus posibles duplicados y una justificacion. Las sugerencias:

- no cambian candidatos ni sus decisiones;
- no pueden compartir candidatos entre grupos;
- quedan en `pending_review`, `accepted_as_review_plan` o `rejected`;
- requieren una nueva operacion humana antes de aplicar cualquier fusion real.

La aplicacion controlada de una sugerencia aceptada rechaza solamente sus duplicados que aun estan `pending_review`, con una decision individual auditable que referencia al candidato canonico. No aprueba ese candidato canonico y no emite una release. La interfaz tambien permite aprobar o rechazar explicitamente una seleccion de candidatos en revision masiva, siempre con revisor, rol y nota.

## Regla de release

Una release se emite solamente si:

- no queda ningun candidato `pending_review`;
- no queda ningun elemento del modelo canónico `pending_review`;
- existe al menos un candidato aprobado;
- se identifica la persona responsable de emitirla.

La release no vuelve a inferir relaciones: publica conceptos, reglas y KPIs aprobados, más las estructuras canónicas que hayan sido curadas y aprobadas. Esta es una restricción intencional para no presentar inferencias como conocimiento validado.

El `agent_context_pack.json` resultante contiene exclusivamente elementos aprobados, sus bindings de evidencia y una instruccion de abstencion fuera de esos limites.

## Comparación semántica

Nexo puede comparar el draft activo con una release base, o dos releases entre sí. El comparador identifica elementos agregados, eliminados o modificados por `tipo + nombre normalizado`; destaca cambios de definición, estado, responsable y vínculos. Cada resultado se conserva localmente bajo `data/registry/<project>/comparisons/` y es estrictamente de revisión: no modifica decisiones ni publica nada.

## Situacion de risk1

El primer draft heuristico contiene 148 candidatos: 104 conceptos, 37 reglas y 7 KPIs. Se preserva como historial. El draft vigente generado desde el scanner GPT-5.6 contiene 119 candidatos: 35 conceptos, 51 reglas y 33 KPIs; los 119 tienen `source_chunk_id` y evidencia trazable. Todos estan en `pending_review`; no se registro ninguna decision ficticia ni se emitio una release. GPT-5.6 propuso siete grupos de consolidacion que cubren 15 candidatos sin solapamiento; siguen tambien en `pending_review`.

## Límites actuales

- Las propiedades, relaciones, sinónimos y restricciones son curadas manualmente; aún no hay generación asistida de estas estructuras.
- No existen adapters de publicacion o mapping hacia Fabric/Databricks.
- Una release se guarda en carpetas locales; aún no hay control de acceso, firma ni versionado Git.

## Criterio de done de este corte

Una persona puede revisar cada candidato con su evidencia y obtener una release local reconstruible que separa lo aprobado de lo rechazado. El futuro Runtime podra consumir su `agent_context_pack` sin leer directamente documentos crudos.
