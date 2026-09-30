# Decision de arquitectura MVP - Monolito web local

Fecha: 2026-08-13
Estado: decision vigente para el MVP operativo y su evolucion posterior
Decision: ONTO se construye inicialmente como una unica aplicacion web monolitica, local y orientada a PoC/MVP.

## Contexto

ONTO debe validar tres capacidades de producto: assessment, validacion/registry y Runtime investigador. La prioridad actual es confirmar que los contratos, los flujos de trabajo, los paquetes ontologicos y el valor para un dominio real son correctos.

En esta etapa, una arquitectura distribuida agregaria configuracion, despliegue, identidades, observabilidad, migraciones y puntos de fallo sin responder las preguntas de producto fundamentales. Tambien haria mas dificil que personas y asistentes de desarrollo automatico entiendan y cambien el sistema de forma segura.

## Decision

Se mantiene una unica aplicacion web basada en el enfoque local existente de Streamlit. La aplicacion se ejecuta como un solo proceso y concentra interfaz, logica de producto, conectores, prompts y persistencia local.

Los tres productos se diferencian por sus pantallas, modelos y archivos de salida, pero **no** por servicios desplegables distintos:

```text
streamlit_app.py              # entrada: proyecto, navegacion y administracion
onto_ui/                      # pantallas por producto
  atlas.py                    # Assessment
  nexo.py                     # Registry & Validation
  argos.py                    # Runtime / Investigador
src/ontology_workbench/       # modulos Python internos, no microservicios
data/                         # proyectos, contexto, workspaces, releases y ejecuciones JSON
prompts/                      # instrucciones versionadas
docs/                         # contratos y decisiones
.env                          # configuracion y credenciales locales, nunca versionadas
```

La separacion interna en modulos sigue siendo necesaria para que el codigo sea legible y testeable. Esa separacion no habilita procesos, APIs internas, colas ni despliegues independientes.

## Restricciones explicitas del MVP

| Decision | Regla |
| --- | --- |
| Ejecucion | Un unico proceso web local; el punto de entrada actual es Streamlit. |
| Persistencia | Carpetas bajo `data/` con JSON y manifests. SQLite es una opcion futura, no un requisito actual. |
| Configuracion | `.env` local y `.env.example`; no se almacenan secretos en JSON ni en las carpetas de datos. |
| Multiusuario | Fuera de alcance. Los roles de revision existen como dato de dominio, no como SSO/portal empresarial. |
| Conectores | Se invocan desde el monolito y solo con credenciales autorizadas en la maquina o sesion local. |
| LLM | Proveedor configurable por `.env`; las salidas se persisten con prompt/configuracion/evidencia para poder revisarlas. |
| Interoperabilidad | Fabric y Databricks se prueban como adaptadores puntuales, sin crear servicios de sincronizacion permanentes. |
| Despliegue | Sin contenedores, colas, API gateway, base de datos gestionada ni CI/CD obligatorio en esta etapa. |

## Estructura local de datos objetivo

Cada trabajo se organiza en carpetas para que una persona pueda inspeccionar el resultado sin infraestructura adicional. La raiz es `data/`, o la carpeta indicada en `ONTO_DATA_DIR` (la usan los tests de interfaz). La estructura efectiva actual es:

```text
data/
  projects/<project-id>.json          # incluye sistemas y casos de uso
  history/<project-id>/...            # snapshots
  context/<project-id>/...            # metadata tecnica importada y documentos
  workspaces/<client>/<domain>/<data-product>/runs/<run-id>/...   # diagnosticos Atlas
  registry/<project-id>/drafts|releases|comparisons/...
  connections/<project-id>/<profile-id>.env
  runtime/<project-id>/<release-id>/<investigation-id>/...
  interoperability/<project-id>/<release-id>/<target>/<package-id>/...
```

Los paquetes `assessment-package/` y `ontology-release/` son directorios exportables dentro de `output/`; su manifest permite moverlos o usarlos en otro entorno mas adelante.

## Consecuencias aceptadas

- La disponibilidad, concurrencia y retencion son las de una aplicacion local de PoC.
- El almacenamiento no es un sistema de registro empresarial ni un backend multiusuario.
- Las credenciales de conectores se gestionan manualmente para cada entorno de prueba.
- La migracion a una arquitectura superior sera una decision futura basada en uso real, no una premisa de diseno actual.

## Criterio para evolucionar la arquitectura

Solo se evaluara una evolucion a servicios, despliegue cloud, SSO, base de datos compartida o sincronizacion continua cuando se cumpla al menos una condicion concreta: piloto multiusuario aprobado, necesidad de operar para mas de un cliente en paralelo, requisito de disponibilidad/retencion formal, o integracion de plataforma que no pueda operar correctamente desde el monolito local.
