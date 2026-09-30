# ONTO explicado sin tecnicismos: paso a paso

Para: personas de negocio, gerencia, clientes y cualquiera que no trabaje en datos.

## La idea en una frase

**Antes, una persona experta en datos decidía qué significa cada dato, cómo se cruza y qué se puede responder. Ahora preparamos ese conocimiento para que lo use una IA, con personas aprobándolo.**

Lo que ONTO produce no son datos nuevos ni un tablero: produce **contexto**, es decir, el "manual de instrucciones" que una IA necesita para responder bien sobre tu negocio.

## Una comparación que todos entienden

Imaginá que entra una persona nueva a la empresa, muy inteligente pero que no conoce nada de tu negocio. Antes de dejarla responder preguntas de un cliente o de la gerencia, harías esto:

1. Le contás **para qué la contratamos**: qué preguntas va a tener que responder.
2. Le mostrás **dónde está la información**: el sistema de ventas, el de stock, las planillas de presupuesto.
3. Le das **el glosario y los manuales**: qué es un "cliente activo", cómo se calcula el margen.
4. Le explicás **cómo se relacionan las cosas**: "el cliente que ves en el sistema de ventas es el mismo que aparece en el CRM, pero con otro número".
5. Un responsable **revisa y aprueba** lo que aprendió: "esto está bien, esto no".
6. La dejás trabajar, pero con una regla: **si no sabe algo, lo dice; no inventa**.

Una IA necesita exactamente lo mismo. ONTO es la herramienta para prepararlo de forma ordenada y verificable.

## ¿Por qué hace falta?

Porque en casi todas las empresas ese conocimiento:

- está **repartido** en varios sistemas (el ERP, el CRM, el Excel de presupuesto, el tablero de Power BI);
- vive **en la cabeza de pocas personas**;
- tiene **nombres distintos** para lo mismo en cada sistema;
- **nunca fue aprobado** formalmente por nadie.

Si le das una IA a la empresa sin ese contexto, responde con seguridad cosas que pueden estar mal. El problema no es la IA: es que nadie le explicó el negocio.

## El paso a paso

ONTO tiene tres etapas. Cada una tiene un nombre, pero lo importante es qué se hace en cada una.

```text
  1. ATLAS            2. NEXO               3. ARGOS
  ¿Cómo estamos?  ->  ¿Qué aprobamos?   ->  ¿Qué podemos responder?
  (diagnóstico)       (validación)          (uso con IA)
```

### Etapa 1 · Atlas: "¿Cómo estamos?" (diagnóstico)

**Paso 1. Definir para qué lo queremos.**
Se eligen una o dos preguntas de negocio concretas. Ejemplo: "¿Qué clientes nos dejan más margen?".
*Quién participa:* alguien de negocio que sepa qué necesita saber.

**Paso 2. Listar los sistemas que tienen la información.**
Por ejemplo: sistema de ventas, lakehouse de datos, tablero Power BI, CRM, planillas de presupuesto. Para cada uno se anota quién es el responsable.
*Quién participa:* alguien de sistemas o datos.

**Paso 3. Subir la "estructura" de cada sistema.**
No se suben los datos (ni ventas, ni clientes, ni montos): solo **qué tablas y campos tiene** cada sistema, como el índice de un libro. El área de sistemas lo exporta en un archivo y se sube.
*Quién participa:* sistemas.

**Paso 4. Subir los documentos del negocio.**
Glosarios, definiciones de indicadores, procesos, manuales. Lo que exista, aunque esté incompleto.
*Quién participa:* negocio.

**Paso 5. Analizar.**
ONTO lee los documentos y detecta términos, definiciones, reglas e indicadores. También compara los sistemas entre sí y encuentra qué cosas aparecen en varios (por ejemplo, "cliente" está en el ERP, en el lakehouse y en Power BI).

**Paso 6. Obtener el diagnóstico.**
ONTO entrega un informe con:
- una **nota de 0 a 5** de qué tan preparado está el tema;
- la **lista de lo que falta**, ordenada por importancia. Ejemplos: "el CRM no tiene responsable", "no está la estructura del presupuesto", "las ventas no se pueden cruzar entre el lakehouse y Power BI porque no comparten un número común".

**Paso 7. Revisar el diagnóstico.**
Un responsable lo lee y confirma si refleja la realidad.

> **Resultado de la etapa 1:** sabemos con claridad qué tenemos, qué falta y qué hay que resolver antes de darle el tema a una IA. Muchas empresas se detienen acá y ya les sirve como diagnóstico.

### Etapa 2 · Nexo: "¿Qué aprobamos?" (validación)

**Paso 8. Revisar lo que ONTO propone.**
A partir del diagnóstico, ONTO arma una lista de "candidatos": definiciones, reglas, indicadores y relaciones. Cada uno muestra **de dónde salió** (qué documento o qué sistema).
*Quién participa:* referentes de negocio y de datos.

**Paso 9. Aprobar o rechazar, uno por uno.**
Es como corregir un examen: "esta definición de cliente activo está bien", "esta regla está vieja, la rechazo". Queda registrado **quién decidió y por qué**.

**Paso 10. Completar lo que falta.**
Se agregan relaciones y equivalencias que solo una persona sabe. Ejemplo: "la 'Cuenta' del CRM es el mismo 'Cliente' del ERP".

**Paso 11. Publicar una versión aprobada.**
Cuando todo tiene una decisión, se genera una **versión oficial** del conocimiento, como la versión 1.0 de un manual. Solo esa versión puede usar la IA.

> **Resultado de la etapa 2:** un "manual del negocio" aprobado por personas, con fecha, versión y responsables. Se puede llevar después a la plataforma que use la empresa (Microsoft Fabric, Databricks u otra).

### Etapa 3 · Argos: "¿Qué podemos responder?" (uso con IA)

**Paso 12. Hacer preguntas.**
Cualquier persona pregunta en lenguaje normal: "¿Cuántas ventas tiene el cliente 42?".

**Paso 13. Recibir respuestas con respaldo.**
La IA responde usando **solo** el manual aprobado y consultas autorizadas. Cada respuesta muestra de dónde sale.

**Paso 14. Aceptar el "no sé".**
Si la pregunta está fuera de lo aprobado, la IA **se niega a responder** en lugar de inventar. Eso es una virtud, no una falla.

**Paso 15. Probar antes de confiar.**
Se prepara una lista de preguntas de prueba ("esta la tiene que responder", "esta no") y se verifica que se comporte como se espera.

> **Resultado de la etapa 3:** una IA que responde sobre el negocio con respaldo y que sabe cuándo callarse.

## Resumen en una tabla

| Paso | Qué se hace | Quién | Qué se sube o se obtiene |
| --- | --- | --- | --- |
| 1 | Definir las preguntas de negocio | Negocio | Uno o dos casos de uso |
| 2 | Listar los sistemas y sus responsables | Sistemas | Lista de sistemas |
| 3 | Subir la estructura de cada sistema | Sistemas | Archivo con tablas y campos (sin datos) |
| 4 | Subir documentos del negocio | Negocio | Glosarios, manuales, indicadores |
| 5 | Analizar | ONTO | Términos, reglas y cruces detectados |
| 6 | Diagnóstico | ONTO | Nota, faltantes e informe |
| 7 | Revisar el diagnóstico | Responsable | Diagnóstico confirmado |
| 8-10 | Revisar, aprobar y completar | Negocio y datos | Decisiones registradas |
| 11 | Publicar versión aprobada | Responsable | Manual oficial del negocio |
| 12-15 | Preguntar y probar | Usuarios | Respuestas con respaldo o "no sé" |

## Lo que ONTO **no** hace

- No reemplaza los sistemas de la empresa ni los modifica.
- No copia los datos del negocio para armar el manual: trabaja con la estructura y los documentos.
- No aprueba nada sola: una IA puede proponer, pero decide una persona.
- No inventa respuestas: si no está aprobado, dice que no sabe.

## Preguntas frecuentes

**¿Es un tablero o un reporte?**
No. Es la preparación del conocimiento que después usan la IA, los tableros o las personas.

**¿Tenemos que tener todo en una misma plataforma?**
No, y ese es justamente el foco: ONTO arma la vista completa aunque la información esté repartida en varios sistemas.

**¿Hay que subir datos sensibles?**
No. Para el diagnóstico alcanza con la estructura de los sistemas (nombres de tablas y campos) y los documentos. Los datos reales solo se consultan en la etapa 3, con permisos de solo lectura y consultas aprobadas.

**¿Cuánto participa la gente del negocio?**
En tres momentos: al definir las preguntas (paso 1), al aportar documentos (paso 4) y al aprobar el conocimiento (pasos 8 a 11).

**¿Qué pasa si el diagnóstico da mal?**
Es el resultado más útil: dice exactamente qué ordenar antes de invertir en IA.

## Cómo contarlo en 30 segundos

> "Hoy, cuando alguien pregunta algo del negocio, una persona de datos sabe dónde buscar, qué significa cada número y qué no se puede afirmar. Ese conocimiento está en su cabeza. ONTO lo ordena, lo hace aprobar por los responsables y lo convierte en el contexto que necesita una IA para responder igual de bien, mostrando de dónde sale cada respuesta y diciendo 'no sé' cuando corresponde."

## Palabras que vas a escuchar

| Palabra | Qué significa |
| --- | --- |
| Contexto | El conocimiento que la IA necesita para entender el negocio: definiciones, reglas, relaciones y límites. |
| Ontología | El "manual del negocio" ordenado: qué cosas existen (cliente, pedido, producto) y cómo se relacionan. |
| Metadata | La estructura de un sistema (tablas y campos), no los datos. Como el índice de un libro. |
| Diagnóstico / assessment | El informe de la etapa 1: qué tan preparado está el tema y qué falta. |
| Brecha (gap) | Algo que falta o está mal y bloquea el uso con IA. |
| Candidato | Una definición o regla propuesta que todavía no fue aprobada. |
| Release / versión aprobada | La versión oficial del manual; lo único que usa la IA. |
| Abstención | Cuando la IA dice "no sé" porque la pregunta está fuera de lo aprobado. |

Para el detalle técnico: [Objetivo, alcance y foco](OBJETIVO_ALCANCE_Y_FOCO.md) y [MVP operativo](00_MVP_OPERATIVO.md).
