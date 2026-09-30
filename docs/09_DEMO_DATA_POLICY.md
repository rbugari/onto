# Politica de datos demo

Estado: vigente para el MVP operativo local y sus demos Risk/Ventas

## Objetivo

ONTO debe demostrar capacidades de preparacion ontologica sin versionar datos reales de clientes ni documentacion interna sensible.

## Reglas

- No versionar datos personales, transacciones reales, credenciales, secretos ni documentacion confidencial.
- Los artefactos operativos de ejecuciones locales viven fuera del conjunto de ejemplos publicables.
- Los ejemplos compartidos deben estar bajo `examples/` o en `data/samples/` y ser dummy, sinteticos o anonimizados con autorizacion.
- La metadata real solo puede usarse si fue autorizada, minimizada y revisada para no exponer informacion sensible.
- Una demo externa debe preferir un modelo sintetico inspirado en el dominio, no una copia de datos reales.
- Las salidas de Atlas, Nexo, Argos y conectores no se consideran automaticamente material de demo.

## Clasificacion

| Categoria | Ubicacion | Politica |
| --- | --- | --- |
| Codigo y contratos | raiz, `src/`, `tests/` | Versionable |
| Documentacion de producto | `docs/` | Versionable y revisable |
| Ejemplos sinteticos | `examples/`, `data/samples/` | Versionable despues de revision |
| Ejecuciones locales | `data/workspaces/`, `data/context/`, `data/registry/`, `data/runtime/` | No versionar por defecto |
| Credenciales y configuracion local | `.env`, `data/connections/`, registros de autenticacion | Nunca versionar |
| Deliverables generados | `deliverables/` | Versionar solo si son derivados aprobados |

## Limpieza y respuesta

Si se detecta material sensible:

1. detener su distribucion;
2. identificar commits, archivos y posibles secretos;
3. retirar el archivo del estado actual;
4. limpiar la historia con `git filter-repo` o una herramienta equivalente si corresponde;
5. rotar credenciales expuestas;
6. documentar la decision y validar que no queden copias en artefactos derivados.

`.gitignore` evita nuevas incorporaciones, pero no elimina archivos ya versionados. La clasificacion y la limpieza historica requieren una revision explicita.
