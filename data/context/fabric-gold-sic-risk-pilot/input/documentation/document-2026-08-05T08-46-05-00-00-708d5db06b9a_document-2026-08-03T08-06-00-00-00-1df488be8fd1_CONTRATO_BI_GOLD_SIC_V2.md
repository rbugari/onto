# Contrato BI v2 - Gold Riesgo SIC

## Objetivo

Definir una interfaz estable para el dominio SIC en un esquema separado llamado gold_sic.

Actualizacion 2026-05-07: el calculo `sql_v1_silver` ya es el unico modo operativo vigente, el ciclo completo LLDT + SIC se reejecuto en SUCCESS y los esquemas legacy `gold` y `gold_pt` ya fueron retirados del DW.

En la fase actual del proyecto, el objetivo funcional prioritario de este dominio es dejar implantado y bien explicado el analisis de riesgo para las SIC del Departament d'Economia.

## Decision de arquitectura

- El esquema nuevo es gold_sic.
- El SP del dominio SIC sigue el mismo patron operacional ya usado en LLDT: un procedimiento unico de carga y una validacion separada.

Esto no implica que el dominio SIC ya quede cerrado para todos los departamentos. El alcance funcional que debe considerarse objetivo de esta primera fase es el conjunto de SICs del Departament d'Economia.

## Objetos expuestos

1. gold_sic.fact_riesgo
2. gold_sic.fact_impacto_sig
3. gold_sic.fact_probabilidad_sig
4. gold_sic.fact_impacto_bloque
5. gold_sic.fact_probabilidad_bloque
6. gold_sic.fact_impacto
7. gold_sic.fact_probabilidad
8. gold_sic.dim_sig
9. gold_sic.dim_regla
10. gold_sic.dim_supuesto_modelo
11. gold_sic.vw_riesgo_resumen
12. gold_sic.vw_impacto_matriz_reglas_por_sig
13. gold_sic.vw_probabilidad_matriz_reglas_por_sig

## Modo de despliegue actual

El dominio gold_sic opera con un unico modo vigente dentro del procedimiento gold_sic.usp_load_modelo_riesgo_sic.

### sql_v1_silver

Es el unico modo vigente del dominio SIC.

Significa que:

- el calculo se apoya en Silver cuando la fuente ya existe y la regla esta cerrada;
- el contrato externo de gold_sic no cambia.

Este modo convierte a gold_sic en la capa objetivo y unica vigente del dominio SIC. Lo que queda fuera del dato ideal ya forma parte del modelo hoy aceptado, no de una migracion abierta.

Desde 2026-04-27 el camino operativo de inventario queda estabilizado por `silver.usp_load_dim_inventario_from_shortcut` cuando existe. Ese loader adapta el shortcut Bronze `FACT_INV_APP_COMPONENTS_CTTI` y expone `I_BUSINESS_CRITICALITY_LEVEL` como `silver.dim_inventario.nivell_criticitat_de_negoci`.

## Estado de evolucion

La evolucion a calculo nativo desde silver ya comenzo. Ya no es solo una fase futura teorica.

El cambio sigue siendo interno al SP. No cambia la forma de consumo de gold_sic.

En este momento la lectura correcta es esta:

- sql_v1_silver ya es el modo operativo validado del dominio;
- gold_sic es la unica salida vigente del dominio SIC en DW;
- el siguiente hito es cerrar reglas, coberturas y cruces pendientes con cliente dentro del alcance inicial de SICs del Departament d'Economia.
- gold_sic.dim_sig publica tambien el CPD operativo resuelto para navegacion BI mediante `cpd_codigo` y `cpd_lot_id`.

## Reglas y decisiones funcionales ya fijadas

Nota de lectura sobre el calculo de probabilidad:

- el dato original de una regla no se agrega directamente con el resto; primero se traduce a un `nivel` comun del modelo;
- la escala comun de probabilidad es `1 = BAIX`, `2 = MIG`, `3 = ALT`, `4 = MOLT ALT`;
- `gold_sic.fact_probabilidad_bloque` y `gold_sic.fact_probabilidad_sig` agregan esos niveles, no los porcentajes o recuentos originales;
- cuando existe `peso_regla` configurado, el agregado se calcula como promedio ponderado de niveles; si los pesos activos son uniformes, el resultado equivale a promedio simple.

- Probabilidad SIC: FACT_PER_APLICATION_PERIMETER se trata como snapshot y se usa siempre la foto mas reciente.
- Probabilidad SIC: FACT_VUL_VULNERABILITIES se trata como fuente transaccional y se cuentan solo vulnerabilidades Critical no resueltas.
- Probabilidad SIC: las reglas 1005, 2006, 2009, 3005 y 3009 ya tienen fuente en `silver.fact_exposicion_amenaza_cpd` y el cableado SIC -> CPD queda resuelto en `silver.inv_sic_atributos_current.fk_lot_cpd`, priorizando `REL_INV_APPS_LOTS` + `DIM_INV_LOTS` filtrado a `D_TYPE = 'CPD'`. Silver publica un unico CPD por SIC: el CPD que mas se repite y, en empate, el menor `fk_lot`; `FK_LOT_CPD` queda como respaldo cuando no hay relacion app-lote.
- Navegacion SIC: ese mismo cruce operativo de CPD deja de quedar solo como dato de calculo y pasa a exponerse en `gold_sic.dim_sig` para segmentacion analitica en BI.
- Probabilidad SIC: la regla 2007 ya queda cableada a `silver.inv_sic_atributos_current.has_gicar`; si el origen viene vacio, la salida queda `DEFAULT` por ausencia de dato, no por ausencia de implementacion.
- Probabilidad SIC: las reglas 4002-4006 ya consumen `silver.fact_gobernanza_departamento`, proyeccion Silver de `XLS_Gobernanza`, con lectura directa si/no por departamento. La 4001 consume `silver.fact_certificacion_sic`, proyeccion Silver de `CAU_DIALOG_CODE_CERTIFICATIONS` interpretando `FK_ID_DIALOG_CODE` como lista operativa de SICs; si el campo trae varios IDs separados por `;`, se proyectan todos.
- Impacto SIC: la regla 102 debe cruzar criticidad/SIC con usuarios de consulta en inventario.
- Impacto SIC: las reglas 103, 105 y 203 ya usan `criticidad_negocio` cargada desde inventario; si falta el dato la salida debe quedar `DEFAULT/SIN_DATO`, y si existe debe quedar `REAL/OK`.
- Impacto SIC: la regla 402 debe heredar el mismo criterio que la 102 si reutiliza esa logica.
- Impacto SIC: la regla 104 distingue internet frente a intranet; si es T11 se considera internet y el resto intranet.
- Impacto SIC: la regla 202 sigue el mismo criterio funcional de exposicion; si es T11 se considera publico y si no, interno.
- Impacto SIC: la regla 203 se alinea funcionalmente con la 105.
- Impacto SIC: la regla 205 deja de formar parte del modelo objetivo y ya fue retirada del motor nativo `sql_v1_silver`.
- Impacto SIC: la regla 401 debe calcular la clasificacion del sistema como el maximo de las dimensiones C, I, D, A y T del SIC.

## Backlog residual no bloqueante

- Mantener trazabilidad del cruce SIC -> CPD ya implantado en Silver para la familia 1005, 2006, 2009, 3005 y 3009, diferenciando fuente directa frente a imputacion operativa.
- Completar cobertura del bridge `host -> app -> SIC` para reducir `DEFAULT` en las reglas EDR.
- Mantener la documentacion alineada con la definicion vigente de T11/publico, CPD y bloque 4000 ya cerrada con cliente.

No se preve incorporar nuevas fuentes para este dominio en el corto plazo. La lectura correcta es mantener el modelo actual y solo reabrirlo si cliente cambia una definicion funcional.

## Scripts tecnicos

- Evolucion nativa / hibrida del SP: ../../sql/31_UPDATE_GOLD_SIC_NATIVE.sql
- Validacion del modo sql_v1_silver: ../../sql/32_VALIDATE_GOLD_SIC_NATIVE.sql
- Ejecucion unica del ciclo: ../../sql/34_CREATE_SP_GOLD_RISK_ORCHESTRATOR.sql

## Estado operativo comprobado

- `gold_sic.usp_load_modelo_riesgo_sic @modo_carga = 'sql_v1_silver'` ya ejecuto en SUCCESS el 2026-04-23.
- `audit.usp_run_gold_risk_models @modo_carga_sic = 'sql_v1_silver'` ya se reejecuto en SUCCESS el 2026-05-20 con LLDT y SIC en el mismo ciclo, `run_id = 'GOLD_RISK_20260520_133425_247'`, 99 filas LLDT y 3009 filas SIC.
- `gold_sic.usp_load_modelo_riesgo_sic @modo_carga = 'sql_v1_silver'` ya se revalido en SUCCESS el 2026-05-20 con `run_id = 'SIC_20260520_070208_857'`, 59 SIC en `dim_sig`, 2065 filas en `fact_probabilidad`, 708 en `fact_impacto` y 236 en `fact_riesgo`.
- El dominio SIC ya puede recalcularse en modo nativo desde Silver.
- La vista `silver.vw_cpd_edr_sic_current` fue reconstruida para soportar este modo.
- La criticidad de negocio del inventario ya entra de forma operativa en el calculo SIC a traves de `silver.dim_inventario`.
- Mientras no exista mapeo host -> app cargado, las reglas SIC basadas en EDR degradan a un fallback neutral `DEFAULT` de nivel 2 y no al mejor caso.

## Criterio operativo vigente

El corte tecnico del legacy ya esta completado en DW. La referencia correcta hoy es `gold_sic` en `sql_v1_silver`, con las reglas y supuestos documentados como definicion vigente del modelo.