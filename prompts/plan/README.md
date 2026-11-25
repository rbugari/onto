# Prompts de ejecucion por fase (historico)

Estado: las fases F1 a F4 ya se ejecutaron (ver el estado en [docs/18_PLAN_REPOSICIONAMIENTO.md](../../docs/18_PLAN_REPOSICIONAMIENTO.md)); F5 es opcional y se decide despues del piloto. Estos prompts se conservan como referencia para repetir o retomar una fase.

Plan: [docs/18_PLAN_REPOSICIONAMIENTO.md](../../docs/18_PLAN_REPOSICIONAMIENTO.md).

Uso: lanzar un agente autonomo por fase, en orden, pasandole el contenido del archivo. Revisar la rama y el resumen antes de lanzar la siguiente.

| Archivo | Fase |
| --- | --- |
| `f1_foco_y_limpieza.md` | F1 |
| `f2_atlas_capa_y_viabilidad.md` | F2 |
| `f3_contenido_semantico.md` | F3 |
| `f4_formatos_estables.md` | F4 |
| `f5_importar_existente.md` | F5 (opcional) |

Cada prompt asume que el agente lee primero el plan y las reglas de la seccion "Reglas para el agente autonomo".
