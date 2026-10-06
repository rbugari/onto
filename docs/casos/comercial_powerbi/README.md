# Caso: comercial con una sola fuente (Power BI)

| | |
| --- | --- |
| Tipo | Sintetico (sin datos reales) |
| Objetivo | Recorrer Atlas, Nexo, Argos y la entrega a Fabric con una sola fuente bien documentada |
| Ruta esperada | **A** en Fabric (todo implementable) |
| Regenerar | `python scripts/run_commercial_sales_demo.py` (agregar `--keep` para no borrar lo anterior) |

## Origenes

| Archivo | Que es |
| --- | --- |
| `input/model.bim` | Modelo semantico Power BI: 3 tablas, 9 columnas, 2 medidas |
| `input/documentation/01..05_*.md` | Glosario, KPIs, proceso pedido-factura, diccionario del modelo y preguntas frecuentes |

## Que cargar en Atlas (UI)

1. **Alcance**: cliente `demo-client`, dominio `commercial-sales`, producto `sales-analytics`. Casos de uso (de `05_preguntas_negocio_frecuentes.md`):
   - "Ventas netas" - Como se calculan las ventas netas? - Gerencia Comercial - alta.
   - "Clientes activos" - Que significa cliente activo? - Gerencia Comercial - media.
2. **Fuentes**: sistema "Modelo Power BI Ventas", plataforma Power BI, con responsable; importar `model.bim`.
3. **Contexto**: subir los 5 documentos y analizar.
4. **Diagnostico**: generar.

## Resultado esperado

Con el script (sin casos de uso ni responsables): **4,25 strong_foundation**.

| Dimension | Puntaje | Lectura |
| --- | --- | --- |
| Metadata tecnica | 5 | Cubierto |
| Contexto de negocio | 5 | Cubierto |
| Cruce tecnico-negocio | 3 | Casi |
| Gobierno y trazabilidad | 4 | Cubierto |

Brechas: faltan casos de uso (alcance), responsables (gobierno, dos brechas) y revision funcional (negocio). Cargando el caso completo desde la UI (pasos 1 y 2), las de alcance y responsable desaparecen.

## Despues de Atlas

- Nexo: 24 candidatos, release, paquete Fabric con ruta A (13/13).
- Argos: 1 consulta sintetica (`ventas del cliente 42`), abstencion fuera de catalogo, evaluacion 2/2.
