# ONTO: objetivo, alcance y foco

Fecha: 2026-09-30
Estado: documento de entrada. Resume para qué existe ONTO, qué problema resuelve, qué incluye hoy y qué no. El detalle está en los documentos numerados de esta carpeta. Versión sin tecnicismos: [Guía paso a paso](GUIA_PASO_A_PASO_NO_TECNICA.md).

## 1. Objetivo

ONTO convierte evidencia técnica y funcional existente en **conocimiento ontológico gobernado, revisable y consumible por IA**, y lo **entrega a la plataforma del cliente** (Microsoft Fabric, Databricks u otra) para que lo implemente en su propia ontología.

**ONTO no compite con la ontología de Fabric ni con la de Databricks. Hace el trabajo previo que esas plataformas necesitan**: relevar, cruzar, validar y aprobar el conocimiento del dominio, para que después se implemente allá.

Dicho de forma operativa: toma la metadata de los sistemas de un dominio (ERP, lakehouse, warehouse, modelos de BI, CRM, planillas) y su documentación de negocio, y produce:

1. un **diagnóstico** de qué tan preparado está ese dominio y de **qué se puede implementar en la plataforma destino**;
2. una **ontología aprobada por personas** y un **paquete para cargar en la plataforma** del cliente;
3. un **banco de prueba** que valida con preguntas reales que el contexto aprobado funciona, y que opera como **plan B** solo para lo que la plataforma no puede resolver.

## 1.1 Ruta de implementación: primero la plataforma, ONTO como plan B

| Ruta | Cuándo | Qué hace ONTO |
| --- | --- | --- |
| **A. Nativa (preferida)** | La plataforma del cliente puede alcanzar las fuentes y representar el conocimiento aprobado. | Entrega el paquete para implementarlo en Fabric IQ Ontology, Databricks u otra herramienta. La plataforma pasa a ser el sistema de registro. |
| **B. Mixta** | La plataforma cubre una parte, pero otra parte queda afuera (fuentes que no ve, reglas que no soporta, costo o gobierno). | La plataforma implementa lo que puede; ONTO sostiene solo el resto. Cada elemento declara dónde vive. |
| **C. Plan B (ONTO)** | Ninguna plataforma puede implementarlo de forma viable (dominio repartido en sistemas que ninguna alcanza, restricciones técnicas o de costo). | ONTO conserva la release y Argos responde sobre ella, con las mismas reglas de evidencia y abstención. |

La decisión se toma con evidencia en el diagnóstico de Atlas y se revisa en Nexo antes de emitir la release. La ruta por defecto es siempre la A.

## 2. El problema que resuelve

Un agente de IA no falla por falta de datos, sino por falta de **significado confiable**: qué es un "cliente activo", qué tabla lo representa, cómo se cruza entre sistemas, quién lo aprobó y qué no debe responder.

Ese conocimiento existe, pero está:

- **distribuido** en varios sistemas y plataformas (MariaDB, Databricks, Fabric, SQL Server, Power BI, planillas);
- **implícito** en modelos, nombres de columnas y documentos desiguales;
- **sin dueño ni aprobación** explícitos;
- **sin puntos de cruce declarados**: la misma entidad tiene nombres y claves distintas en cada sistema.

Cuando todo vive en una sola plataforma, sus herramientas nativas ayudan, pero igual necesitan que alguien releve, cruce y apruebe el conocimiento antes de cargarlo. Cuando el dominio está repartido, el problema crece: nadie tiene la vista completa y ninguna plataforma individual puede declararla. ONTO resuelve ese trabajo previo y lo deja listo para la plataforma.

## 3. Foco: qué hace distinto a ONTO

| Foco | Qué significa en la práctica |
| --- | --- |
| **Al servicio de la plataforma del cliente** | No reemplaza la ontología de Fabric ni la de Databricks: prepara y valida lo que después se implementa ahí. ONTO solo sostiene lo que la plataforma no puede (plan B). |
| **Dominio completo, no una plataforma** | Atlas inventaria todos los sistemas del dominio en un mismo proyecto y detecta qué entidades comparten, con qué clave se cruzan y dónde faltan equivalencias. |
| **Formato de trabajo portable** | El modelo intermedio de ONTO no depende de ninguna plataforma, para poder entregarlo a cualquiera de ellas mediante mappings. |
| **Evidencia antes que inferencia** | Cada elemento conserva su fuente (archivo, hash, fragmento, sistema). Un LLM puede proponer; solo una persona aprueba. |
| **Casos de uso primero** | El diagnóstico prioriza brechas según los casos de uso que el negocio declaró. |
| **Abstención como capacidad** | Argos se niega a responder fuera de la release aprobada y nunca ejecuta SQL libre. |
| **Simple de operar** | Una sola aplicación local, sin infraestructura adicional, pensada para equipos chicos y consultoría. |

## 4. Los tres productos

| Producto | Pregunta que responde | Usuario | Entrega |
| --- | --- | --- | --- |
| **Atlas** · Preparar evidencia | ¿Cómo estamos? ¿Qué sistemas, qué evidencia, qué falta, cómo se conectan y qué puede implementar la plataforma? | Analista técnico o funcional, consultor | Assessment package: alcance, casos de uso, inventario por sistema, mapa entre sistemas, score, brechas priorizadas, informe. |
| **Nexo** · Validar conocimiento | ¿Qué conocimiento aceptamos y cómo lo entregamos a la plataforma? | Responsable de gobierno, referente de negocio | Release aprobada y paquete de mapping para Fabric o Databricks (ruta A/B); `agent_context_pack` para el plan B. |
| **Argos** · Investigar el negocio | ¿El contexto aprobado responde bien las preguntas reales? | Usuario de negocio, analista | Banco de prueba antes de implementar en la plataforma; runtime de plan B para lo que la plataforma no cubre. |

```text
Sistemas + documentación ──► Atlas (diagnóstico) ──► Nexo (conocimiento aprobado) ──► Paquete para Fabric / Databricks  (ruta A, preferida)
                                                                 │
                                                                 ├──► Argos: prueba con preguntas reales
                                                                 └──► Argos: plan B solo para lo que la plataforma no cubre
```

## 5. Alcance actual (MVP operativo)

### Incluye

- Aplicación web local (Streamlit) con Atlas, Nexo y Argos como áreas separadas.
- **Varios sistemas por proyecto**, cada uno con plataforma, responsable, formato y hash.
- Carga de metadata por archivo exportado: DDL (`.sql`), `information_schema.columns` (CSV), `model.bim`, TMDL, PBIP. Sirve para Databricks, SQL Server, PostgreSQL, Snowflake, Oracle, MariaDB y planillas.
- Conexión directa de solo lectura a metadata de Microsoft Fabric.
- Casos de uso con pregunta de negocio, prioridad, responsable y sistemas involucrados.
- Diagnóstico determinista: score por dimensión (incluida alineación entre sistemas), brechas por sistema, entre sistemas y por caso de uso, e informe descargable.
- Revisión humana de candidatos, modelo canónico (propiedades, relaciones, sinónimos, restricciones, vínculos con fuentes), releases y comparación entre versiones.
- Paquetes de mapping locales para Fabric y Databricks (`ready_for_review`).
- Argos con consultas nombradas, parametrizadas y de solo lectura (Fabric, MariaDB, adapter sintético), abstención y evaluación.

### No incluye

- Descubrimiento remoto de Databricks u otras plataformas (se cargan por archivo exportado).
- Publicación o escritura en sistemas externos.
- SQL libre generado desde una pregunta.
- Aprobación automática de conocimiento.
- Usuarios, SSO, roles técnicos o multiusuario.
- Garantía de calidad de datos a nivel de filas.
- Reemplazo del catálogo, del gobierno de datos, de la plataforma del cliente ni de su ontología (Fabric IQ Ontology, Databricks u otra).
- Evaluación automática de viabilidad por plataforma: hoy la ruta A/B/C la decide el equipo con la evidencia del diagnóstico.

## 6. Cómo se usa en un proyecto

1. **Encuadre**: dominio, uno o dos casos de uso, sistemas involucrados, responsables y **plataforma destino** del cliente.
2. **Atlas**: registrar sistemas, cargar su metadata y la documentación, analizar contexto, generar y revisar el diagnóstico. Se identifica qué puede alcanzar la plataforma destino y qué no.
3. **Nexo**: aprobar o rechazar candidatos con evidencia, completar el modelo, emitir la release y **decidir la ruta** (A nativa, B mixta, C plan B).
4. **Argos**: probar con preguntas reales y con la batería de evaluación que el contexto aprobado responde bien, antes de implementarlo.
5. **Entrega**: generar el paquete para la plataforma destino y acompañar su implementación. ONTO solo queda operando lo que la plataforma no puede cubrir.

## 7. Cómo se mide el éxito

- Todos los sistemas del caso de uso están inventariados y tienen responsable.
- Las entidades compartidas entre sistemas tienen una clave o regla de cruce documentada.
- Cada elemento aprobado se rastrea hasta una fuente o una decisión humana.
- Argos responde con evidencia las preguntas del caso de uso y se abstiene en las que están fuera de alcance.
- La release puede reconstruirse desde sus manifiestos y mapearse a la plataforma destino.
- La mayor parte del conocimiento aprobado termina implementado en la plataforma del cliente; lo que queda en ONTO (plan B) está justificado por escrito.

## 8. Límites que siempre deben decirse

- El score es basal y determinista: orienta el trabajo, no certifica preparación productiva.
- El mapa entre sistemas es heurístico (nombres normalizados y claves): las equivalencias las confirman los responsables.
- Las definiciones extraídas por el scanner son candidatas hasta que una persona las aprueba.
- Los mappings hacia plataformas externas son paquetes locales; no se publican.

## 9. Glosario mínimo

| Término | Significado |
| --- | --- |
| Sistema / fuente técnica | Plataforma o base que aporta metadata (ERP, lakehouse, modelo BI, CRM, planilla). |
| Assessment package | Carpeta reproducible que produce Atlas en cada diagnóstico. |
| Brecha (gap) | Falta de evidencia, responsable, documentación o cruce que bloquea un caso de uso. |
| Candidato | Concepto, regla, KPI o activo técnico propuesto a partir de la evidencia, pendiente de decisión. |
| Release | Versión aprobada del conocimiento; la base del paquete para la plataforma y lo único que Argos puede usar. |
| Context pack | Subconjunto de la release preparado para un agente, con instrucción de abstención. |
| Ruta A / B / C | Dónde se implementa el conocimiento: en la plataforma del cliente (A), repartido entre plataforma y ONTO (B) o solo en ONTO como plan B (C). |
| Plano de datos / plano ontológico | Dónde se leen metadata y datos, frente a dónde se conserva o publica la ontología. |

## 10. Documentos relacionados

- [MVP operativo](00_MVP_OPERATIVO.md): cómo trabajar hoy con la release local.
- [PRD](02_PRD_ONTOLOGY_FACTORY.md): requisitos, contratos y métricas.
- [Atlas](05_ATLAS_ASSESSMENT_MVP.md), [Nexo](06_NEXO_REGISTRY_MVP.md), [Argos](07_ARGOS_RUNTIME_MVP.md): detalle por producto.
- [Posicionamiento y límites](10_POSITIONING_AND_BOUNDARIES.md): mensaje público y anti-promesas.
- [Demo end-to-end](12_DEMO_END_TO_END.md): guiones reproducibles.
