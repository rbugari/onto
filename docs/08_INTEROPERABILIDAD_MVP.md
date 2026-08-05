# Interoperabilidad MVP

Estado: primer corte implementado y con lectura de metadata Fabric validada  
Alcance: lectura de catálogo y preparación local; sin publicación externa

## Propósito

ONTO conserva una ontología canónica propia. Fabric y Databricks son destinos opcionales: este corte prepara cómo podría representarse una release aprobada, sin reemplazar ni duplicar la ontología de ONTO.

## Paquete generado

Una release puede preparar un paquete para `fabric` o `databricks` bajo:

```text
data/interoperability/<project>/<release>/<target>/<package-id>/
  publication_manifest.json
  mapping.json
  deployment_manifest.json
```

El mapping cubre entidades, reglas, KPIs, propiedades, relaciones, sinónimos y restricciones. Cada entrada conserva nombre, definición, responsable y vínculos de origen cuando existen.

## Conector Fabric de solo lectura

Atlas puede reutilizar la configuración externa de Fabric ya autorizada para ONTO. La autenticación es delegada mediante Entra; ONTO no copia secretos. El conector valida identidad y base de datos, y puede consultar únicamente `INFORMATION_SCHEMA.TABLES` y `INFORMATION_SCHEMA.COLUMNS` con límites de inventario.

El resultado se guarda bajo `data/fabric/<project>/discoveries/` y puede incorporarse al proyecto como tablas y columnas técnicas. El archivo de metadata queda retenido con hash SHA-256, por lo que el assessment Atlas lo usa como evidencia técnica reproducible. La validación inicial contra el Warehouse configurado confirmó acceso de solo lectura y recuperación limitada de catálogo.

Al crear un draft Nexo desde ese assessment, los objetos Fabric se convierten en candidatos `technical_asset`. Los `source_binding` aprobados conectan esos activos con conceptos o KPIs de negocio y alimentan el context pack de Argos con una frontera de consulta explícita.

## Límites de seguridad

- El paquete tiene estado `ready_for_review`; no se publica automáticamente.
- No pide ni guarda credenciales.
- El inventario Fabric no consulta filas de negocio; solo metadata de `INFORMATION_SCHEMA`.
- No contiene datos de negocio ni ejecuta escrituras contra una plataforma externa.
- El rollback lógico consiste en descartar el paquete, porque todavía no ocurrió ningún cambio externo.

## Próximo corte

Cuando exista un piloto y se elija destino, el adapter concreto deberá declarar autenticación, workspace o catálogo, capacidades soportadas, bindings aprobados, deployment manifest, auditoría y rollback de la publicación real.
