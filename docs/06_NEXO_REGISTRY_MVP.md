# Nexo - Registry & Validation MVP

Estado: MVP operativo implementado (modelo canónico v0.2)
Producto: 2 de 3 de ONTO

## Que es Nexo

Nexo toma un assessment de Atlas y lo transforma en una cola de conocimiento candidato. No edita el assessment, no aprueba candidatos automaticamente y no publica en Fabric, Databricks ni otra plataforma.

Su funcion es separar claramente tres cosas:

1. lo que Atlas encontro;
2. lo que una persona decide aceptar o rechazar;
3. la release local reconstruible que consume Argos mediante su `agent_context_pack`.

El piloto guiado incorpora ademas una decision automatica determinista para el
flujo operativo: aprueba candidatos con evidencia disponible, origen identificado
y confianza suficiente, y rechaza explicitamente el resto con una decision trazable.
Esta automatizacion no cambia el contrato de Nexo: la regla es del runner de demo
y toda decision conserva revisor, rol, nota y fecha. No representa una aprobacion
autonoma para un uso de negocio ni reemplaza el workflow de revision humana.

## Alcance implementado

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

El draft inicial materializa candidatos desde el diagnostico Atlas:

- `concept`: definiciones candidatas;
- `business_rule`: reglas candidatas;
- `kpi`: indicadores candidatos;
- `technical_asset`: tablas, columnas y medidas inventariadas en cualquier sistema (Fabric, MariaDB, Databricks, Power BI u otro), con el `source_id` del sistema de origen.

Cada candidato conserva confianza, documento, `source_chunk_id`, extracto y estado de evidencia. Los estados permitidos en esta etapa son `pending_review`, `approved` y `rejected`. Cada cambio agrega una decision con revisor, rol, nota y fecha.

## Modelo canónico v0.2

Además de los candidatos extraídos por Atlas, una persona puede agregar al draft elementos explícitos del modelo: `property`, `relationship`, `synonym` y `constraint`. Cada elemento tiene nombre, definición, responsable de negocio opcional y vínculos a uno o dos candidatos del mismo draft.

- una propiedad, sinónimo o restricción debe vincular un candidato;
- una relación debe vincular exactamente dos candidatos;
- todo elemento comienza en `pending_review` y tiene su propio registro de decisiones;
- una release solo incorpora elementos aprobados cuyos vínculos apuntan exclusivamente a candidatos aprobados.

La release v0.2 conserva `entities`/`concepts`, `business_rules`, `kpis`, `properties`, `relationships`, `synonyms`, `constraints` y `ownership`. No infiere estructuras: la persona responsable las declara y aprueba de forma explícita.

Los activos técnicos (`technical_asset`) conservan el sistema de origen como evidencia. Un elemento `source_binding` aprobado vincula exactamente un concepto o KPI de negocio con un activo técnico, sin dar acceso libre a la fuente. La release conserva esos `data_bindings` y un contrato que limita futuras consultas a operaciones `SELECT` y bindings aprobados.

Una release puede incluir un `query_catalog` explícito. Cada entrada declara `query_name`, adapter, `template_id`, binding requerido, parámetros permitidos, límites, routing y, cuando corresponde, `connection_profile`. En Risk, Ventas y Nalub estos catálogos alimentan adapters read-only y no permiten que Argos genere SQL arbitrario.

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

## Pantalla de Nexo

La pantalla (`onto_ui/nexo.py`) muestra metricas del draft, el avance de decisiones y el siguiente paso, y se organiza en cinco pestanas: **Revision de candidatos** (tabla filtrable por estado, tipo y texto; detalle con evidencia y botones Aprobar/Rechazar/Pendiente; decision masiva con confirmacion), **Modelo canonico**, **Consolidacion**, **Comparar** y **Release e interoperabilidad**.

El revisor/a y su rol se indican una vez por sesion en la barra lateral y se registran en cada decision. Sin revisor/a, la aplicacion no registra aprobaciones ni rechazos.

## Situacion del piloto Fabric

El piloto `fabric-gold-sic-risk-pilot` conserva drafts, decisiones, releases y comparaciones locales bajo `data/registry/`. La release `documentation-first` aprobada alimenta la batería de evaluación de Argos descrita en el documento del Runtime. Los artefactos se mantienen como evidencia operativa del piloto y no sustituyen la revisión humana requerida para nuevos drafts o cambios de negocio.

## Límites actuales

- Las propiedades, relaciones, sinónimos y restricciones son curadas manualmente; aún no hay generación asistida de estas estructuras.
- Las equivalencias entre sistemas que detecta Atlas (por ejemplo, Cliente del ERP y del lakehouse) todavia no se registran como decision de Nexo; hoy se expresan con relaciones o sinonimos curados manualmente.
- Existen paquetes de mapping locales para Fabric y Databricks, pero no adapters de publicación externa.
- Una release se guarda en carpetas locales y es reconstruible desde sus manifests; aún no hay control de acceso, firma ni gobierno de inmutabilidad empresarial.

## Autoridad documental implementada

El MVP ya permite seleccionar la autoridad `technical`, `documentation` o `hybrid` al crear un draft. En modo `documentation-first`, la documentación define el universo funcional y los activos técnicos se conservan como referencias revisables para poder validarlos, pero no se incorporan automáticamente como conceptos de negocio; el modo elegido queda registrado en los manifiestos. ONTO ejecuta además un matching determinista conservador por identificador técnico completo y conserva, por candidato, estado, confianza, motivo, documento/chunk y activos técnicos vinculados. Los matches únicos pueden convertirse en propuestas `source_binding` pendientes; los matches ambiguos o ausentes generan gaps para revisión humana. El matching nunca aprueba ni publica un binding por sí mismo.

El valor por defecto al crear un draft es `technical`; el piloto Fabric y la demo comercial usan `documentation`:

```text
source_authority = technical | documentation | hybrid
```

En `documentation-first`:

- la documentación define el alcance y el modelo funcional que se desea utilizar;
- los conceptos, reglas y KPIs documentados son la fuente principal de candidatos;
- los sistemas tecnicos se consultan para validar y crear bindings, no para ampliar automáticamente el modelo;
- un concepto documentado sin correspondencia técnica queda visible como gap;
- un objeto técnico no mencionado en la documentación queda fuera de la release, sin tratarlo como error;
- la release solo incorpora elementos documentados y bindings técnicos validados.

El matching debe ser explícito y trazable por candidato: documento/chunk de origen,
activo técnico vinculado, estado del vínculo, confianza y motivo de aceptación o
rechazo. El modo `hybrid` queda reservado para una decisión posterior sobre cómo
resolver conflictos entre documentación y metadata técnica.

## Criterio de done de este corte

Una persona puede revisar cada candidato con su evidencia y obtener una release local reconstruible que separa lo aprobado de lo rechazado. Argos consume su `agent_context_pack` sin leer directamente documentos crudos.
