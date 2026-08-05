# Guia operativa del ciclo

Fecha: 2026-04-27  
Objetivo: describir el flujo real del proyecto, separar lo que ya esta operativo de lo que sigue pendiente y dejar una referencia unica para ejecucion y mantenimiento.

---

## Alcance

Esta guia ordena el ciclo completo en seis tramos:

1. validacion y publicacion de ManualLoads;
2. precheck tecnico del ciclo;
3. sincronizacion de ManualLoads a Silver;
4. recarga del core Silver compartido;
5. recalculo de Gold;
6. refresh del modelo semantico cuando la ejecucion es end to end.

No sustituye la documentacion detallada de cada script. Su funcion es operativa: explicar el orden, la dependencia y el criterio de uso.

---

## Mapa del proceso

```text
Files/ManualLoads
        |
        v
Validate + Publish a Bronze
        |
        v
Precheck tecnico
        |
        v
Sync ManualLoads -> Silver
        |
        v
Silver core compartido
        |
        v
Gold LLDT + SIC + CULTURA + GOVERNANCA + INFRA
        |
        v
Refresh modelo semantico
```

---

## Tramo 1. Landing

### Que entra aqui

- Excel funcionales subidos manualmente.
- Ficheros dejados en OneLake Files.
- Fuentes auxiliares de CPD o equivalentes que luego se publican en Bronze.

### Que existe hoy

- un gate canonico para archivos manuales del conjunto A;
- un notebook de publicacion de compatibilidad a Bronze para los manual loads;
- un camino operativo separado solo para excepciones tecnicas; CPD_EDR queda fuera del foco operativo frente a CrowdStrike canonico.

### Que falta formalizar

El gate de contrato del conjunto A ya existe para los archivos manuales curados. Lo que sigue separado es el conjunto B de shortcuts y fuentes amplias.

### Referencias

- [IMPORTACION_EXCEL_SHAREPOINT.md](IMPORTACION_EXCEL_SHAREPOINT.md)
- [GUIA_CONJUNTO_A_MANUALLOADS.md](GUIA_CONJUNTO_A_MANUALLOADS.md)
- [../sql/NOTEBOOK_Validate_ManualLoads.py](../sql/NOTEBOOK_Validate_ManualLoads.py)
- [../sql/NOTEBOOK_Publish_ManualLoads_to_Bronze.py](../sql/NOTEBOOK_Publish_ManualLoads_to_Bronze.py)

Nota operativa: `NOTEBOOK_Import_CPD_EDR` no forma parte del camino canonico vigente de SIC si el entorno ya opera con `silver.fact_crowdstrike_cpd` -> `silver.vw_crowdstrike_cpd_current`.

Los notebooks legacy manuales fueron retirados del repo; la lista historica y de borrado en Fabric quedo en [../sql/bak_legacy_manual_loads/README.md](../sql/bak_legacy_manual_loads/README.md).

---

## Tramo 2. Bronze ready

### Que se necesita antes de relanzar Silver

Antes de una recarga completa o de un ciclo critico deberia comprobarse:

- que las tablas Bronze existen;
- que los shortcuts responden;
- que las columnas minimas siguen estando;
- que la fuente no quedo vacia por error;
- que las fuentes snapshot necesarias tienen una fotografia utilizable.

### Estado actual

Desde 2026-05-20 el ciclo ya dispone de un precheck unificado e invocable desde SP, pensado para bloquear la carga si los shortcuts/origenes no estan utilizables.

El gate tecnico del ciclo queda en:

- [GUIA_PRECHECK_CICLO.md](GUIA_PRECHECK_CICLO.md)
- [../sql/33_PRECHECK_CICLO.sql](../sql/33_PRECHECK_CICLO.sql)

### Conclusion operativa

El ciclo ya puede validar shortcuts/origenes antes de mover datos fisicos. Sigue pendiente, si se quiere, evolucionarlo con contratos funcionales mas finos por fuente o reglas de cambio semantico.

---

## Tramo 3. Silver

### Que incluye hoy

- dimensiones maestras;
- catalogos MITRE;
- vulnerabilidades;
- training;
- inventario de workstations;
- identidad de puestos;
- CPD EDR;
- exposicion amenaza CPD;
- perimetro;
- tablas auxiliares de mapeo y soporte.

### Ejecucion actual

No todo Silver corre como un solo procedimiento unico. Hoy conviven:

- un split operativo entre `silver.usp_sync_manual_loads_to_silver` y `silver.usp_load_all_dimensions_core`;
- scripts de full reload;
- cargas separadas por dominio cuando el caso lo requiere.

En inventario hay una regla operativa adicional ya vigente:

- si existe `silver.usp_load_dim_inventario_from_shortcut`, tanto el wrapper `silver.usp_load_all_dimensions` como el full reload lo priorizan para adaptar el shortcut Bronze `FACT_INV_APP_COMPONENTS_CTTI` sin tocar Bronze.

### Referencias principales

- [GUIA_FULL_RELOAD_SILVER.md](GUIA_FULL_RELOAD_SILVER.md)
- [GUIA_SILVER_MINIMO_RIESGO.md](GUIA_SILVER_MINIMO_RIESGO.md)
- [ESQUEMAS_TABLAS_SILVER.md](ESQUEMAS_TABLAS_SILVER.md)
- [LINEAJE_DATOS.md](LINEAJE_DATOS.md)
- [../sql/10_CREATE_SP_MASTER_ORCHESTRATOR.sql](../sql/10_CREATE_SP_MASTER_ORCHESTRATOR.sql)
- [../sql/13_FULL_RELOAD_SILVER.sql](../sql/13_FULL_RELOAD_SILVER.sql)

### Nota importante

El script de full reload debe interpretarse junto con el estado actual del repositorio. No todo el proyecto cabe ya en la fotografia historica del reload inicial; por eso conviene tratar esta guia como la referencia de flujo y el indice SQL como la referencia de inventario.

Ademas, desde 2026-05-20 queda fijado un criterio mas estricto:

- el Silver minimo para riesgo no equivale al Silver historico completo;
- la referencia de alcance para decidir que objetos deben mantenerse por el calculo es [GUIA_SILVER_MINIMO_RIESGO.md](GUIA_SILVER_MINIMO_RIESGO.md);
- `10_CREATE_SP_MASTER_ORCHESTRATOR.sql`, `13_FULL_RELOAD_SILVER.sql` y `33_PRECHECK_CICLO.sql` deben leerse como operativa legacy o generalista, no como definicion exacta del core de riesgo.

---

## Tramo 4. Riesgo de puestos de trabajo

### Estado

Operativo en esquema canonico gold_lldt como unico dominio vigente para LLDT.

El impacto LLDT se resuelve hoy con una mezcla entre valoracion departamental propia y SIC emulado por departamento desde `silver.dim_lldt_cidat`.

### Patrón de ejecucion

1. Silver de identidad y fuentes auxiliares preparado.
2. Carga del modelo gold_lldt.
3. Validacion del modelo gold_lldt.

Nota operativa actual:

- hoy el impacto de LLDT no hereda automaticamente desde SIC, pero si usa `codi_dialeg` como SIC emulado cuando una regla de impacto necesita datos SIC para poder calcularse.

### Referencias

- [ANALISIS_PROBABILIDAD_PUESTOS_FUENTES.md](ANALISIS_PROBABILIDAD_PUESTOS_FUENTES.md)
- [ER_GOLD_SIC_LLDT.md](ER_GOLD_SIC_LLDT.md)
- [../sql/25_CREATE_GOLD_LLDT.sql](../sql/25_CREATE_GOLD_LLDT.sql)
- [../sql/26_VALIDATE_GOLD_LLDT.sql](../sql/26_VALIDATE_GOLD_LLDT.sql)

---

## Tramo 5. Riesgo SIC

### Estado actual

El dominio SIC ya tiene esquema propio gold_sic y el unico modo operativo vigente del procedimiento es sql_v1_silver.

Actualizacion 2026-06-01:

- el flujo Manual Loads -> Bronze -> Silver -> Gold ya quedo revalidado de punta a punta;
- la cobertura del archivo manual de defaults de reglas ya quedo alineada al catalogo activo con 84 reglas sobre 84;
- el full reload de Silver ya volvio a cerrar sin errores operativos ni de validacion;
- la ultima ejecucion validada de LLDT fue `LLDT_20260601_150143_027`;
- la ultima ejecucion validada de SIC fue `SIC_20260601_151405_840`.

### Situacion real a 2026-04-27

- la separacion tecnica de gold_sic ya esta lograda;
- el modo sql_v1_silver ya ejecuto en SUCCESS en DW;
- los esquemas legacy gold y gold_pt ya fueron retirados del DW;
- el bridge host -> app -> SIC ya queda publicado en `silver.inv_sic_host_current`; el pendiente real es completar cobertura, no crear el bridge;
- usuarios SIC y GICAR ya entran en las derivadas Silver (`num_usuarios_max_silver`, `has_gicar`), aunque GICAR llega vacio en la foto actual del origen;
- ya existe ejecucion unica LLDT + SIC + CULTURA + GOVERNANCA + INFRA mediante `audit.usp_run_gold_risk_models`;
- ya existe ejecucion unica precheck -> ManualLoads -> Silver core -> LLDT + SIC + CULTURA + GOVERNANCA + INFRA mediante `audit.usp_run_risk_cycle`;
- la matriz final de riesgo ya se gestiona como fuente manual canonica `shared_risk_final_matrix.xlsx`, publicada a Bronze y consumida por los 5 dominios via `silver.ref_risk_final_matrix`;
- el scope propio de INFRA ya se publica en `silver.dim_infra_cidat` desde `raw_infra_cidat_catalog` y alimenta `gold_infra` sin contaminar `silver.dim_sic_cidat`;
- la auditoria de ejecucion quedo saneada para el ciclo operativo actual;
- el loader shortcut-compatible de inventario ya quedo integrado en el flujo estandar de Silver;
- `I_BUSINESS_CRITICALITY_LEVEL` del shortcut Bronze ya se carga en `silver.dim_inventario.nivell_criticitat_de_negoci`;
- las reglas de impacto 103, 105 y 203 ya distinguen dato real frente a dato faltante: `REAL/OK` si hay criticidad y `DEFAULT/SIN_DATO` si no;
- el ciclo completo historico LLDT + SIC ya se reejecuto en SUCCESS el 2026-05-20 con `audit.usp_run_gold_risk_models @modo_carga_sic = 'sql_v1_silver'`, `run_id = 'GOLD_RISK_20260520_133425_247'`, 99 filas LLDT y 3009 filas SIC;
- desde 2026-06-02 el mismo orquestador Gold ya integra tambien CULTURA y GOVERNANCA, validadas en forma individual antes de su entrada al ciclo unico;
- el refresh `silver.usp_refresh_inv_risk_derived` y la carga `gold_sic.usp_load_modelo_riesgo_sic` volvieron a ejecutarse en SUCCESS el 2026-05-20 ya sobre el flujo Silver -> Gold corregido en Fabric;
- las reglas 104 y 202 ya consumen `silver.inv_sic_atributos_current.is_t11` como criterio operativo T11/publico;
- las reglas 4002-4006 ya consumen `silver.fact_gobernanza_departamento`, cargada desde `XLS_Gobernanza`, con evaluacion directa por departamento en si/no. La 4001 ya consume `silver.fact_certificacion_sic`, cargada desde `CAU_DIALOG_CODE_CERTIFICATIONS`; en la validacion 2026-05-21 siguio en `DEFAULT` porque no hubo SIC certificados materializados en `silver.dim_sic_cidat`.
- desde 2026-06-10 CULTURA y GOVERNANCA quedan cerrados con una unica valoracion por riesgo y departamento; ambos dominios publican `codigo_departamento_ref` como clave canonica de consolidacion y conservan `sic` solo como atributo auxiliar;
- en esos dos dominios la consolidada final `fact_riesgo` debe cruzar probabilidad e impacto por `codigo_departamento_ref` e `id_risc`; no debe añadirse un match extra por bloque entre ambas facts;
- la operacion vigente asume recarga completa de tablas Gold en cada ejecucion de CULTURA y GOVERNANCA para evitar arrastre de informacion previa.

### Orden recomendado de ejecucion hoy

1. Desplegar [../sql/33_PRECHECK_CICLO.sql](../sql/33_PRECHECK_CICLO.sql), [../sql/10_CREATE_SP_MASTER_ORCHESTRATOR.sql](../sql/10_CREATE_SP_MASTER_ORCHESTRATOR.sql), [../sql/34_CREATE_SP_GOLD_RISK_ORCHESTRATOR.sql](../sql/34_CREATE_SP_GOLD_RISK_ORCHESTRATOR.sql), [../sql/53_CREATE_SP_RISK_CYCLE_ORCHESTRATOR.sql](../sql/53_CREATE_SP_RISK_CYCLE_ORCHESTRATOR.sql), [../sql/57_CREATE_REF_RISK_FINAL_MATRIX.sql](../sql/57_CREATE_REF_RISK_FINAL_MATRIX.sql), [../sql/64_CREATE_INFRA_CIDAT_BRONZE.sql](../sql/64_CREATE_INFRA_CIDAT_BRONZE.sql) y [../sql/65_CREATE_GOLD_INFRA.sql](../sql/65_CREATE_GOLD_INFRA.sql) si el entorno aun no los tiene actualizados.
2. Lanzar la ejecucion unica con `EXEC audit.usp_run_risk_cycle @modo_carga_sic = 'sql_v1_silver';` o, si se esta armando el pipeline end to end, ejecutar por separado `audit.usp_precheck_risk_cycle`, `silver.usp_sync_manual_loads_to_silver`, `silver.usp_load_all_dimensions_core` y `audit.usp_run_gold_risk_models`.
3. Si el ciclo bloquea en precheck, revisar la salida de `audit.usp_precheck_risk_cycle` y coordinar con admins antes de reintentar.
4. Usar [../sql/26_VALIDATE_GOLD_LLDT.sql](../sql/26_VALIDATE_GOLD_LLDT.sql), [../sql/32_VALIDATE_GOLD_SIC_NATIVE.sql](../sql/32_VALIDATE_GOLD_SIC_NATIVE.sql), [../sql/63_VALIDATE_GOLD_GOVERNANCA.sql](../sql/63_VALIDATE_GOLD_GOVERNANCA.sql) y el validador equivalente de CULTURA si hace falta validacion detallada por dominio.

### Referencias

- [gold_sic/CONTRATO_BI_GOLD_SIC_V2.md](gold_sic/CONTRATO_BI_GOLD_SIC_V2.md)
- [gold_sic/PLAN_MIGRACION_GOLD_SIC.md](gold_sic/PLAN_MIGRACION_GOLD_SIC.md)
- [CIERRE_OPERATIVO_RIESGO_01JUN2026.md](CIERRE_OPERATIVO_RIESGO_01JUN2026.md)
- [ACTUALIZACION_GOLD_RIESGO_23APR2026.md](ACTUALIZACION_GOLD_RIESGO_23APR2026.md)
- [GUIA_OPERACION_MANUAL_CICLO_RIESGO.md](GUIA_OPERACION_MANUAL_CICLO_RIESGO.md)
- [../sql/33_PRECHECK_CICLO.sql](../sql/33_PRECHECK_CICLO.sql)
- [../sql/31_UPDATE_GOLD_SIC_NATIVE.sql](../sql/31_UPDATE_GOLD_SIC_NATIVE.sql)
- [../sql/32_VALIDATE_GOLD_SIC_NATIVE.sql](../sql/32_VALIDATE_GOLD_SIC_NATIVE.sql)
- [../sql/34_CREATE_SP_GOLD_RISK_ORCHESTRATOR.sql](../sql/34_CREATE_SP_GOLD_RISK_ORCHESTRATOR.sql)
- [../sql/53_CREATE_SP_RISK_CYCLE_ORCHESTRATOR.sql](../sql/53_CREATE_SP_RISK_CYCLE_ORCHESTRATOR.sql)

---

## Orden recomendado de lectura

### Para operacion del ciclo

1. [INDICE_DOCUMENTACION.md](INDICE_DOCUMENTACION.md)
2. [GUIA_PRECHECK_CICLO.md](GUIA_PRECHECK_CICLO.md)
3. [GUIA_FULL_RELOAD_SILVER.md](GUIA_FULL_RELOAD_SILVER.md)
4. [ANALISIS_PROBABILIDAD_PUESTOS_FUENTES.md](ANALISIS_PROBABILIDAD_PUESTOS_FUENTES.md)
5. [gold_sic/CONTRATO_BI_GOLD_SIC_V2.md](gold_sic/CONTRATO_BI_GOLD_SIC_V2.md)

### Para tocar SQL

1. [FABRIC_DW_REGLAS_Y_PATRONES.md](FABRIC_DW_REGLAS_Y_PATRONES.md)
2. [ESQUEMAS_TABLAS_SILVER.md](ESQUEMAS_TABLAS_SILVER.md)
3. [../sql/INDICE_SCRIPTS_SQL.md](../sql/INDICE_SCRIPTS_SQL.md)

---

## Gaps pendientes priorizados

1. Gate de validacion landing para Excel manuales.
2. Consolidacion del flujo Silver completo en una operativa mas unica y menos dispersa.
3. Cierre funcional con cliente de reglas y cruces pendientes del modo sql_v1_silver en gold_sic.
4. Evolucion futura del precheck para incluir contratos funcionales mas finos por fuente.

---

## Documentos historicos o de contexto

Siguen siendo utiles, pero no deben ser el primer punto de entrada:

- [estructura.md](estructura.md)
- [Documentacion_Base_de_Datos_Seguridad.md](Documentacion_Base_de_Datos_Seguridad.md)
- [REORGANIZACION_12FEB2026.md](REORGANIZACION_12FEB2026.md)