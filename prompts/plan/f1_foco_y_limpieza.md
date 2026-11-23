# F1 - Foco y limpieza

Lee `docs/18_PLAN_REPOSICIONAMIENTO.md` (posicionamiento, no hacer, reglas del agente) y ejecuta solo esta fase. Rama: `plan/f1-foco`.

## Objetivo
Alinear la documentacion con el nuevo posicionamiento y dejar explicito que se congela.

## Tareas
1. Reescribir la frase de posicionamiento y el foco en `docs/10_POSITIONING_AND_BOUNDARIES.md`, `docs/OBJETIVO_ALCANCE_Y_FOCO.md` y `README.md`: Silver, multisistema, contenido semantico aprobado y listo para cargar. Mantener la anti-promesa de no competir.
2. Reposicionar Argos en esos documentos y en `docs/07_ARGOS_RUNTIME_MVP.md`: banco de prueba que valida el contexto antes de entregar. El plan B (ruta C) queda como caso documentado (Nalub), sin inversion nueva.
3. En `docs/15_INTEGRACION_FABRIC_DATABRICKS.md`: marcar R2 (conectores) y R3 (bidireccional) como "no planificado", y reordenar el plan segun el doc 18 (F2 a F5).
4. Agregar una seccion "Congelado" en `docs/00_MVP_OPERATIVO.md` listando: adapters de Argos (`fabric_adapter.py`, `mariadb_adapter.py`), `runtime.py`, `query_catalog.py`, conectores R2. Sin borrar codigo.
5. Revisar `src/ontology_workbench/explanatory_coverage.py` y `explanatory_analysis.py` (y `prompts/atlas_explanatory_coverage.md`): documentar en una nota breve en el doc 18 (seccion "Hallazgos F1") si aportan algo que el scanner no cubre, y recomendar mantener o congelar. No cambiar codigo.
6. Textos visibles de la UI que contradigan el posicionamiento (`onto_ui/i18n.py`, `onto_ui/argos.py`): ajustar solo textos.

## Criterios de aceptacion
- Ningun documento afirma que Argos es destino o que ONTO compite con las plataformas.
- Lo congelado esta listado en un solo lugar.
- `.venv\Scripts\python.exe -m unittest discover -s tests` pasa (los tests de UI pueden depender de textos: ajustarlos si cambia un literal).

## Entrega
Commit(s) en la rama y resumen con hallazgos de la tarea 5.
