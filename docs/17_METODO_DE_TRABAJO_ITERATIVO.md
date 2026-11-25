# Metodo de trabajo iterativo de ONTO

Estado: implementado en el discovery simple y en la revision Nexo.

## Principio

**Los insumos se versionan, las propuestas pendientes se pueden rehacer y las decisiones humanas no se reinician.**

Un proyecto representa un ambito de conocimiento que puede crecer con nuevas fuentes. No es necesario crear un proyecto por cada ejecucion. Proyectos de ambitos independientes deben mantenerse separados.

ONTO distingue cuatro cosas:

1. Insumos activos: estructura y documentos disponibles para interpretar el negocio.
2. Version de trabajo activa: conocimiento decidido mas propuestas pendientes.
3. Historial: versiones anteriores, conservadas para consulta y comparacion.
4. Releases: paquetes aprobados, inmutables; regenerar la propuesta no altera una release existente.

La continuidad es incremental respecto del conocimiento y sus decisiones. La sintesis vuelve a leer **todos los insumos activos**, no solamente el ultimo archivo. No se promete procesamiento incremental ni ahorro de llamadas al proveedor.

## Primera ejecucion

1. Crear o abrir un proyecto, indicar el ambito y cargar los archivos disponibles en Atlas.
2. Generar borrador de ontologia.
3. Revisar los nucleos propuestos, entidades principales y secundarias, reglas y preguntas.
4. Abrir Revisar y validar para trabajar sobre ese mismo borrador en Nexo.
5. Aprobar o rechazar con un revisor identificado. Escribir un motivo, especialmente al rechazar: un duplicado no significa lo mismo que una interpretacion incorrecta.

Al generarse correctamente, el borrador pasa a ser la version de trabajo activa. Todo conocimiento nuevo comienza pendiente. Las preguntas analiticas son posibilidades sujetas a los faltantes indicados, no consultas ejecutadas ni respuestas verificadas.

## Siguientes ejecuciones

| Operacion | Cuando usarla | Resultado |
| --- | --- | --- |
| Actualizar propuesta | Corregir o completar informacion, responder dudas o rehacer pendientes. | Regenera propuestas sobre los insumos vigentes y conserva decisiones previas. |
| Ampliar alcance | Agregar documentos, otro sistema o una parte adicional del negocio del mismo proyecto. | Aplica la misma continuidad sobre el conjunto ampliado y propone nuevos conceptos y conexiones. |
| Empezar de cero | Descartar explicitamente la herencia de decisiones en la nueva version de trabajo. | Exige confirmacion; genera todo pendiente, conservando archivos, versiones anteriores y releases. |

Actualizar y ampliar usan la misma politica de reconciliacion. La diferencia es la intencion del trabajo y los insumos incorporados, no una fusion automatica de ontologias independientes.

En proyectos anteriores a este metodo, la primera actualizacion permite elegir la **Base de conocimiento** entre los borradores existentes. Elegir el que contiene las decisiones que se quiere continuar; no se fusionan automaticamente decisiones de ramas distintas. Si esa base tiene identidades duplicadas ambiguas, primero consolidarlas en Nexo o elegir otra base. A partir de la primera actualizacion correcta, el proyecto tiene una version activa explicita y las anteriores quedan de solo lectura.

## Que ocurre con cada estado

| Estado de la base | Resultado de la nueva sintesis | Tratamiento |
| --- | --- | --- |
| Aprobado | Sin cambios de contenido ni contexto relevante. | Conserva su aprobacion, identidad y decision. |
| Aprobado | Cambia definicion, vinculacion o fuentes relevantes. | Conserva lo aprobado y agrega una propuesta de cambio pendiente. |
| Rechazado | La misma propuesta, incluso con otra redaccion, sin nueva evidencia relevante. | Mantiene el rechazo y su motivo. |
| Rechazado | Cambia la evidencia contextual relevante. | Mantiene el rechazo y presenta una reconsideracion pendiente. |
| Pendiente | Vuelve a proponerse o cambia. | Se regenera; la version anterior queda en el historial. |
| Pendiente | No aparece nuevamente. | Sale de la version activa, salvo que sea necesario para conservar un vinculo decidido. |
| Decidido | No aparece nuevamente. | Se conserva. La omision del modelo no autoriza borrado ni retiro. |
| Nuevo | No tiene correspondencia segura en la base. | Entra pendiente, sin aprobacion heredada. |

La politica se aplica a entidades, reglas, propiedades, relaciones y elementos manuales decididos. Una propiedad se identifica en el contexto de su entidad; una relacion incluye sus extremos y direccion. No se hereda una aprobacion solo porque coincida un nombre.

Los cambios rechazados tambien se recuerdan: una reformulacion sin evidencia nueva no vuelve a abrir la misma discusion. El revisor puede reabrir explicitamente una decision en la version activa; el modelo no lo hace por su cuenta. Un rechazo por duplicado conserva su nota y su referencia al concepto canonico; no se convierte en una exclusion general del negocio.

## Revisar un cambio en Nexo

1. Seleccionar la version de trabajo activa. Las anteriores muestran un aviso de solo lectura y permiten consultar y comparar, no editar ni publicar una nueva release desde ellas.
2. Una propuesta de cambio o reconsideracion muestra la definicion vigente, la decision anterior, su motivo si existe y la nueva propuesta.
3. Aprobar la propuesta aplica el cambio al elemento canonico, conservando su identificador y registrando el antes/despues y la decision humana.
4. Rechazar la propuesta mantiene intacto el elemento anterior. Dejarla pendiente tampoco cambia lo vigente.

Las propuestas de cambio se muestran aun si afectan entidades secundarias. Los contadores de Nexo incluyen todas las decisiones activas; no se puede emitir una release mientras haya cambios o elementos pendientes. Las releases ya emitidas no se reescriben.

## Incorporar informacion y respuestas

- Archivo nuevo: suma contexto al mismo proyecto.
- Mismo nombre y contenido: no duplica la carga.
- Nueva version del mismo archivo: reemplaza su version activa; se conservan los archivos originales y la evidencia historica.
- Respuesta a una pregunta de negocio o tecnica: incorporarla como documento, con responsable, fecha, ambito y la aclaracion aportada; luego actualizar la propuesta. No es necesario crear un proyecto nuevo.
- Una pregunta analitica no se agrega automaticamente al catalogo aprobado de Argos. Primero deben completarse sus faltantes y validarse sus definiciones y vinculos.

El LLM recibe las decisiones aprobadas y rechazadas, sus motivos y vinculaciones. Puede proponer correspondencias mediante un identificador previo; un renombrado se presenta como cambio pendiente, no como equivalencia aprobada. Si no existe correspondencia segura, el elemento queda como nuevo para revision humana.

## Historial, fallos y limites

- Cada generacion correcta guarda otra version y cambia el puntero activo; no borra el borrador anterior.
- El historial se consulta desde Draft en revision; Abrir version activa regresa al trabajo actual. No hay restauracion automatica de conocimiento ni de archivos al consultar una version anterior.
- Si falla la sintesis, validacion o reconciliacion, la version activa y sus decisiones siguen vigentes. Los archivos ya incorporados permanecen disponibles y pueden requerir una nueva generacion; no se revierte la carga.
- Si cambia la base revisada durante la generacion, se rechaza el resultado desactualizado y se solicita reintentar. Es un control optimista local, no un sistema distribuido de ramas o transacciones.
- El presupuesto serializado es de 90.000 caracteres para fuentes y estructura y otros 90.000 para el contexto de decisiones, mas el envoltorio JSON y el prompt. No se truncan silenciosamente las fuentes o decisiones. Un proveedor con menor capacidad puede rechazar la solicitud; ese fallo no autoriza a perder decisiones.
- Los fingerprints son conservadores: una variacion contextual puede generar un cambio pendiente aunque el revisor finalmente concluya que el significado no cambio. La existencia de referencias no prueba la interpretacion.
- Este metodo no cambia la base legacy, no consulta filas por si solo, no aprueba automaticamente ni publica en plataformas externas.

## Ejemplo de continuidad

Se aprueban Cliente y Pedido, se rechaza una interpretacion de deuda y queda pendiente Stock disponible. Luego se incorpora un manual de cobranza:

1. Elegir Ampliar alcance y cargar el manual en el mismo proyecto.
2. Cliente y Pedido permanecen aprobados si no hay cambios relevantes.
3. Stock disponible se vuelve a proponer con el conjunto de informacion vigente.
4. La interpretacion de deuda solo se reconsidera si el manual aporta nuevo contexto relevante para ella.
5. Cualquier concepto nuevo entra pendiente. Un cambio a Pedido se revisa por separado, sin alterar la definicion aprobada hasta su aceptacion.
6. La version anterior sigue consultable y cualquier release existente permanece igual.