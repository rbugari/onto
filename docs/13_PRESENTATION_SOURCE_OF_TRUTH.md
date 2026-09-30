# Fuente de verdad para presentaciones

Estado: narrativa oficial del MVP operativo

## Elevator pitch

ONTO convierte evidencia tecnica y funcional existente en conocimiento ontologico gobernado, revisable y consumible por IA.

Version para publico no tecnico: "Lo que antes decidia y validaba una persona experta en datos (que significa cada dato, como se cruza y que se puede responder), ahora lo preparamos como contexto aprobado para que lo use una IA". Guion completo en la [guia paso a paso](GUIA_PASO_A_PASO_NO_TECNICA.md).

Mensaje obligatorio frente a Fabric y Databricks: "No competimos con su ontologia: hacemos el relevamiento, el cruce entre sistemas y la validacion que necesitan para implementarla. Solo cubrimos por nuestra cuenta lo que la plataforma no puede (plan B)".

## Problema

Los modelos, datos, catalogos y documentos de una organizacion contienen conocimiento, pero suelen estar dispersos, ser desiguales y no declarar con claridad que puede usar un agente, con que evidencia y dentro de que limites.

El caso mas frecuente y mas dificil es el dominio repartido en varios sistemas: la misma entidad tiene nombres y claves distintas en el ERP, el lakehouse, el modelo de BI y el CRM, y ninguna plataforma individual ve el dominio completo.

## Propuesta

ONTO ayuda a descubrir la evidencia de todos los sistemas del dominio, medir su readiness y sus cruces, convertirla en candidatos, someterla a revision humana y emitir una release portable para agentes y herramientas del cliente. En el MVP prepara paquetes que la plataforma importa (Fabric IQ, Databricks); no publica externamente.

## Productos

- Atlas: assessment de readiness multi-sistema ("te cuento como estas y que puede implementar tu plataforma").
- Nexo: registry, validacion y paquete para la plataforma ("que conocimiento esta aprobado y como se entrega").
- Argos: banco de prueba y runtime de plan B ("funciona de verdad; y cubrimos lo que la plataforma no puede").

## Ruta de implementacion

Ruta A (por defecto): la plataforma del cliente implementa todo. Ruta B (mixta): la plataforma implementa lo que puede y ONTO el resto. Ruta C: ONTO como plan B, solo si ninguna plataforma puede de forma viable. Todo deck debe mostrar este orden. El paquete de entrega de Nexo recomienda A, B o C segun que fuentes alcanza la plataforma. Datos fuera de la plataforma no implican C por si solos: puede haber un puente (copia o federacion).

## Arquitectura narrativa

ONTO usa un modelo intermedio portable para poder entregar a cualquier plataforma. Fabric, Databricks, Snowflake, SQL Server y otras plataformas pueden aportar datos, metadata o modelos semanticos. Fabric IQ Ontology, Databricks u otras herramientas son el destino preferido y el sistema de registro de la ontologia; ONTO solo lo es en el plan B.

## Demo oficial

La demo principal debe mostrar un dominio sintetico comercial: primero el dominio distribuido en cinco sistemas (Atlas) y despues el flujo completo con release y Argos. El piloto Fabric/SIC demuestra el mismo flujo sobre metadata y datos reales de solo lectura; el caso Nalub es una evidencia tecnica secundaria con MariaDB. La historia debe incluir sistemas repartidos, documentacion incompleta, gaps, revision humana, release aprobada, respuesta sustentada y abstencion.

## Limites que deben decirse

- ONTO no reemplaza el catalogo ni el gobierno de datos.
- ONTO no reemplaza la plataforma de datos.
- ONTO no aprueba inferencias automaticamente.
- ONTO no acepta SQL libre.
- Databricks y otras plataformas distintas de Fabric se inventarian por archivo exportado, no por conexion en vivo.
- El mapa entre sistemas es heuristico; las equivalencias las confirman los responsables.
- ONTO no publica cambios externos en el MVP; solo genera un paquete local que quedaria sujeto a release, mapping y autorizacion.
- El MVP es local, monolitico y no multiusuario.

## Control de versiones

Cada deck o demo debe indicar:

- commit o version de ONTO;
- documentos fuente utilizados;
- fecha de generacion;
- estado `draft`, `reviewed` o `approved`;
- dominio y datos utilizados.

Una promesa fuerte que no este respaldada por esta documentacion no debe aparecer en una presentacion.
