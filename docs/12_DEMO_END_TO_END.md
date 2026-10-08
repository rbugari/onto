# Demo end-to-end

Estado: guion validado del MVP operativo

## Proxima sesion manual

Para repetir el caso distribuido desde cero el **2026-10-07**, seguir la [guia de validacion manual](casos/ventas_distribuidas/README.md#validacion-manual-desde-cero-2026-10-07). Usa los mismos archivos en un proyecto nuevo, conserva el historial del proyecto anterior y define puntos de control, criterios de detencion y una plantilla de registro. No ejecutar los runners automaticos durante ese recorrido.

El ciclo real del 2026-10-06 y sus limites estan documentados en el [plan de cobertura explicativa](16_PLAN_ATLAS_COBERTURA_EXPLICATIVA.md#ciclo-real-del-2026-10-06). Los resultados de Argos y los paquetes de ese ciclo corresponden a la release anterior aprobada, no al draft nuevo pendiente.

## Objetivo

Mostrar que ONTO prepara conocimiento gobernado para IA y que puede convivir con distintos repositorios de datos y repositorios ontologicos. La demo no debe depender exclusivamente del caso SIC/riesgo.

## Demo A: dominio distribuido (Atlas)

Muestra el foco del producto: un dominio comercial repartido en varios sistemas.

```powershell
python scripts/run_distributed_demo.py
```

Fuentes en `docs/casos/ventas_distribuidas/input/` (ver el [README del caso](casos/ventas_distribuidas/README.md) para la carga paso a paso y el resultado esperado):

| Sistema | Plataforma | Archivo |
| --- | --- | --- |
| ERP operativo | MariaDB | `erp_mariadb.sql` (DDL) |
| Lakehouse analitico | Databricks | `lakehouse_databricks_columns.csv` (`information_schema.columns`) |
| Modelo Power BI Ventas | Power BI | `powerbi_ventas.bim` |
| CRM comercial | SQL Server | `crm_sqlserver.sql` (DDL), sin responsable |
| Planillas de presupuesto | Planillas | declarado sin metadata |

Incluye tres documentos (glosario, equivalencias entre sistemas, KPIs) y tres casos de uso en `scope.json`.

Resultado esperado: Cliente y Producto presentes en ERP, lakehouse y Power BI con clave comun; Venta en lakehouse y Power BI sin clave comun; gaps por CRM sin responsable, planillas sin metadata y venta sin clave. En la aplicacion, abrir el proyecto "Distribuidora - Ventas distribuidas" y recorrer las pestanas de Atlas.

El script continua hasta Nexo (aprobacion de demo, release) y genera los paquetes para Fabric y Databricks. Ambos recomiendan **ruta B**: el ERP MariaDB y el CRM SQL Server no son alcanzables por la plataforma sin un puente (Mirroring/shortcuts o Lakehouse Federation). En Nexo, pestana **Release y entrega a la plataforma**, se ve la cobertura y se descarga el ZIP.

Relato: "Ninguna plataforma por si sola ve el dominio completo; Atlas si, y muestra exactamente que falta para que un agente pueda cruzar los sistemas".

## Demo B: flujo completo (Atlas, Nexo, Argos)

`commercial_sales_demo`, con datos sinteticos y documentacion parcial.

Fuentes:

- metadata tecnica dummy de ventas;
- documentacion de glosario y KPIs;
- procesos de pedido y facturacion;
- preguntas de negocio frecuentes;
- datos operativos sinteticos para consultas read-only.

La implementacion actual usa el adapter `local_synthetic` para `sales_by_customer`, con binding aprobado a `FactSales` y parametros declarativos.

La demo reproducible se ejecuta con `python scripts/run_commercial_sales_demo.py`. El caso mantiene sus datos sinteticos separados de Risk y Nalub y permite conservar los resultados locales con `--keep`.

## Secuencia

1. Crear un proyecto y completar Alcance: cliente, dominio, data product y casos de uso.
2. Registrar los sistemas e importar su metadata; cargar la documentacion.
3. Ejecutar Atlas.
4. Revisar inventario, score y gaps.
5. Crear un draft Nexo desde el assessment.
6. Revisar candidatos, evidencia, conflictos y bindings.
7. Agregar y aprobar propiedades, relaciones y KPIs necesarios.
8. Emitir una release Nexo local reconstruible.
9. Generar `agent_context_pack` y el paquete importable para Fabric (ruta A: todo implementable).
10. Ejecutar Argos con una pregunta respondible.
11. Ejecutar una consulta operativa parametrizada si existe binding aprobado.
12. Ejecutar una pregunta fuera de alcance y demostrar abstencion.
13. Mostrar que la misma release puede preparar un paquete para un destino ontologico externo sin publicar cambios automaticamente.

La misma secuencia se puede recorrer en `fabric-gold-sic-risk-pilot`, cambiando el adapter de datos y el catalogo de consultas; no cambia el flujo de usuario.

## Criterios de aceptacion

- La demo no requiere modificar `runtime.py` para cambiar el dominio.
- Toda respuesta tiene evidencia o resultado operativo autorizado.
- La pregunta fuera de alcance produce abstencion.
- Los gaps permanecen visibles y no se convierten en definiciones por inferencia.
- La release puede reconstruirse desde sus manifiestos.
- `sales_by_customer` devuelve filas para un cliente conocido y aplica abstencion cuando la pregunta queda fuera del catalogo.
- El paquete externo queda `ready_for_review` y no ejecuta escrituras.

## Relato

Atlas responde “como estas”. Nexo responde “que conocimiento esta validado y como se entrega a tu plataforma”. Argos responde “funciona de verdad” y cubre lo que la plataforma no pueda. La demo debe cerrar mostrando el paquete para Fabric o Databricks: ese es el destino, no Argos.
