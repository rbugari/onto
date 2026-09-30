# Interoperabilidad MVP

Estado: MVP operativo implementado; lectura de metadata Fabric, adapters read-only y mappings locales validados
Alcance: dos planos de interoperabilidad; sin publicación externa

## Principio

ONTO trabaja con un formato canonico intermedio para relevar y validar el conocimiento, y lo entrega al repositorio ontologico que el cliente ya utilice (destino preferido). Solo lo conserva como sistema de registro cuando la plataforma no puede implementarlo (plan B). Fabric y Databricks no son una sola integracion: pueden ser fuentes de datos, modelos semanticos, fuentes de una ontologia existente o destinos de publicacion.

## Plano de datos

En este plano, Fabric es un repositorio estructurado mas, igual que Databricks, Snowflake, SQL Server o MySQL.

Atlas puede:

- registrar varios sistemas por dominio, cada uno con plataforma y responsable;
- descubrir tablas y columnas de Fabric mediante catalogo, de solo lectura;
- importar metadata exportada de Databricks, SQL Server, PostgreSQL, Snowflake, Oracle, MariaDB o planillas mediante DDL (`.sql`) o CSV de `information_schema.columns`;
- importar `model.bim`, TMDL, paquetes PBIP ZIP y payloads JSON semanticos compatibles;
- conservar hashes y metadata como evidencia reproducible;
- detectar entidades compartidas entre sistemas y sus claves comunes;
- registrar activos tecnicos para su posterior vinculacion.

Argos puede consultar datos operativos solo mediante bindings aprobados y operaciones nombradas, parametrizadas y read-only. Fabric mantiene las consultas del piloto SIC; MariaDB implementa el catalogo live del caso Nalub; ninguno es un catalogo universal.

## Plano ontologico

Nexo puede preparar una release para ser:

- conservada como ontologia canonica en ONTO;
- mapeada hacia Fabric IQ Ontology;
- mapeada hacia capacidades ontologicas de Databricks;
- exportada a Purview, Collibra, Neo4j, RDF/OWL u otro formato futuro.

El mapping ontologico no publica automaticamente. El repositorio de datos, el repositorio ontologico, la release, la identidad autorizada y el estado de sincronizacion deben declararse por separado.

## Paquete generado

Una release puede preparar un paquete local bajo:

```text
data/interoperability/<project>/<release>/<target>/<package-id>/
  publication_manifest.json
  mapping.json
  deployment_manifest.json
  coverage.json
  export/            # archivos importables por la plataforma destino
```

El mapping cubre entidades, reglas, KPIs, propiedades, relaciones, sinonimos y restricciones. Cada entrada conserva nombre, definicion, responsable y vinculos de origen cuando existen.

Para Fabric y Databricks, `export/` contiene los archivos que la plataforma importa: item Ontology y Data Agent de Fabric IQ; Pages, metric views, SQL de Unity Catalog y request de Genie Agents en Databricks. Tambien incluye un reporte de cobertura por elemento y la ruta recomendada (A o B). Detalle, formatos, pasos de importacion y plan de conectores: [Integracion con Fabric y Databricks](15_INTEGRACION_FABRIC_DATABRICKS.md).

## Conector Fabric de solo lectura

Atlas puede reutilizar la configuracion externa de Fabric ya autorizada para ONTO. La autenticacion es delegada mediante Entra; ONTO no copia secretos. El descubrimiento de metadata consulta `INFORMATION_SCHEMA.TABLES` y `INFORMATION_SCHEMA.COLUMNS` con limites de inventario.

Las consultas de Argos sobre filas de negocio son otro contrato: se ejecutan solo desde operaciones allowlisted, con bindings aprobados y parametros validados. No deben confundirse con el descubrimiento de metadata de Atlas.

## Límites de seguridad

- El paquete ontologico tiene estado `ready_for_review`; no se publica automaticamente.
- No pide ni guarda credenciales.
- Atlas no consulta filas de negocio durante el inventario Fabric.
- Argos puede consultar filas solo por operaciones read-only declaradas y aprobadas.
- No se ejecutan escrituras externas en este MVP.
- El rollback logico consiste en descartar el paquete, porque todavia no ocurrio ningun cambio externo.

## Evolucion posterior al MVP

1. Separar en contratos de adapter la lectura de datos, la importacion de ontologias y la publicacion ontologica.
2. Descubrimiento remoto de metadata en Databricks (Unity Catalog) con identidad delegada y solo lectura; hoy se carga por archivo exportado.
3. Consolidar `template_id`, limites y formateo desde adapters de datos configurables; el primer adapter local sintetico ya esta validado.
4. Conectores de publicacion para Fabric IQ y Databricks (release 2 del plan en [15_INTEGRACION_FABRIC_DATABRICKS.md](15_INTEGRACION_FABRIC_DATABRICKS.md)), con autenticacion, auditoria y rollback.
5. Endurecer el adapter MariaDB de Nalub mediante un `connection_profile` aislado por proyecto, con credenciales read-only rotadas y pruebas de permisos, limites, latencia y abstencion.
