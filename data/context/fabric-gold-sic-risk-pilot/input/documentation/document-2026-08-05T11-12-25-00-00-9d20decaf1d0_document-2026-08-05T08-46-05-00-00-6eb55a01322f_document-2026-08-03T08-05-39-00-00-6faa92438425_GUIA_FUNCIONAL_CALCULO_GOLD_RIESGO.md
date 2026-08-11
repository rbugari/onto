# Guia funcional del calculo Gold de riesgo

Ultima actualizacion: 2026-07-26
Estado: vigente  
Objetivo: explicar a responsables funcionales y duenos del modelo como funciona el calculo de riesgo en Gold para los cinco ejes del modelo, LLDT, SIC, CULTURA, GOVERNANCA e INFRA, sin entrar en detalle de cargas o despliegue tecnico.  
Alcance: calculo funcional vigente, reglas, defaults, constantes y trazabilidad por regla.

> Estado del documento: guia funcional vigente del calculo Gold.
> Alcance: explica el modelo vigente en `gold_lldt`, `gold_sic`, `gold_cultura`, `gold_governanca` y `gold_infra`, incluyendo reglas, valores posibles, defaults, constantes y trazabilidad por regla.
> Actualizacion 2026-06-04: las reglas SIC 1002, 2010, 3002 y 3010 quedan fijadas con la definicion del workbook v3.1: perimetro base desde `silver.fact_perimetro.base_attributes_noncompleted`, filtrando `status = Alta`, tomando solo la foto mas reciente y calculando `% despliegue base = 1 - (base_attributes_noncompleted / 6)`.
> Actualizacion 2026-06-10: CULTURA y GOVERNANCA pasan a publicarse a grano departamento con una unica valoracion por riesgo y departamento. Ambos dominios conservan un SIC canonico como atributo auxiliar, pero la clave de calculo y consolidacion final es `codigo_departamento_ref`.
> Actualizacion 2026-07-16: para lectura regla por regla, la referencia funcional detallada queda en [CATALOGO_FUNCIONAL_REGLAS_RIESGO_VIGENTE.md](CATALOGO_FUNCIONAL_REGLAS_RIESGO_VIGENTE.md). La documentacion vigente ya no debe presentar `PROXY` ni `PENDIENTE` como tipos de resultado Gold; el modelo actual usa `REAL`, `DEFAULT`, `CONSTANTE` y la lectura especial `LLDT_SIC_EMULADO` para impacto LLDT.
> Actualizacion 2026-07-26: las reglas de training `2006`, `2011` y `4001` de CULTURA y GOVERNANCA quedan alineadas con LLDT: `I_PASS` frente a workstations derivados de `DIM_INV_DEVICES`, sin veto adicional por `linked_hosts`.

---

## 1. Que explica esta guia

Esta guia responde cuatro preguntas:

1. que riesgos calcula el modelo;
2. que significa cada regla;
3. como se traduce cada dato a un nivel de riesgo;
4. que pasa cuando falta el dato real.

No explica la carga Bronze -> Silver. El foco esta en el calculo funcional vigente en Gold.

Para explicar una regla concreta ante negocio, usar esta guia junto con [CATALOGO_FUNCIONAL_REGLAS_RIESGO_VIGENTE.md](CATALOGO_FUNCIONAL_REGLAS_RIESGO_VIGENTE.md), que resume para cada regla que usa, como calcula, para que sirve y que default aplica.

---

## 2. Resumen ejecutivo

El modelo actual tiene cinco ejes:

- LLDT: riesgo sobre puestos de trabajo y sus ambitos de uso.
- SIC: riesgo sobre sistemas de informacion criticos y aplicaciones.
- CULTURA: riesgo de cultura sobre el mismo universo funcional de SIC, pero publicado con una unica valoracion por departamento y foco en training.
- GOVERNANCA: riesgo de governanca sobre el mismo universo funcional de SIC, tambien publicado por departamento y con bloque 4000 propio.
- INFRA: riesgo de infraestructura con scope funcional propio publicado en `silver.dim_infra_cidat` y metodo de calculo alineado con SIC.

Cada eje calcula 4 riesgos:

- bloque 100: indisponibilidad de servicios o sistemas;
- bloque 200: compromiso y perdida de informacion;
- bloque 300: compromiso del equipo o plataforma;
- bloque 400: incumplimiento legal y normativo.

Cada riesgo tiene dos frentes:

- probabilidad: que tan expuesto esta ese riesgo;
- impacto: que daño produciria si se materializa.

El riesgo final de cada bloque se calcula igual en los cinco dominios:

- se obtiene un nivel final de probabilidad del bloque;
- se obtiene un nivel final de impacto del bloque;
- el riesgo final no se calcula con promedio ni ponderacion lineal: se cruza probabilidad e impacto en una matriz 4x4 de doble entrada.

Escala comun usada por todo el modelo:

- 1 = BAIX / bajo
- 2 = MIG / medio
- 3 = ALT / alto
- 4 = MOLT ALT / muy alto

---

## 3. Como leer los codigos de regla

La codificacion sigue este patron:

- reglas 101-105, 201-204, 301, 401-402: impacto;
- reglas 1001-1999, 2001-2999, 3001-3999, 4001-4999: probabilidad.

El primer bloque del numero identifica el riesgo:

- 100 / 1000: indisponibilidad
- 200 / 2000: compromiso y perdida de informacion
- 300 / 3000: compromiso del equipo o plataforma
- 400 / 4000: incumplimiento legal y normativo

Ejemplo:

- regla 1003 = probabilidad del bloque 100;
- regla 204 = impacto del bloque 200;
- regla 3007 = probabilidad del bloque 300.

---

## 4. Tipos de valor que usa el modelo

Cada regla queda marcada con un tipo de valor para que el resultado sea auditable y explicable.

### REAL

La regla usa una fuente considerada valida y activa para ese calculo.

### DEFAULT

La regla no tiene dato usable para ese activo o ambito y el modelo aplica un valor por defecto para no romper el calculo.

### CONSTANTE

La regla queda cerrada por decision funcional con un valor fijo, no porque exista una fuente dinamica.

### LLDT_SIC_EMULADO

Es la etiqueta especial vigente del impacto LLDT:

- `LLDT_SIC_EMULADO`: impacto LLDT resuelto con mezcla de datos departamentales y SIC emulado por departamento.
- `silver.dim_lldt_cidat` aporta la valoracion propia del departamento y `codi_dialeg` indica el SIC por defecto que debe emularse cuando una regla de impacto necesita datos SIC.

---

## 5. Glosario funcional de metadatos clave

Este glosario ayuda a leer las reglas sin tener que conocer el detalle SQL.

| Dato / metadata | Que significa funcionalmente |
|---|---|
| `pct_antivirus` | porcentaje de equipos del ambito con antivirus desplegado y operativo |
| `pct_edr` / `pct_edr_current` | porcentaje de equipos con EDR desplegado y operativo |
| `pct_patch_gt_60` | porcentaje de equipos con mas de 60 dias sin actualizar Windows |
| `alert_ticket_count` | numero de tickets/alertas departamentales cerradas usados como senal operativa del problema |
| `pct_mfa_vpn` | porcentaje de usuarios con MFA en VPN |
| `pct_mfa_o365` | porcentaje de usuarios con MFA en O365 |
| `generic_accounts` | numero de cuentas genericas del ambito |
| `pct_training_attendance` | cobertura de formacion, calculada sobre aprobados frente al parque de equipos del ambito y limitada al 100% |
| `pct_tpm` | porcentaje de equipos con TPM |
| `pct_encrypted` | porcentaje de equipos cifrados |
| `pct_os_obsolete` | porcentaje de equipos con sistema operativo obsoleto |
| `security_score` | puntuacion de seguridad/perimetro publicada para la aplicacion o SIC |
| `total_attributes_noncompleted` | cantidad de atributos de perimetro sin completar; si es 0 el perimetro esta mejor resuelto |
| `critical_open_count` | numero de vulnerabilidades criticas abiertas |
| `valor_exposicion` | exposicion CPD ya traducida a BAIX, MIG, ALT o MOLT ALT |
| `is_t11` | indicador de exposicion a publico / internet |
| `has_gicar` | indica integracion con GICAR para autenticacion |
| `num_usuarios_max` / `num_usuarios_max_silver` | volumetria de usuarios afectados o soportados |
| `criticidad_negocio` | criticidad del sistema en escala de inventario; en la implementacion actual los valores bajos representan mayor criticidad |
| `key_seguretat` | nivel de clasificacion o seguridad informado para el SIC |
| `cidat_max_nivel` | maximo nivel entre C, I, D, A y T |
| `rto` | tiempo maximo tolerable de indisponibilidad |

---

## 6. Mapa general del calculo

| Dominio | Unidad calculada | Riesgos | Probabilidad | Impacto | Salida final |
|---|---|---|---|---|---|
| LLDT | departamento / ambito de puestos | 4 | detalle por regla y agregado por bloque | agregado por bloque con mezcla LLDT + SIC emulado | `gold_lldt.fact_riesgo` |
| SIC | SIC / aplicacion | 4 | detalle por regla, por bloque y por SIC | detalle por regla, por bloque y por SIC | `gold_sic.fact_riesgo` |
| CULTURA | departamento de referencia con SIC canonico auxiliar | 2 y 4 | detalle por regla y agregado por bloque | detalle por regla y agregado por bloque | `gold_cultura.fact_riesgo` |
| GOVERNANCA | departamento de referencia con SIC canonico auxiliar | 2 y 4 | detalle por regla y agregado por bloque | detalle por regla y agregado por bloque | `gold_governanca.fact_riesgo` |
| INFRA | activo INFRA / aplicacion | 4 | detalle por regla, por bloque y por activo | detalle por regla, por bloque y por activo | `gold_infra.fact_riesgo` |

Regla de combinacion final en los cinco dominios:

- `riesgo_final_num = matriz_4x4(probabilidad_final_num, impacto_final_num)`
- La matriz vigente ya no debe mantenerse hardcodeada en Gold: se publica como fuente manual canonica `shared_risk_final_matrix.xlsx`, se carga en Bronze como `dbo.raw_shared_risk_final_matrix` y se consume desde `silver.ref_risk_final_matrix`.

Matriz vigente de combinacion final:

| Impacto \ Probabilidad | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| 4 | 3 | 4 | 4 | 4 |
| 3 | 2 | 3 | 4 | 4 |
| 2 | 2 | 2 | 3 | 3 |
| 1 | 1 | 1 | 2 | 2 |

No hay ponderaciones distintas por riesgo en la version vigente.

---

## 8.4. Dominios CULTURA y GOVERNANCA

Ambos dominios reutilizan atributos del universo SIC y la misma matriz final 4x4, pero no son una variante cosmetica de SIC. Tienen catalogo, defaults administrados y salida Gold propios.

Actualizacion operativa vigente:

- el scope se materializa con un unico SIC canonico por `codigo_departamento_ref`, derivado desde `silver.dim_lldt_cidat`;
- la salida final queda a grano departamento, no a grano SIC;
- las tablas Gold se recargan en modo truncate-reload en cada ejecucion para evitar arrastre de informacion vieja;
- la consolidada `fact_riesgo` une probabilidad e impacto por `codigo_departamento_ref` e `id_risc`; no debe forzarse un join adicional por bloque entre ambas facts porque en estos ejes las codificaciones de bloque de probabilidad e impacto no coinciden numericamente.
- las reglas de training `2006`, `2011` y `4001` siguen el mismo contrato que LLDT: aprobados `I_PASS` desde `FACT_TRA_TRAININGS_TARGETS` y denominator de equipos desde `DIM_INV_DEVICES`, publicados en Silver como `fact_training.passed` y `fact_inventario_workstations`.
- `linked_hosts` es un atributo auxiliar del scope SIC/departamento y no participa en el calculo ni en la decision `REAL`/`DEFAULT` de esas tres reglas.

### CULTURA

Lectura funcional resumida:

- solo activa riesgos de los bloques 200 y 400;
- la probabilidad se apoya en las reglas `2006`, `2011` y `4001`, ligadas a training departamental y consolidadas directamente por `codigo_departamento_ref`;
- para esas reglas, el porcentaje es `min(100, 100 * aprobados / workstations)`; si hay workstations y no hay aprobados, publica `0% REAL`, y solo usa `DEFAULT` si falta denominator;
- el impacto reutiliza el patron aplicacional para `201`, `204`, `401` y `402`, pero lo publica sobre el departamento de referencia usando el SIC canonico como atributo auxiliar;
- los defaults observados en el workbook son `4` para probabilidad y `2` para impacto.

Salida Gold vigente:

- `gold_cultura.dim_sig_scope`
- `gold_cultura.dim_regla`
- `gold_cultura.dim_supuesto_modelo`
- `gold_cultura.fact_probabilidad`
- `gold_cultura.fact_probabilidad_bloque`
- `gold_cultura.fact_impacto`
- `gold_cultura.fact_impacto_bloque`
- `gold_cultura.fact_riesgo`

### GOVERNANCA

Lectura funcional resumida:

- activa riesgos de los bloques 200 y 400;
- comparte con CULTURA las reglas de training `2006`, `2011` y `4001`;
- esas tres reglas usan exactamente el mismo contrato de fuentes y calculo que CULTURA y LLDT;
- incorpora `4002` desde `silver.fact_certificacion_sic`;
- incorpora `4003` a `4007` desde `silver.fact_gobernanza_departamento` aplicando remapeo explicito `4002-4006 -> 4003-4007` y consolidando el resultado por `codigo_departamento_ref`;
- el impacto reutiliza el mismo patron departamental con SIC canonico auxiliar que CULTURA;
- los defaults observados en workbook son `4` para training, `2` para impacto y `3/2` segun la regla concreta del bloque 4000 de governanza.

Salida Gold vigente:

- `gold_governanca.dim_sig_scope`
- `gold_governanca.dim_regla`
- `gold_governanca.dim_supuesto_modelo`
- `gold_governanca.fact_probabilidad`
- `gold_governanca.fact_probabilidad_bloque`
- `gold_governanca.fact_impacto`
- `gold_governanca.fact_impacto_bloque`
- `gold_governanca.fact_riesgo`

---

## 7. Dominio LLDT

## 7.1. Que calcula LLDT

LLDT calcula riesgo por departamento dentro del scope operativo vigente.

El calculo Gold LLDT tiene dos particularidades importantes:

1. la probabilidad si se materializa regla por regla;
2. el impacto no se publica regla por regla, pero si se construye bloque por bloque combinando reglas LLDT propias con reglas derivadas del SIC emulado por departamento.

Impacto LLDT vigente:

- toma `key_seguretat` y C/I/D/A/T desde `silver.dim_lldt_cidat` para la valoracion propia del departamento;
- usa `codi_dialeg` de esa misma tabla como SIC por defecto a emular;
- resuelve con ese SIC emulado las reglas de impacto que dependen de RTO, criticidad, usuarios o T11/publico;
- agrega el resultado por bloque y lo publica en `gold_lldt.fact_impacto_bloque`.

Eso significa que la semantica de las reglas de impacto sigue existiendo en el catalogo funcional, pero el Gold vigente de LLDT no las explota una a una como hace SIC.

---

## 7.2. Probabilidad LLDT por regla

### Bloque 100. Indisponibilidad

| Regla | Objetivo funcional | Que mira | Como se calcula | Valores / niveles | Tipo y default |
|---|---|---|---|---|---|
| 1001 | Despliegue antivirus | `% equipos con antivirus` en `silver.fact_inventario_workstations` | mide cobertura real de antivirus en el ambito | >= 96% = BAIX; 91-95 = MIG; 86-90 = ALT; < 86 = MOLT ALT | `REAL` si hay dato; `DEFAULT` si falta y se asume 100% |
| 1002 | Despliegue EDR | `% equipos con EDR` en `silver.fact_inventario_workstations` | mide cobertura real de EDR en el ambito | mismo tramo que 1001 | `REAL` si hay dato; `DEFAULT` si falta y se asume 100% |
| 1003 | Parches desactualizados | `% equipos con mas de 60 dias sin actualizar` | usa la metrica operativa real de parchado del ambito | < 30% = BAIX; 30-79 = MIG; 80-89 = ALT; >= 90 = MOLT ALT | `REAL` si hay dato; `DEFAULT` si falta y se asume 0% |
| 1004 | Alertas no resueltas | `tickets_tancat` por departamento en `silver.fact_ticket_alerta_departamento` | cuenta tickets cuyo estado contiene `Tancat` como senal operativa de alertas | 0 = BAIX; 1-5 = ALT; > 5 = MOLT ALT | `REAL` si hay fila; `DEFAULT` si falta y se asume 0 |

### Bloque 200. Compromiso y perdida de informacion

| Regla | Objetivo funcional | Que mira | Como se calcula | Valores / niveles | Tipo y default |
|---|---|---|---|---|---|
| 2001 | Proteccion de credenciales via EDR | `% equipos con EDR` | usa la cobertura EDR operativa del puesto como dato vigente del modelo | >= 96% = BAIX; 91-95 = MIG; 86-90 = ALT; < 86 = MOLT ALT | `REAL` si hay dato; `DEFAULT` si falta y se asume 100% |
| 2002 | MFA VPN administradores | decision funcional | no depende de fuente dinamica; queda fijada a 100% | siempre BAIX | `CONSTANTE` |
| 2003 | MFA VPN usuarios | `% MFA VPN` desde `silver.vw_src_prob_puestos_mfa_vpn` | mide cobertura MFA para usuarios de VPN | >= 90% = BAIX; 60-89 = MIG; 30-59 = ALT; < 30 = MOLT ALT | `REAL` si hay dato; `DEFAULT` si falta y se asume 100% |
| 2004 | MFA O365 usuarios | `% MFA O365` desde `silver.vw_src_prob_puestos_mfa_o365` | mide cobertura MFA para usuarios O365 | mismo tramo que 2003 | `REAL` si hay dato; `DEFAULT` si falta y se asume 100% |
| 2005 | MFA cuentas genericas | decision funcional | se considera que las cuentas genericas no tienen MFA real gestionado por fuente | siempre MOLT ALT | `CONSTANTE`, valor fijo 0% MFA |
| 2006 | Formacion usuarios | `silver.fact_training.passed` + parque de workstations | compara aprobados de formaciones realizadas/finalizadas frente al parque del ambito; limita la cobertura al 100% | > 60% = BAIX; 45-60 = MIG; 30-44 = ALT; < 30 = MOLT ALT | `REAL` si hay workstations; `DEFAULT` si falta denominador y se asume 100% |
| 2007 | TPM | `% equipos con TPM` | mide cobertura real de TPM en el ambito | >= 95% = BAIX; < 95 = MOLT ALT | `REAL` si hay dato; `DEFAULT` si falta y se asume 100% |
| 2008 | EDR correo / plataforma | `% equipos con EDR` | reutiliza cobertura EDR como senal de proteccion de plataforma de usuario | >= 96% = BAIX; 91-95 = MIG; 86-90 = ALT; < 86 = MOLT ALT | `REAL` si hay dato; `DEFAULT` si falta y se asume 100% |
| 2009 | MFA O365 correo / plataforma | `% MFA O365` | misma semantica de cobertura MFA para correo/plataforma | >= 90% = BAIX; 60-89 = MIG; 30-59 = ALT; < 30 = MOLT ALT | `REAL` si hay dato; `DEFAULT` si falta y se asume 100% |
| 2010 | Cuentas genericas en correo / plataforma | `generic_accounts` en `silver.vw_src_prob_puestos_o365_vpn` | no mide MFA real; mide cantidad de cuentas genericas como riesgo operativo | 0 = BAIX; 1-199 = MIG; 200-700 = ALT; > 700 = MOLT ALT | `REAL` si hay dato; `DEFAULT` si falta y se asume 0 cuentas |
| 2011 | Formacion usuarios correo / plataforma | training departamental | reutiliza el indicador de aprobados del bloque 200, limitado al 100% | > 60% = BAIX; 45-60 = MIG; 30-44 = ALT; < 30 = MOLT ALT | `REAL` si hay workstations; `DEFAULT` si falta denominador y se asume 100% |
| 2012 | Parches desactualizados para credenciales | `% equipos con mas de 60 dias sin actualizar` | usa la metrica operativa real de parchado para exposicion a credenciales | < 30% = BAIX; 30-79 = MIG; 80-89 = ALT; >= 90 = MOLT ALT | `REAL` si hay dato; `DEFAULT` si falta y se asume 0% |
| 2013 | Cifrado del disco | `% equipos cifrados` | mide cobertura real de cifrado del puesto en el ambito | >= 95% = BAIX; 50-94 = ALT; < 50 = MOLT ALT | `REAL` si hay dato; `DEFAULT` si falta y se asume 100% |

### Bloque 300. Compromiso del equipo

| Regla | Objetivo funcional | Que mira | Como se calcula | Valores / niveles | Tipo y default |
|---|---|---|---|---|---|
| 3001 | Antivirus | `% equipos con antivirus` | misma logica que 1001, aplicada al riesgo de compromiso del equipo | >= 96% = BAIX; 91-95 = MIG; 86-90 = ALT; < 86 = MOLT ALT | `REAL` si hay dato; `DEFAULT` si falta y se asume 100% |
| 3002 | EDR | `% equipos con EDR` | misma logica que 1002 | >= 96% = BAIX; 91-95 = MIG; 86-90 = ALT; < 86 = MOLT ALT | `REAL` si hay dato; `DEFAULT` si falta y se asume 100% |
| 3003 | Parches desactualizados | `% equipos con mas de 60 dias sin actualizar` | misma logica que 1003 | < 30% = BAIX; 30-79 = MIG; 80-89 = ALT; >= 90 = MOLT ALT | `REAL` si hay dato; `DEFAULT` si falta y se asume 0% |
| 3004 | Alertas no resueltas | tickets departamentales `Tancat` | misma logica que 1004 | 0 = BAIX; 1-5 = ALT; > 5 = MOLT ALT | `REAL` si hay fila; `DEFAULT` si falta y se asume 0 |
| 3005 | Obsolescencia de version SO | `% equipos con SO obsoleto` | usa la lectura de obsolescencia SO publicada en Silver para el ambito | 0% obsoleto = BAIX; > 0% = ALT | `REAL` si hay dato; `DEFAULT` si no hay dato y se asume 0% |
| 3006 | Parches desactualizados para malware/explotacion | `% equipos con mas de 60 dias sin actualizar` | misma logica que 1003 y 3003 | < 30% = BAIX; 30-79 = MIG; 80-89 = ALT; >= 90 = MOLT ALT | `REAL` si hay dato; `DEFAULT` si falta y se asume 0% |
| 3007 | Obsolescencia SO para riesgo de explotacion | `% equipos con SO obsoleto` | misma logica que 3005 | 0% obsoleto = BAIX; > 0% = ALT | `REAL` si hay dato; `DEFAULT` si no hay dato |

### Bloque 400. Incumplimiento legal y normativo

| Regla | Objetivo funcional | Que mira | Como se calcula | Valores / niveles | Tipo y default |
|---|---|---|---|---|---|
| 4001 | Formacion de usuarios en cumplimiento | training departamental | reutiliza el indicador de formacion para cumplimiento | > 60% = BAIX; 45-60 = MIG; 30-44 = ALT; < 30 = MOLT ALT | `REAL` si hay training activo; `DEFAULT` si falta y se asume 100% |

### Lectura funcional de los defaults en LLDT

En LLDT, la mayoria de los defaults son provisionales y optimistas:

- si falta una cobertura positiva, suele asumirse 100%;
- si falta una cobertura negativa, suele asumirse 0%;
- el objetivo es no bloquear el calculo mientras se mantiene trazabilidad de la falta de dato.

Esto es importante para negocio: un `DEFAULT` LLDT no significa que el control este bien medido. Significa que el modelo no dispone de dato usable y adopta una hipotesis de continuidad.

---

## 7.3. Impacto LLDT

## 7.3.1. Como se calcula en Gold

El impacto LLDT vigente no se publica regla a regla en Gold, pero internamente si combina reglas de dos tipos:

1. reglas con valoracion propia departamental desde `silver.dim_lldt_cidat`;
2. reglas que requieren un SIC para poder calcularse y por eso usan `codi_dialeg` como SIC emulado del departamento.

La resolucion vigente queda asi:

1. busca la fila del departamento en `silver.dim_lldt_cidat`;
2. toma `codi_dialeg` como SIC emulado del departamento;
3. calcula reglas SIC-emuladas con `silver.inv_sic_atributos_current` para RTO, criticidad, usuarios y T11/publico;
4. calcula la regla 204 con `key_seguretat` propio del departamento;
5. calcula la regla 401 con el maximo entre C, I, D, A y T del propio departamento;
6. promedia por bloque las reglas resultantes y publica ese nivel agregado en `gold_lldt.fact_impacto_bloque`.

Traduccion funcional:

- LLDT ya no debe leerse como una severidad unica replicada a cuatro bloques;
- cada bloque sale de una mezcla distinta entre la valoracion propia del departamento y el SIC que ese departamento debe emular.

## 7.3.2. Semantica funcional del catalogo LLDT

Aunque Gold no publica 12 reglas de impacto separadas, el catalogo funcional si define la intencion de cada una:

| Regla | Significado funcional | Que queria mirar el workbook |
|---|---|---|
| 101 | Tiempo maximo tolerable de indisponibilidad | `RTO` |
| 102 | Ambito de usuarios y criticidad del sistema | criticidad + usuarios expuestos |
| 103 | Criticidad del sistema | criticidad de negocio |
| 104 | Ambito y volumetria de usuarios afectados | numero de usuarios |
| 105 | Impacto legal segun criticidad | criticidad de negocio |
| 201 | Volumetria de usuarios afectados | numero de usuarios |
| 202 | Ambito de usuarios | numero de usuarios / publico |
| 203 | Criticidad del sistema | criticidad de negocio |
| 204 | Nivel de clasificacion de la informacion | `key_seguretat` / clasificacion |
| 301 | Volumetria de usuarios y criticidad | usuarios + criticidad |
| 401 | Proteccion de datos y ENS | maximo entre C, I, D, A y T |
| 402 | Ambito de usuarios y criticidad del sistema | criticidad + usuarios expuestos |

Conclusion funcional para LLDT:

- la intencion del modelo sigue siendo rica y multi-regla;
- la implementacion Gold vigente agrega por bloque, pero ya no reduce todo a una sola valoracion compartida.

---

## 8. Dominio SIC

## 8.1. Que calcula SIC

SIC calcula riesgo por sistema / aplicacion critica.

A diferencia de LLDT:

- SIC si calcula probabilidad regla por regla;
- SIC si calcula impacto regla por regla;
- luego agrega por bloque y obtiene riesgo final por bloque y por SIC.

Este es el dominio mas completo desde el punto de vista del calculo Gold.

---

## 8.2. Probabilidad SIC por regla

### Bloque 100. Indisponibilidad

| Regla | Objetivo funcional | Que mira | Como se calcula | Valores / niveles | Tipo y default |
|---|---|---|---|---|---|
| 1001 | Despliegue EDR por SIC | cobertura EDR por hosts relacionados con el SIC | usa bridge host -> app -> SIC y la foto EDR actual | >= 95% = BAIX; 91-94 = MIG; 86-90 = ALT; < 86 = MOLT ALT | `REAL` si hay coverage; `DEFAULT` neutral nivel 2 si no hay mapeo usable |
| 1002 | Estado del perimetro base | `base_attributes_noncompleted` de `silver.fact_perimetro` con `status = Alta` | toma la foto mas reciente del perimetro usable y calcula `% despliegue base = 1 - (base_attributes_noncompleted / 6)` | 100% = BAIX; 85%-99% = MIG; 1%-84% = ALT; 0% = MOLT ALT | `REAL`; `DEFAULT` nivel 2 si falta perimetro usable |
| 1003 | Vulnerabilidades criticas | numero de `Critical` abiertas | cuenta vulnerabilidades criticas no remediadas | 0 = BAIX; 1-5 = ALT; > 5 = MOLT ALT | `REAL` |
| 1004 | Alertas criticas no resueltas | tickets departamentales asociados al SIC | usa conteo operativo de tickets por departamento | 0 = BAIX; 1-5 = ALT; > 5 = MOLT ALT | `REAL`; `DEFAULT` neutral nivel 2 si falta fila |
| 1005 | Exposicion a amenaza en CPD | `valor_exposicion` BAIX/MIG/ALT/MOLT ALT | traduce la exposicion CPD del SIC ya resuelta en Silver | BAIX = 1; MIG = 2; ALT = 3; MOLT ALT = 4 | `REAL` si existe exposicion; `DEFAULT` nivel 2 si ni siquiera hay regla resoluble; `CONSTANTE` nivel 3 si la regla existe pero el valor concreto queda vacio |
| 1006 | Publicacion a internet | `is_t11` | distingue servicio interno frente a servicio expuesto a publico | interno = BAIX; T11/publico = ALT; sin dato = MIG | `REAL` si hay dato; `DEFAULT` neutral si falta |

### Bloque 200. Compromiso y perdida de informacion

| Regla | Objetivo funcional | Que mira | Como se calcula | Valores / niveles | Tipo y default |
|---|---|---|---|---|---|
| 2001 | EDR para proteccion de credenciales | cobertura EDR del SIC | misma matriz de 1001, leida como dato operativo vigente del SIC | >= 95% = BAIX; 91-94 = MIG; 86-90 = ALT; < 86 = MOLT ALT | `REAL` si hay dato; `DEFAULT` neutral nivel 2 si falta |
| 2002 | MFA VPN administradores | decision funcional | se considera cubierto al 100% | siempre BAIX | `CONSTANTE` |
| 2003 | MFA cloud administradores | decision funcional | se considera cubierto al 100% | siempre BAIX | `CONSTANTE` |
| 2004 | MFA aplicaciones administradores | decision funcional | se considera cubierto al 100% | siempre BAIX | `CONSTANTE` |
| 2005 | MFA aplicaciones usuarios | decision funcional | se considera que no existe MFA de usuarios a nivel aplicacion/SIC | siempre MOLT ALT | `CONSTANTE` |
| 2006 | Exposicion CPD para compromiso de informacion | `valor_exposicion` del cruce SIC -> CPD | misma logica que 1005 aplicada al riesgo 200 | BAIX = 1; MIG = 2; ALT = 3; MOLT ALT = 4 | `REAL` si hay valor; `DEFAULT` 2 si falta la resolucion; `CONSTANTE` 3 si la regla existe sin valor |
| 2007 | Integracion con GICAR | `has_gicar` | asume menor riesgo si el SIC integra GICAR | con GICAR = BAIX; sin GICAR = ALT | `REAL` si el origen informa; `DEFAULT` si el origen llega vacio |
| 2008 | Vulnerabilidades criticas para compromiso de informacion | vulnerabilidades Critical abiertas | misma logica que 1003 | 0 = BAIX; 1-5 = ALT; > 5 = MOLT ALT | `REAL` |
| 2009 | Exposicion CPD para compromiso tecnico | `valor_exposicion` CPD | misma logica que 1005 y 2006 | BAIX = 1; MIG = 2; ALT = 3; MOLT ALT = 4 | `REAL` / `DEFAULT` / `CONSTANTE` segun disponibilidad del valor |
| 2010 | Estado del perimetro base para exfiltracion / compromiso | `base_attributes_noncompleted` con `status = Alta` | misma logica que 1002 sobre el despliegue del perimetro base | 100% = BAIX; 85%-99% = MIG; 1%-84% = ALT; 0% = MOLT ALT | `REAL`; `DEFAULT` 2 si falta perimetro usable |
| 2011 | Publicacion a internet para compromiso de informacion | `is_t11` | misma semantica que 1006 | interno = BAIX; publico = ALT; sin dato = MIG | `REAL`; `DEFAULT` si falta |

### Bloque 300. Compromiso del equipo o plataforma

| Regla | Objetivo funcional | Que mira | Como se calcula | Valores / niveles | Tipo y default |
|---|---|---|---|---|---|
| 3001 | EDR para malware / ransomware | cobertura EDR del SIC | misma matriz de 1001 | >= 95% = BAIX; 91-94 = MIG; 86-90 = ALT; < 86 = MOLT ALT | `REAL`; `DEFAULT` 2 si falta |
| 3002 | Estado del perimetro tecnico base | `base_attributes_noncompleted` con `status = Alta` | misma logica que 1002 sobre el despliegue del perimetro base | 100% = BAIX; 85%-99% = MIG; 1%-84% = ALT; 0% = MOLT ALT | `REAL`; `DEFAULT` |
| 3003 | Vulnerabilidades criticas de plataforma | Critical abiertas | misma logica que 1003 | 0 = BAIX; 1-5 = ALT; > 5 = MOLT ALT | `REAL` |
| 3004 | Alertas criticas no resueltas | tickets asociados por departamento | misma logica que 1004 | 0 = BAIX; 1-5 = ALT; > 5 = MOLT ALT | `REAL`; `DEFAULT` 2 si falta |
| 3005 | Exposicion a amenaza CPD | `valor_exposicion` CPD | misma logica de exposicion CPD | BAIX = 1; MIG = 2; ALT = 3; MOLT ALT = 4 | `REAL`; `DEFAULT` 2; `CONSTANTE` 3 si la regla queda sin valor concreto |
| 3006 | Publicacion a internet | `is_t11` | misma semantica que 1006 | interno = BAIX; publico = ALT; sin dato = MIG | `REAL`; `DEFAULT` |
| 3007 | Obsolescencia SO del parque soportado | `% hosts obsoletos` vinculados al SIC | cruza `silver.vw_crowdstrike_cpd_current` con `silver.ref_sic_server_os_lifecycle` via `silver.inv_sic_host_current` | sin hosts = ALT default; 0% obsoleto = BAIX; > 0% = ALT | `REAL` si hay parque usable; `DEFAULT` si no hay parque usable |
| 3008 | Vulnerabilidades criticas para compromiso del equipo | Critical abiertas | misma logica que 3003 | 0 = BAIX; 1-5 = ALT; > 5 = MOLT ALT | `REAL` |
| 3009 | Exposicion CPD para explotacion | `valor_exposicion` CPD | misma logica que 3005 | BAIX = 1; MIG = 2; ALT = 3; MOLT ALT = 4 | `REAL`; `DEFAULT` 2; `CONSTANTE` 3 si no llega valor |
| 3010 | Perimetro tecnico base complementario | `base_attributes_noncompleted` con `status = Alta` | misma semantica que 3002 sobre el despliegue del perimetro base | 100% = BAIX; 85%-99% = MIG; 1%-84% = ALT; 0% = MOLT ALT | `REAL`; `DEFAULT` |
| 3011 | Obsolescencia SO para otra familia de compromiso | `% hosts obsoletos` | misma logica que 3007 usando CPD current + catalogo lifecycle de servidores | sin hosts = ALT default; 0% obsoleto = BAIX; > 0% = ALT | `REAL` si hay parque usable; `DEFAULT` si no hay parque usable |
| 3012 | Publicacion a internet complementaria | `is_t11` | misma semantica que 3006 | interno = BAIX; publico = ALT; sin dato = MIG | `REAL`; `DEFAULT` |

### Bloque 400. Incumplimiento legal y normativo

| Regla | Objetivo funcional | Que mira | Como se calcula | Valores / niveles | Tipo y default |
|---|---|---|---|---|---|
| 4001 | Certificaciones / auditorias | `silver.fact_certificacion_sic` por SIC | Silver interpreta `CAU_DIALOG_CODE_CERTIFICATIONS.FK_ID_DIALOG_CODE` como lista operativa de SICs y la expande por `;`: certificacion activa vigente = BAIX `REAL`, solo certificacion caducada/no vigente = MOLT ALT `REAL`, sin SIC certificado usable = MIG `DEFAULT` | BAIX / MIG / MOLT ALT | `REAL` si existe certificacion materializada; `DEFAULT` si no |
| 4002 | Politica de ciberseguridad | `silver.fact_gobernanza_departamento` por departamento | lee el control departamental silverizado desde `XLS_Gobernanza`: `Si` = BAIX, `No` = MOLT ALT, sin dato usable = MIG | BAIX / MIG / MOLT ALT | `REAL` si hay dato; `DEFAULT` si falta |
| 4003 | Marco normativo actualizado | `silver.fact_gobernanza_departamento` por departamento | misma logica directa si/no por departamento | BAIX / MIG / MOLT ALT | `REAL` si hay dato; `DEFAULT` si falta |
| 4004 | Roles definidos | `silver.fact_gobernanza_departamento` por departamento | misma logica directa si/no por departamento | BAIX / MIG / MOLT ALT | `REAL` si hay dato; `DEFAULT` si falta |
| 4005 | DPD | `silver.fact_gobernanza_departamento` por departamento | misma logica directa si/no por departamento | BAIX / MIG / MOLT ALT | `REAL` si hay dato; `DEFAULT` si falta |
| 4006 | Comite de seguridad | `silver.fact_gobernanza_departamento` por departamento | misma logica directa si/no por departamento | BAIX / MIG / MOLT ALT | `REAL` si hay dato; `DEFAULT` si falta |

### Lectura funcional de los defaults en SIC

En SIC, el default no suele ser optimista como en LLDT. Normalmente es neutral o controlado:

- reglas EDR sin mapping host -> app -> SIC caen a nivel 2, no al mejor caso;
- en bloque 4000, la 4001 sale desde `silver.fact_certificacion_sic`; cuando esa proyeccion no materializa un SIC con certificacion usable, el resultado observable es `MIG` `DEFAULT`, no una ausencia de cableado;
- varias reglas CPD distinguen entre ausencia total de resolucion y ausencia del valor final.

Esto hace que SIC sea, funcionalmente, mas conservador que LLDT cuando falta dato.

---

## 8.3. Impacto SIC por regla

### Bloque 100. Indisponibilidad

| Regla | Objetivo funcional | Como se calcula | Valores / niveles | Tipo y default |
|---|---|---|---|---|
| 101 | Tiempo maximo tolerable de indisponibilidad | lee `rto` del SIC emulado informado en `codi_dialeg` | `0 horas` = BAIX; `1/8/24 horas` = MIG; `1-3 dias / 48 / 72` = ALT; sin dato = MOLT ALT | `REAL` si existe SIC usable con `rto`; `DEFAULT` si falta |
| 102 | Ambito de usuarios y criticidad | combina `criticidad_negocio` y `num_usuarios_max` del SIC emulado informado en `codi_dialeg` | criticidad 0 con >=1000 usuarios = 4; criticidad 0 = 3; criticidad 1-2 con >=1000 = 3; criticidad 1-4 = 2; resto = 1 | `REAL` si existe SIC usable; `DEFAULT` si falta |
| 103 | Criticidad del sistema | usa `criticidad_negocio` directamente | criticidad 0-1 = 4; 2-3 = 3; 4 = 2; resto = 1 | `REAL` si informado; `DEFAULT` si falta |
| 104 | Ambito y volumetria de usuarios afectados | usa `D_NUMBER_CONSULTANT_USERS` e `is_t11` | T11/publico = ALT; menos de 500 usuarios = BAIX; 500 o mas = MIG; sin dato = MIG | `REAL` si informado; `DEFAULT` si falta todo |
| 105 | Impacto legal por criticidad | misma semantica que 103 | criticidad 0-1 = 4; 2-3 = 3; 4 = 2; resto = 1 | `REAL`; `DEFAULT` si falta |

### Bloque 200. Compromiso y perdida de informacion

| Regla | Objetivo funcional | Como se calcula | Valores / niveles | Tipo y default |
|---|---|---|---|---|
| 201 | Volumetria de usuarios afectados | usa `num_usuarios_max` del SIC emulado informado en `codi_dialeg` | <= 500 = BAIX; 501-3000 = MIG; 3001-9000 = ALT; > 9000 = MOLT ALT | `REAL` si existe SIC usable; `DEFAULT` si falta |
| 202 | Ambito de usuarios | usa `is_t11` | interno = BAIX; publico/T11 = ALT; sin dato = MIG | `REAL`; `DEFAULT` si falta |
| 203 | Criticidad del sistema | misma semantica que 105 | criticidad 0-1 = 4; 2-3 = 3; 4 = 2; resto = 1 | `REAL`; `DEFAULT` si falta |
| 204 | Clasificacion de la informacion | usa `key_seguretat` del catalogo SIC/CIDAT | 1-4 se toman como nivel directo; si falta se aplica 4 | `REAL` si existe; `DEFAULT` al maximo si falta |

### Bloque 300. Compromiso del equipo o plataforma

| Regla | Objetivo funcional | Como se calcula | Valores / niveles | Tipo y default |
|---|---|---|---|---|
| 301 | Volumetria de usuarios y criticidad del sistema | combina `criticidad_negocio` y `num_usuarios_max` del SIC emulado informado en `codi_dialeg` | > 9000 usuarios o criticidad 0-1 = 4; > 3000 o criticidad 2-3 = 3; > 500 o criticidad 4 = 2; resto = 1 | `REAL` si existe SIC usable; `DEFAULT` si falta |

### Bloque 400. Incumplimiento legal y normativo

| Regla | Objetivo funcional | Como se calcula | Valores / niveles | Tipo y default |
|---|---|---|---|---|
| 401 | Proteccion de datos y ENS | toma el maximo entre C, I, D, A y T | maximo CIDAT = nivel final | `REAL` si hay CIDAT; `DEFAULT` nivel 2 si falta |
| 402 | Ambito de usuarios y criticidad | replica la misma logica funcional de la 102 sobre el SIC emulado informado en `codi_dialeg` | misma matriz que 102 | `REAL` si existe SIC usable; `DEFAULT` si falta |

---

## 9. Como se agrega por bloque

### LLDT

LLDT hace dos agregaciones:

1. promedio de las reglas de probabilidad del bloque;
2. cruce con el impacto final del bloque usando la matriz 4x4 de doble entrada.

La tabla de bloque conserva contadores utiles para negocio y auditoria:

- cuantas reglas del bloque fueron `REAL`;
- cuantas quedaron en `DEFAULT`;
- cuantas son `CONSTANTE`.

### SIC

SIC agrega en tres escalas:

1. promedio por bloque;
2. promedio final por SIC;
3. riesgo final por bloque.

Tambien conserva contadores de calidad del calculo:

- reales;
- defaults;
- constantes;
- y, en impacto, no disponibles.

### CULTURA

CULTURA agrega igual que SIC, pero solo sobre los bloques activos del dominio:

1. promedio por bloque de las reglas activas;
2. cruce con impacto final usando la misma matriz 4x4;
3. publicacion final por departamento de referencia dentro de `gold_cultura.fact_riesgo`.

Tambien conserva trazabilidad por regla en `fact_probabilidad` y `fact_impacto`.

### GOVERNANCA

GOVERNANCA agrega igual que CULTURA, con la salvedad de que su bloque 4000 mezcla training, certificaciones SIC y gobernanza departamental remapeada.

La lectura funcional correcta exige mirar siempre:

1. el detalle por regla en `gold_governanca.fact_probabilidad`;
2. el agregado por bloque en `gold_governanca.fact_probabilidad_bloque` y `gold_governanca.fact_impacto_bloque`;
3. el resultado final en `gold_governanca.fact_riesgo`.

---

## 10. Lecturas funcionales importantes para negocio

## 10.1. Los 5 ejes no tratan igual la falta de dato

- LLDT suele resolver la ausencia de dato con defaults provisionales favorables, para no cortar el calculo departamental.
- SIC suele usar defaults neutrales o controlados, especialmente en reglas EDR y en 4001 mientras esa regla siga sin proyeccion Silver operativa.
- CULTURA usa defaults altos en probabilidad de training y neutrales en impacto reutilizado.
- GOVERNANCA combina defaults altos en training con defaults controlados en certificaciones y gobernanza departamental.
- INFRA reutiliza la lectura funcional del metodo SIC, pero aplicada sobre un scope propio de `gold_infra.dim_sig` derivado de `silver.dim_infra_cidat`.

## 10.2. El nivel de una regla no siempre nace de un dato exacto

Hay tres situaciones distintas:

- medicion real del control;
- default por falta de cobertura;
- constante funcional pactada.

La interpretacion de negocio debe mirar siempre tambien el `tipo_valor`, no solo el nivel numerico.

## 10.3. Criticidad de negocio en SIC tiene una escala propia

En la implementacion vigente, `criticidad_negocio` se interpreta asi:

- valores 0 y 1 implican mayor severidad;
- 2 y 3 severidad intermedia;
- 4 menor severidad relativa.

No debe leerse como una escala ascendente simple de 1 a 4.

## 10.4. Como queda resuelto el bloque 4000 de SIC

Funcionalmente significa:

- el bloque 4000 forma parte del resultado publicado de SIC;
- la definicion funcional de datos es `CAU_DIALOG_CODE_CERTIFICATIONS` para 4001 y `XLS_Gobernanza` para 4002-4006;
- 4002-4006 se leen desde `silver.fact_gobernanza_departamento` y el motor Gold las consume por `codigo_departamento`;
- la traduccion vigente es directa: `Si` = BAIX, `No` = MOLT ALT, sin dato usable = MIG `DEFAULT`;
- 4001 se lee desde `silver.fact_certificacion_sic`; si esa proyeccion no materializa un SIC con certificacion usable, el resultado visible para esa regla queda en `MIG` `DEFAULT`.

## 10.5. Como debe leerse el impacto LLDT

El catalogo describe 12 reglas de impacto y la implementacion Gold vigente las resuelve a nivel de bloque con dos familias de datos:

- datos propios del departamento desde `silver.dim_lldt_cidat`, usados en 204 y 401;
- datos del SIC emulado informado en `codi_dialeg`, usados para reglas que dependen de RTO, criticidad, usuarios o exposicion publica.

Lectura de cierre para las reglas LLDT 102 y 201:

- la 102 se alinea a la logica SIC de criticidad + usuarios, pero en LLDT debe leerse como `REAL` cuando `silver.dim_lldt_cidat.codi_dialeg` informa un SIC critico usable para el departamento;
- la 201 debe leerse como `REAL` cuando el SIC critico usable esta informado y como `DEFAULT` cuando falta.
- la 301 y la 402 siguen la misma lectura operativa que la 102: `REAL` cuando el SIC critico usable esta informado y `DEFAULT` cuando falta.

Por lo tanto, el impacto LLDT no debe leerse como una severidad unica replicada a cuatro riesgos. Debe leerse como una construccion por bloque apoyada en una mezcla fija y trazable entre catalogo departamental y SIC emulado.

## 10.6. Como debe leerse el bloque 4000 de GOVERNANCA

El bloque 4000 de GOVERNANCA no debe leerse como una copia mecanica del 4000 SIC.

Su lectura correcta es esta:

- `4001` mantiene la logica de training del dominio;
- `4002` reutiliza certificaciones SIC desde `silver.fact_certificacion_sic`;
- `4003-4007` reutilizan gobernanza departamental, pero con remapeo explicito desde `silver.fact_gobernanza_departamento` `4002-4006`.

Eso permite conservar compatibilidad con SIC en Silver sin mezclar numeraciones funcionales dentro de Gold.

---

## 11. Donde ver el resultado funcional

La lectura funcional correcta no sale de una sola tabla. En ambos dominios conviene seguir siempre el mismo orden:

1. identificar la ejecucion en auditoria;
2. mirar el resultado final publicado;
3. abrir el bloque que explica ese resultado;
4. bajar al detalle de reglas y al catalogo funcional que las describe.

Para esa trazabilidad hay que separar dos conceptos:

- `modo_carga` indica el camino tecnico de calculo usado por el motor, por ejemplo `sql_v1_silver`;
- `version_modelo` indica la etiqueta del corte funcional publicado.

En el estado vigente del repositorio no conviven varias versiones funcionales activas del modelo. Por eso el valor canonico por defecto de `version_modelo` es `v1_modelo_actual` en los cinco dominios y solo debe cambiarse cuando se quiera dejar trazada de forma explicita una variante coexistente.

## 11.0. Como leer nivel y peso en probabilidad

Antes de agregar reglas conviene separar tres conceptos:

- `valor` o dato fuente: es el porcentaje, recuento, si/no o constante original que llega a una regla;
- `nivel_num` y `nivel_texto`: son la traduccion de ese dato a la escala comun del modelo, donde `1 = BAIX`, `2 = MIG`, `3 = ALT` y `4 = MOLT ALT`;
- `peso_regla`: es el factor con el que una regla entra al agregado del bloque o del eje completo.

Por lo tanto, el motor Gold no mezcla porcentajes crudos, tickets o booleanos entre si. Primero traduce cada regla a un nivel comun y despues agrega esos niveles.

Lectura funcional correcta del `nivel`:

- no significa porcentaje de cumplimiento;
- no significa si la regla da verdadero o falso;
- significa severidad final de esa regla ya interpretada por el modelo.

Lectura funcional correcta del agregado de probabilidad:

- `fact_probabilidad` publica el detalle por regla, con su `valor`, su `nivel` y su `tipo_valor`;
- `fact_probabilidad_bloque` agrega los `nivel_num` de las reglas del bloque;
- si el dominio tiene pesos configurados para esas reglas, el agregado es ponderado por `peso_regla`;
- si todos los pesos activos son iguales, el resultado equivale a un promedio simple de niveles;
- si alguna regla tiene `peso_regla = 0`, esa regla sigue visible en trazabilidad pero no influye en el promedio mientras existan otras con peso positivo.

La formula funcional del agregado de probabilidad es esta:

- si la suma de pesos del conjunto es mayor que cero, se calcula `SUM(nivel_num * peso_regla) / SUM(peso_regla)`;
- si no hay pesos positivos, se calcula `AVG(nivel_num)`.

Despues de ese promedio, el motor redondea el resultado al entero mas cercano y lo vuelve a expresar como `BAIX`, `MIG`, `ALT` o `MOLT ALT`.

## 11.1. Eje LLDT

Unidad de lectura: departamento o ambito de puestos.

Orden recomendado de consulta:

1. `gold_lldt.fact_riesgo` para ver el resultado final por bloque;
2. `gold_lldt.fact_impacto_bloque` y `gold_lldt.fact_probabilidad_bloque` para entender de donde sale ese riesgo;
3. `gold_lldt.fact_probabilidad` para bajar al detalle de reglas;
4. `gold_lldt.dim_regla` y `gold_lldt.dim_supuesto_modelo` para interpretar semanticamente cada codigo y cada supuesto del modelo.

| Objeto | Que muestra | Como se usa funcionalmente |
|---|---|---|
| `audit.gold_risk_run` | una fila por ejecucion LLDT con `run_id`, version del modelo, estado y conteos | sirve para saber que ejecucion esta leyendo negocio, si termino bien y con que version quedo publicada |
| `audit.execution_log` | traza tecnica de ejecucion del SP | sirve para validar que la ejecucion LLDT termino sin error y en que ventana temporal corrio |
| `gold_lldt.dim_departamento_scope` | perimetro departamental efectivamente calculado | define que departamentos entran al modelo y con que nombre/codigo se publican |
| `gold_lldt.dim_regla` | catalogo funcional de reglas LLDT activas | traduce `codigo_regla`, `bloque`, `id_risc` y descripcion funcional para leer las facts |
| `gold_lldt.dim_supuesto_modelo` | supuestos, constantes y criterios de lectura del eje LLDT | explica por que una regla usa dato real, default o constante y cuales son las decisiones funcionales vigentes |
| `gold_lldt.fact_probabilidad` | una fila por regla de probabilidad y por departamento | muestra el valor calculado, nivel numerico/textual, `tipo_valor`, fuente, `peso_regla` y nota de supuesto para cada regla LLDT |
| `gold_lldt.fact_probabilidad_bloque` | una fila por bloque y por departamento | resume la probabilidad final del bloque como agregado de niveles por regla, ponderado por `peso_regla` cuando existe configuracion activa, y publica contadores de `REAL`, `DEFAULT` y `CONSTANTE` |
| `gold_lldt.fact_impacto_bloque` | una fila por bloque y por departamento | publica el impacto final usado por LLDT, el `impacto_origen_tipo`, el SIC emulado si aplica y la nota funcional del bloque |
| `gold_lldt.fact_riesgo` | una fila final por bloque y por departamento | es la salida final de LLDT: probabilidad final, impacto final y riesgo final ya cruzados por la matriz 4x4 |

Lectura funcional minima de una fila LLDT:

- `codigo_departamento` identifica el ambito;
- `bloque` e `id_risc` indican que riesgo se esta leyendo;
- `probabilidad_final_num` e `impacto_final_num` muestran los dos ejes que entran a la matriz;
- `riesgo_final_num` es el resultado publicado;
- `run_id` y `version_modelo` permiten reconstruir exactamente con que ejecucion se calculo.

## 11.2. Eje SIC

Unidad de lectura: SIC o aplicacion critica.

Orden recomendado de consulta:

1. `gold_sic.fact_riesgo` para ver el resultado final por SIC y por bloque;
2. `gold_sic.fact_probabilidad_bloque` y `gold_sic.fact_impacto_bloque` para abrir la explicacion por bloque;
3. `gold_sic.fact_probabilidad` y `gold_sic.fact_impacto` para bajar a cada regla;
4. `gold_sic.fact_probabilidad_sig` y `gold_sic.fact_impacto_sig` para ver el resumen global por SIC;
5. `gold_sic.dim_regla` y `gold_sic.dim_supuesto_modelo` para interpretar reglas, defaults y supuestos.

| Objeto | Que muestra | Como se usa funcionalmente |
|---|---|---|
| `audit.gold_risk_run` | una fila por ejecucion SIC con `run_id`, version y conteos | sirve para fijar la ejecucion publicada y validar que la carga SIC termino en `SUCCESS` |
| `audit.execution_log` | traza tecnica del procedimiento SIC | permite confirmar ventana de ejecucion, estado y errores si los hubiera |
| `gold_sic.dim_sig` | universo de SICs y aplicaciones que entran al calculo | define la lista de SIC evaluados y su identificacion funcional de lectura |
| `gold_sic.dim_regla` | catalogo funcional de reglas SIC activas | explica codigo, bloque, riesgo, amenaza y fuente principal de cada regla |
| `gold_sic.dim_supuesto_modelo` | supuestos funcionales del eje SIC | documenta constantes, defaults y criterios operativos usados por el motor Gold |
| `gold_sic.fact_probabilidad` | una fila por regla de probabilidad y por SIC | muestra valor base, nivel, `tipo_valor`, fuente, `peso_regla` y notas de interpretacion por regla |
| `gold_sic.fact_probabilidad_bloque` | una fila por bloque y por SIC | resume la probabilidad final del bloque como agregado de niveles por regla, ponderado por `peso_regla` cuando existe configuracion activa, y la calidad del calculo con contadores de reales, defaults y constantes |
| `gold_sic.fact_probabilidad_sig` | una fila resumen por SIC | agrega toda la probabilidad del SIC con el mismo criterio de niveles y pesos y permite ver el nivel final medio del eje probabilidad para ese sistema |
| `gold_sic.fact_impacto` | una fila por regla de impacto y por SIC | publica cada regla de impacto con su nivel, `tipo_valor`, estado y origen funcional |
| `gold_sic.fact_impacto_bloque` | una fila por bloque y por SIC | resume el impacto final por riesgo, incluyendo contadores de `REAL`, `DEFAULT` y no disponibles |
| `gold_sic.fact_impacto_sig` | una fila resumen por SIC | agrega el impacto de los cuatro riesgos y deja un nivel final medio de impacto para el SIC |
| `gold_sic.fact_riesgo` | una fila final por bloque y por SIC | es la salida final del modelo SIC: cruza probabilidad final e impacto final del bloque y publica el riesgo resultante |

Lectura funcional minima de una fila SIC:

- `sic` identifica el sistema o aplicacion;
- `bloque` e `id_risc` indican el riesgo evaluado;
- `probabilidad_final_num` e `impacto_final_num` muestran los niveles finales del bloque;
- `riesgo_final_num` expresa el nivel publicado para ese riesgo;
- `run_id` y `version_modelo` permiten auditar la ejecucion exacta.

## 11.3. Eje CULTURA

Unidad de lectura: departamento de referencia (`codigo_departamento_ref`) dentro del scope del eje CULTURA, con SIC canonico auxiliar solo como atributo de apoyo.

Orden recomendado de consulta:

1. `gold_cultura.fact_riesgo` para ver el resultado final por bloque;
2. `gold_cultura.fact_probabilidad_bloque` y `gold_cultura.fact_impacto_bloque` para abrir la explicacion por bloque;
3. `gold_cultura.fact_probabilidad` y `gold_cultura.fact_impacto` para bajar al detalle de reglas;
4. `gold_cultura.dim_regla` y `gold_cultura.dim_supuesto_modelo` para interpretar codigos, defaults y supuestos.

Lectura funcional minima de una fila CULTURA:

- `codigo_departamento_ref` identifica el departamento publicado;
- `sic` queda como atributo auxiliar cuando el modelo necesita SIC canonico para resolver impacto;
- `bloque` indica si el resultado pertenece al riesgo 200 o 400;
- `probabilidad_final_num` e `impacto_final_num` muestran los niveles finales del bloque;
- `riesgo_final_num` es el resultado publicado;
- `run_id` y `version_modelo` permiten reconstruir la ejecucion exacta.

## 11.4. Eje GOVERNANÇA

Unidad de lectura: departamento de referencia (`codigo_departamento_ref`) dentro del scope del eje GOVERNANCA, con SIC canonico auxiliar solo como atributo de apoyo.

Orden recomendado de consulta:

1. `gold_governanca.fact_riesgo` para ver el resultado final por bloque;
2. `gold_governanca.fact_probabilidad_bloque` y `gold_governanca.fact_impacto_bloque` para abrir la explicacion por bloque;
3. `gold_governanca.fact_probabilidad` y `gold_governanca.fact_impacto` para bajar al detalle de reglas;
4. `gold_governanca.dim_regla` y `gold_governanca.dim_supuesto_modelo` para interpretar codigos, defaults y el remapeo del bloque 4000.

Lectura funcional minima de una fila GOVERNANCA:

- `codigo_departamento_ref` identifica el departamento publicado;
- `sic` queda como atributo auxiliar cuando el modelo necesita SIC canonico para resolver impacto;
- `bloque` indica si el resultado pertenece al riesgo 200 o 400;
- `probabilidad_final_num` e `impacto_final_num` muestran los niveles finales del bloque;
- `riesgo_final_num` expresa el nivel publicado;
- `run_id` y `version_modelo` permiten auditar la ejecucion exacta.

## 11.5. Regla practica de lectura

Si negocio quiere explicar un resultado sin abrir SQL de transformacion, la secuencia correcta es:

1. empezar por la fact final (`fact_riesgo`);
2. abrir la fact de bloque correspondiente (`fact_probabilidad_bloque` o `fact_impacto_bloque`);
3. bajar a la fact de detalle por regla (`fact_probabilidad` o `fact_impacto`);
4. cerrar la interpretacion con `dim_regla`, `dim_supuesto_modelo` y la ejecucion en `audit.gold_risk_run`.

Con esa secuencia, cualquier resultado Gold queda explicable sin ambiguedad funcional.

---

## 12. Conclusiones funcionales

El modelo vigente permite explicar el resultado a negocio de forma consistente en los 5 ejes, pero la lectura correcta debe distinguir tres cosas:

1. lo que esta medido con dato real;
2. lo que entra al resultado por default;
3. lo que entra al resultado por constante funcional.

La lectura correcta del modelo no es solo "que nivel dio", sino tambien:

- por que dio ese nivel;
- con que fuente se sostuvo;
- y si ese nivel viene de dato real o de una decision de continuidad.

Ese es el mapa funcional vigente del calculo Gold de riesgo.

---

## Referencias

- [VISION_GENERAL_APP_Y_MODELOS_RIESGO.md](VISION_GENERAL_APP_Y_MODELOS_RIESGO.md)
- [CATALOGO_FUNCIONAL_REGLAS_RIESGO_VIGENTE.md](CATALOGO_FUNCIONAL_REGLAS_RIESGO_VIGENTE.md)
- [ACTUALIZACION_GOLD_RIESGO_23APR2026.md](ACTUALIZACION_GOLD_RIESGO_23APR2026.md)
- [PLAN_IMPLEMENTACION_EJES_CULTURA_GOVERNANCA.md](PLAN_IMPLEMENTACION_EJES_CULTURA_GOVERNANCA.md)
- [ANALISIS_PROBABILIDAD_PUESTOS_FUENTES.md](ANALISIS_PROBABILIDAD_PUESTOS_FUENTES.md)
- [ANALISIS_MODELO_RIESGO_V31_CATALOGO_REGLAS.md](ANALISIS_MODELO_RIESGO_V31_CATALOGO_REGLAS.md)
- [gold_sic/CONTRATO_BI_GOLD_SIC_V2.md](gold_sic/CONTRATO_BI_GOLD_SIC_V2.md)
- [gold_sic/EXPLICACION_FUNCIONAL_FALTANTES_SIC.md](gold_sic/EXPLICACION_FUNCIONAL_FALTANTES_SIC.md)
- [../sql/25_CREATE_GOLD_LLDT.sql](../sql/25_CREATE_GOLD_LLDT.sql)
- [../sql/31_UPDATE_GOLD_SIC_NATIVE.sql](../sql/31_UPDATE_GOLD_SIC_NATIVE.sql)
- [../sql/61_CREATE_GOLD_CULTURA.sql](../sql/61_CREATE_GOLD_CULTURA.sql)
- [../sql/62_CREATE_GOLD_GOVERNANCA.sql](../sql/62_CREATE_GOLD_GOVERNANCA.sql)
- [../sql/48_CREATE_DIM_MODELO_RIESGO_REGLA.sql](../sql/48_CREATE_DIM_MODELO_RIESGO_REGLA.sql)
