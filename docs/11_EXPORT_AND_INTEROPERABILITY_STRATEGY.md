# Estrategia de exportacion e interoperabilidad

Estado: estrategia vigente del MVP operativo y direccion de evolucion

## Principio

ONTO conserva una ontologia canonica propia para mantener portabilidad, evidencia y control de ciclo de vida. Puede usar plataformas externas como fuente de datos, fuente de evidencia, repositorio ontologico o destino de publicacion.

## Operaciones separadas

| Operacion | Producto | Resultado |
| --- | --- | --- |
| Importar metadata o datos autorizados | Atlas | Inventario, evidencia y bindings candidatos |
| Importar ontologia externa | Atlas/Nexo | Evidencia o candidatos para revision |
| Mapear | Nexo | Relacion entre elementos aprobados y objetos externos |
| Preparar publicacion | Nexo | Paquete externo local desde una release aprobada |
| Consultar | Argos | Resultado read-only desde un repositorio de datos autorizado |

## Plano de datos

Los adapters de datos deben declarar plataforma, tipo de activo, alcance de metadata, operaciones de consulta, limites, autenticacion y permisos requeridos.

Ejemplos:

- Fabric Warehouse o Lakehouse;
- Databricks SQL;
- Snowflake;
- SQL Server o MySQL;
- Power BI semantic model mediante `model.bim`, PBIP, TMDL o API autorizada.

## Plano ontologico

Los adapters ontologicos deben declarar formato, fidelidad, capacidades de importacion, mapping y publicacion, sistema de registro, identificadores externos, version y estrategia de rollback.

Destinos posibles:

- ONTO canonical JSON;
- Fabric IQ Ontology;
- capacidades ontologicas de Databricks;
- Purview, Collibra o Alation;
- Neo4j;
- JSON-LD o RDF/OWL;
- glosario Excel o paquete documental.

## Paquete canonico

```text
ontology-release/
  release_manifest.json
  canonical_ontology.json
  review_decisions.json
  evidence_index.json
  source_bindings.json
  interoperability_mappings.json
  agent_context_pack.json
  publication_packages/
```

## Paquete de publicacion

Como minimo debe declarar:

```text
publication_manifest.json
mapping.json
deployment_manifest.json
```

La publicacion real requiere release aprobada, mapping aprobado, identidad autorizada, destino explicitamente seleccionado, auditoria, resultado verificable y rollback operativo. El MVP actual solo genera `publication_manifest.json`, `mapping.json` y `deployment_manifest.json` en paquetes `ready_for_review`; no genera aun `rollback_manifest.json` ni ejecuta publicaciones externas.

## Regla de autoridad

La autoridad de una definicion, regla, KPI o binding debe quedar declarada. Una herramienta externa no se convierte en autoridad por el hecho de ser consultada. ONTO puede gobernar la release, delegar el sistema de registro al cliente o trabajar en modo federado, siempre conservando evidencia y estado de sincronizacion.
