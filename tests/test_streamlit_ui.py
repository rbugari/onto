"""End-to-end UI checks for Atlas, Nexo and Argos using Streamlit's headless AppTest."""
from __future__ import annotations

import os
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    from streamlit.testing.v1 import AppTest
except ImportError:  # pragma: no cover - streamlit only lives in the app virtualenv
    AppTest = None

from ontology_workbench.service import WorkbenchService
from ontology_workbench.storage import ProjectStore

EXAMPLE = ROOT_DIR / "docs" / "casos" / "ventas_distribuidas" / "input"
APP = str(ROOT_DIR / "streamlit_app.py")


@unittest.skipIf(AppTest is None, "streamlit no esta instalado en este interprete")
class StreamlitUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp_dir = TemporaryDirectory()
        cls.env = patch.dict(os.environ, {"ONTO_DATA_DIR": cls.temp_dir.name, "ONTO_LLM_PROVIDER": "disabled"})
        cls.env.start()
        cls.service = WorkbenchService(ProjectStore(Path(cls.temp_dir.name) / "projects"))
        cls.project_id = cls._build_full_project()
        cls.empty_project_id = cls.service.create_project("Proyecto vacio").id

    @classmethod
    def tearDownClass(cls) -> None:
        cls.env.stop()
        cls.temp_dir.cleanup()

    @classmethod
    def _build_full_project(cls) -> str:
        service = cls.service
        project = service.create_project("Distribuidora UI")
        service.update_assessment_scope(project.id, "cliente-ui", "comercial", "ventas", "Gerencia")
        erp = service.register_data_source(project.id, "ERP", "mariadb", "Sistemas")
        lake = service.register_data_source(project.id, "Lakehouse", "databricks", "Datos")
        service.register_data_source(project.id, "Presupuesto", "files")
        for source, filename in ((erp, "erp_mariadb.sql"), (lake, "lakehouse_databricks_columns.csv")):
            service.import_source_metadata_file(project.id, source.source_id, filename, (EXAMPLE / filename).read_bytes())
        service.add_use_case(project.id, "Margen por cliente", "¿Quién deja más margen?", "Comercial", "alta",
                             [erp.source_id, lake.source_id])
        for path in sorted((EXAMPLE / "documentation").glob("*.md")):
            service.upload_context_document(project.id, path.name, path.read_bytes(), "functional_docs", "text/markdown")
        service.scan_business_context(project.id)
        assessment = service.create_atlas_assessment(project.id, "cliente-ui", "comercial", "ventas")
        run_id = str(assessment["manifest"]["run_id"])
        draft = service.create_nexo_draft(project.id, run_id, source_authority="documentation")
        draft_id = str(draft["manifest"]["draft_id"])
        service.bulk_update_nexo_candidates(
            project.id, draft_id, [str(item["candidate_id"]) for item in draft["candidates"]],
            "approved", "Ana", "Negocio", "UI test",
        )
        service.publish_nexo_release(project.id, draft_id, "Ana", "Release UI")
        cls.pending_draft_id = str(
            service.create_nexo_draft(project.id, run_id, source_authority="documentation")["manifest"]["draft_id"]
        )
        return project.id

    def _app(self, area: str, project_id: str | None = None, reviewer: str = "", language: str = "es") -> AppTest:
        project_id = project_id or self.project_id
        app = AppTest.from_file(APP, default_timeout=60)
        app.session_state["ui-language"] = language
        app.session_state["selected_project_id"] = project_id
        app.session_state["project_context_ready"] = True
        app.session_state["project_context_project_id"] = project_id
        app.session_state["active_product_area"] = area
        app.session_state["reviewer-name"] = reviewer
        app.session_state["reviewer-role"] = "Responsable" if reviewer else ""
        if project_id == self.project_id:
            app.session_state[f"nexo-draft-select-{project_id}"] = self.pending_draft_id
        return app.run()

    def assertNoExceptions(self, app: AppTest) -> None:  # noqa: N802
        self.assertEqual([item.value for item in app.exception], [])

    def test_every_area_renders_for_full_and_empty_projects(self) -> None:
        for project_id in (self.project_id, self.empty_project_id):
            for area, title in (("Atlas", "Atlas"), ("Nexo", "Nexo"), ("Argos", "Argos"), ("Proyecto", "Proyecto")):
                with self.subTest(project=project_id, area=area):
                    app = self._app(area, project_id)
                    self.assertNoExceptions(app)
                    self.assertTrue(app.title[0].value.startswith(title))

    def test_context_gate_requires_opening_the_project(self) -> None:
        app = AppTest.from_file(APP, default_timeout=60)
        app.session_state["selected_project_id"] = self.project_id
        app.run()
        self.assertEqual(app.title[0].value, "Contexto de trabajo")
        next(button for button in app.button if button.label == "Abrir proyecto").click().run()
        self.assertNoExceptions(app)
        self.assertTrue(app.title[0].value.startswith("Atlas"))

    def test_language_selector_preserves_project_and_product(self) -> None:
        app = self._app("Atlas")
        app.selectbox(key="ui-language").set_value("en").run()
        self.assertNoExceptions(app)
        self.assertEqual(app.session_state["selected_project_id"], self.project_id)
        self.assertEqual(app.session_state["active_product_area"], "Atlas")
        self.assertIn("Assessment", app.radio[0].options[0])
        app.selectbox(key="ui-language").set_value("es").run()
        self.assertNoExceptions(app)
        self.assertEqual(app.session_state["active_product_area"], "Atlas")

    def test_english_screens_and_atlas_selection_survive_language_switch(self) -> None:
        for area, title in (("Atlas", "Atlas · Readiness assessment"), ("Nexo", "Nexo · Validate knowledge"),
                            ("Argos", "Argos · Business investigation"), ("Proyecto", "Project")):
            with self.subTest(area=area):
                app = self._app(area, language="en")
                self.assertNoExceptions(app)
                self.assertEqual(app.title[0].value, title)
                self.assertEqual(app.selectbox(key="ui-language").value, "en")
        app = self._app("Atlas", language="en")
        app.button_group(key=f"atlas-diagnosis-view-{self.project_id}").set_value("Cobertura explicativa").run()
        app.selectbox(key=f"atlas-coverage-kind-{self.project_id}").set_value("property").run()
        run_id = app.selectbox(key=f"atlas-run-{self.project_id}").value
        self.assertTrue(any(item.label == "Properties" for item in app.metric))
        app.selectbox(key="ui-language").set_value("es").run()
        self.assertNoExceptions(app)
        self.assertEqual(app.selectbox(key=f"atlas-run-{self.project_id}").value, run_id)
        self.assertEqual(app.selectbox(key=f"atlas-coverage-kind-{self.project_id}").value, "property")
        self.assertEqual(app.button_group(key=f"atlas-diagnosis-view-{self.project_id}").value, "Cobertura explicativa")
        self.assertTrue(any(item.label == "Propiedades" for item in app.metric))
        app.selectbox(key="ui-language").set_value("en").run()
        self.assertNoExceptions(app)
        self.assertEqual(app.button_group(key=f"atlas-diagnosis-view-{self.project_id}").value, "Cobertura explicativa")
        self.assertEqual(app.selectbox(key=f"atlas-coverage-kind-{self.project_id}").value, "property")

    def test_inferred_explanations_are_warned_in_both_languages(self) -> None:
        from ontology_workbench.models import Concept

        project = self.service.create_project("Inferencias UI")
        project.concepts = [Concept(id="pedidos", name="Pedidos", tags=["table"])]
        self.service.store.save_project(project)
        assessment = self.service.create_atlas_assessment(project.id, project.id, "ventas", project.id)
        coverage = assessment["explanatory_coverage"]
        coverage["inferred_explanations"] = [{"element_id": coverage["elements"][0]["element_id"],
            "aspect": "granularidad", "explanation": "Una fila por pedido, por confirmar.",
            "basis": "Conocimiento general del modelo.", "assumptions": ["No contiene lineas."],
            "validation_needed": ["Consultar al responsable."], "related_evidence": [],
            "origin": "model_inference", "model_contribution": "substantial", "review_status": "pending_review",
            "counts_as_documentary_support": False}]
        self.service.store.save_atlas_assessment(assessment)
        for language, warning in (("es", "Inferida en grado importante por el modelo"),
                                   ("en", "Substantially inferred by the model")):
            app = self._app("Atlas", project.id, language=language)
            app.button_group(key=f"atlas-diagnosis-view-{project.id}").set_value("Cobertura explicativa").run()
            self.assertNoExceptions(app)
            self.assertTrue(any(warning in item.value for item in app.warning))
            self.assertTrue(any(item.value == "Consultar al responsable." for item in app.text))
        self.assertEqual(coverage["groups"]["entity"]["counts"]["explained"], 0)

    def test_language_switch_preserves_active_tab(self) -> None:
        from onto_ui.i18n import EN, localized_tabs

        for labels in (["1. Alcance", "4. Diagnóstico"], ["Revisión de candidatos", "Comparar"],
                       ["Conversación", "Analistas"]):
            with self.subTest(labels=labels):
                state = {"active-tab": labels[1], "ui-language": "en"}
                with patch("onto_ui.i18n.st.session_state", state), patch("onto_ui.i18n.st.tabs") as tabs:
                    localized_tabs(labels, key="active-tab")
                    self.assertEqual(state["active-tab"], EN[labels[1]])
                    self.assertEqual(tabs.call_args.kwargs["default"], EN[labels[1]])
                    self.assertEqual(tabs.call_args.kwargs["on_change"], "rerun")
                    state["ui-language"] = "es"
                    localized_tabs(labels, key="active-tab")
                    self.assertEqual(state["active-tab"], labels[1])
                    self.assertEqual(tabs.call_args.kwargs["default"], labels[1])

    def test_language_switch_preserves_unsaved_form_values_and_reviewer(self) -> None:
        app = self._app("Atlas", reviewer="Revisor original")
        field_key = f"atlas-source-name-{self.project_id}"
        app.text_input(key=field_key).set_value("Sistema sin guardar")
        app.selectbox(key="ui-language").set_value("en").run()
        self.assertNoExceptions(app)
        self.assertEqual(app.text_input(key=field_key).value, "Sistema sin guardar")
        self.assertEqual(app.text_input(key="reviewer-name").value, "Revisor original")
        self.assertEqual(app.query_params["lang"], ["en"])
        app.selectbox(key="ui-language").set_value("es").run()
        self.assertEqual(app.text_input(key=field_key).value, "Sistema sin guardar")

    def test_translation_catalog_templates_and_literal_calls_are_complete(self) -> None:
        import ast
        from string import Formatter
        from onto_ui.i18n import EN

        def fields(message):
            return {(field, spec, conversion) for _, field, spec, conversion in Formatter().parse(message) if field is not None}

        for source, translated in EN.items():
            self.assertEqual(fields(source), fields(translated), source)
        for path in [ROOT_DIR / "streamlit_app.py", *sorted((ROOT_DIR / "onto_ui").glob("*.py"))]:
            if path.name == "i18n.py":
                continue
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "t" and node.args and isinstance(node.args[0], ast.Constant):
                    self.assertIn(node.args[0].value, EN, f"{path.name}:{node.lineno}")
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in {"LocalizedLabels", "localize_rows"}:
                    for child in ast.walk(node):
                        if isinstance(child, ast.Dict):
                            labels = child.values if node.func.id == "LocalizedLabels" else child.keys
                            for label in labels:
                                if isinstance(label, ast.Constant) and isinstance(label.value, str):
                                    self.assertIn(label.value, EN, f"{path.name}:{node.lineno}")

    def test_translation_preserves_business_text_and_does_not_modify_requests(self) -> None:
        from copy import deepcopy
        from onto_ui.i18n import request_text, t

        request = {"action": "request_evidence", "element_name": "Pedidos {sin traducir}", "missing_aspects": ["granularidad"],
                   "request": "Pedido original"}
        original = deepcopy(request)
        with patch("onto_ui.i18n.language", return_value="en"):
            self.assertEqual(t("Una cita de negocio {sin traducir}"), "Una cita de negocio {sin traducir}")
            self.assertIn("Request documentation explaining: grain", request_text(request))
            self.assertTrue(request_text(request).startswith("Pedidos {sin traducir}:"))
            self.assertEqual(request, original)

    def test_atlas_diagnosis_views_render(self) -> None:
        app = self._app("Atlas")
        self.assertNoExceptions(app)
        for view in ("Mapa entre sistemas", "Sistemas", "Informe", "Universo evaluable", "Brechas"):
            with self.subTest(view=view):
                app.button_group(key=f"atlas-diagnosis-view-{self.project_id}").set_value(view).run()
                self.assertNoExceptions(app)
        markdown = " ".join(item.value for item in app.markdown)
        self.assertIn("Fuentes", markdown)

    def test_atlas_context_views_render(self) -> None:
        app = self._app("Atlas")
        for view in ("kpis", "business_rules", "candidate_entities", "questions_for_workshop", "definitions"):
            with self.subTest(view=view):
                app.button_group(key=f"atlas-context-view-{self.project_id}").set_value(view).run()
                self.assertNoExceptions(app)

    def test_atlas_universe_exclusion_requires_reason_and_persists(self) -> None:
        from ontology_workbench.explanatory_scope import SCOPE_KEY

        project = self.service.create_project("Universo UI")
        source = self.service.register_data_source(project.id, "ERP", "mariadb")
        self.service.import_source_metadata_file(project.id, source.source_id, "erp_mariadb.sql",
                                                 (EXAMPLE / "erp_mariadb.sql").read_bytes())
        self.service.create_atlas_assessment(project.id, project.id, "default", project.id)
        app = self._app("Atlas", project.id)
        app.button_group(key=f"atlas-diagnosis-view-{project.id}").set_value("Universo evaluable").run()
        next(item for item in app.checkbox if item.label == "Incluir en el universo").uncheck()
        next(item for item in app.button if item.label == "Guardar alcance y generar diagnóstico").click().run()
        self.assertTrue(any("motivo" in item.value for item in app.error))
        next(item for item in app.text_input if item.label.startswith("Motivo del ajuste")).set_value("Fuera del piloto")
        next(item for item in app.button if item.label == "Guardar alcance y generar diagnóstico").click().run()
        self.assertNoExceptions(app)
        self.assertIn("Fuera del piloto", self.service.get_project(project.id).metadata[SCOPE_KEY])
        self.assertEqual(len(self.service.list_atlas_assessments(project.id)), 2)
        self.assertEqual(app.selectbox(key=f"atlas-run-{project.id}").value,
                 self.service.list_atlas_assessments(project.id)[0]["run_id"])
        options = app.selectbox(key=f"atlas-run-{project.id}").options
        self.assertEqual(len(options), len(set(options)))
        app.run()
        self.assertEqual(app.selectbox(key=f"atlas-run-{project.id}").value,
             self.service.list_atlas_assessments(project.id)[0]["run_id"])
        oldest = self.service.list_atlas_assessments(project.id)[-1]["run_id"]
        app.selectbox(key=f"atlas-run-{project.id}").set_value(oldest).run()
        self.assertNoExceptions(app)
        self.assertTrue(any("difiere del proyecto actual" in item.value for item in app.info))
        self.assertFalse(any(item.label == "Guardar alcance y generar diagnóstico" for item in app.button))

    def test_atlas_coverage_counts_and_evidence_render(self) -> None:
        from ontology_workbench.explanatory_coverage import build_explanatory_coverage
        from ontology_workbench.models import Concept

        project = self.service.create_project("Cobertura UI")
        project.concepts = [Concept(id=f"entity-{index}", name=f"Entidad {index}", tags=["table"])
                            for index in range(4)]
        self.service.store.save_project(project)
        self.service.upload_context_document(project.id, "definiciones.md",
            b"Significado confirmado. Una fila por pedido. Clave pedido_id. Definicion incompatible.",
            "functional_docs", "text/markdown")
        package = self.service.create_atlas_assessment(project.id, project.id, "default", project.id)
        scope = package["explanatory_scope"]
        chunks = self.service.store.load_context_chunks(project.id)
        quotes = {"significado": "Significado confirmado.", "granularidad": "Una fila por pedido.",
                  "identificacion": "Clave pedido_id."}
        decisions = []
        for index, row in enumerate(scope["elements"]):
            aspects = row["required_aspects"] if index in (0, 3) else row["required_aspects"][:1] if index == 1 else []
            decisions.append({"element_id": row["element_id"], "method": "controlled_fixture",
                              "supports": [{"aspect": aspect, "chunk_id": chunks[0]["chunk_id"], "quote": quotes[aspect]}
                                           for aspect in aspects]})
        decisions[3]["contradictions"] = [{"chunk_id": chunks[0]["chunk_id"],
            "quote": "Definicion incompatible.", "reason": "Contradiccion controlada", "material": True}]
        package["explanatory_coverage"] = build_explanatory_coverage(scope, chunks, decisions)
        path = self.service.store.save_atlas_assessment(package)
        app = self._app("Atlas", project.id)
        app.button_group(key=f"atlas-diagnosis-view-{project.id}").set_value("Cobertura explicativa").run()
        self.assertNoExceptions(app)
        self.assertEqual(next(item.value for item in app.metric if item.label == "Entidades"), "25%")
        self.assertEqual(next(item.value for item in app.metric if item.label == "KPIs"), "No evaluable")
        self.assertTrue(any(item.value == "Significado confirmado." for item in app.text))
        app.selectbox(key=f"atlas-coverage-element-{project.id}-entity").set_value(scope["elements"][3]["element_id"]).run()
        self.assertTrue(any(item.value == "Contradiccion controlada" for item in app.warning))
        app.multiselect(key=f"atlas-coverage-status-{project.id}").set_value(["contradictory"]).run()
        self.assertNoExceptions(app)
        self.assertEqual(next(item.value for item in app.metric if item.label == "Entidades"), "25%")
        self.assertTrue(any("Elementos visibles: 1 / 4" in item.value for item in app.caption))
        self.assertEqual(len(app.selectbox(key=f"atlas-request-{project.id}-entity").options), 1)
        self.assertTrue(any("confirmar" in item.value.lower() for item in app.caption if "Responsable propuesto" in item.value))
        self.assertTrue(any(item.value.startswith("Criterio de cierre:") for item in app.text))
        app.multiselect(key=f"atlas-coverage-aspects-{project.id}-entity").set_value(["identificacion"]).run()
        self.assertTrue(any("Sin elementos para estos filtros" in item.value for item in app.info))
        app.multiselect(key=f"atlas-coverage-status-{project.id}").set_value([]).run()
        self.assertTrue(any("Elementos visibles: 2 / 4" in item.value for item in app.caption))
        (path / "explanatory_coverage.json").unlink()
        app = self._app("Atlas", project.id)
        app.button_group(key=f"atlas-diagnosis-view-{project.id}").set_value("Cobertura explicativa").run()
        self.assertTrue(any("anterior a la matriz" in item.value for item in app.info))
        self.service.create_atlas_assessment(project.id, project.id, "default", project.id)
        app = self._app("Atlas", project.id)
        app.button_group(key=f"atlas-diagnosis-view-{project.id}").set_value("Cobertura explicativa").run()
        self.assertNoExceptions(app)
        self.assertEqual(next(item.value for item in app.metric if item.label == "Entidades"), "Sin evaluar")

    def test_atlas_comparison_renders_transitions_evidence_and_scope_change(self) -> None:
        from ontology_workbench.models import Concept
        from ontology_workbench.explanatory_coverage import build_explanatory_coverage
        from ontology_workbench.explanatory_scope import SCOPE_KEY

        project = self.service.create_project("Comparacion UI")
        project.concepts = [Concept(id="pedido", name="Pedidos", tags=["table"])]
        self.service.store.save_project(project)
        self.service.upload_context_document(project.id, "pedidos.md", b"Definicion de pedidos.", "functional_docs", "text/markdown")
        before = self.service.create_atlas_assessment(project.id, project.id, "default", project.id)
        app = self._app("Atlas", project.id)
        app.button_group(key=f"atlas-diagnosis-view-{project.id}").set_value("Comparación").run()
        self.assertTrue(any("dos diagnósticos" in item.value for item in app.info))
        after = self.service.create_atlas_assessment(project.id, project.id, "default", project.id)
        scope = after["explanatory_scope"]
        element_id = scope["elements"][0]["element_id"]
        chunk = self.service.store.load_context_chunks(project.id)[0]
        after["explanatory_coverage"] = build_explanatory_coverage(scope, [chunk], [{"element_id": element_id,
            "method": "controlled", "supports": [{"aspect": aspect, "chunk_id": chunk["chunk_id"], "quote": "Definicion de pedidos."}
                for aspect in scope["elements"][0]["required_aspects"]]}])
        self.service.store.save_atlas_assessment(after)
        app = self._app("Atlas", project.id)
        app.button_group(key=f"atlas-diagnosis-view-{project.id}").set_value("Comparación").run()
        self.assertNoExceptions(app)
        self.assertTrue(any("Inicial: **Sin evaluar**" in item.value and "Final: **100%**" in item.value for item in app.markdown))
        self.assertTrue(any("Análisis completado" in option for option in app.selectbox(key=f"atlas-compare-element-{project.id}").options))
        self.assertTrue(any(item.value == "Definicion de pedidos." for item in app.text))
        self.assertTrue(any("Resultados de pedidos" in item.value for item in app.subheader))
        project = self.service.get_project(project.id)
        project.metadata[SCOPE_KEY] = json.dumps({element_id: {"included": False, "reason": "Fuera del piloto"}})
        self.service.store.save_project(project)
        self.service.create_atlas_assessment(project.id, project.id, "default", project.id)
        app = self._app("Atlas", project.id)
        app.button_group(key=f"atlas-diagnosis-view-{project.id}").set_value("Comparación").run()
        self.assertNoExceptions(app)
        self.assertTrue(any("bases distintas" in item.value for item in app.warning))
        self.assertFalse(any(item.value.startswith("Diferencia:") for item in app.caption))

    def test_atlas_forms_register_source_and_use_case(self) -> None:
        project = self.service.create_project("Formularios Atlas")
        app = self._app("Atlas", project.id)
        app.text_input(key=f"atlas-source-name-{project.id}").input("CRM")
        app.selectbox(key=f"atlas-source-platform-{project.id}").set_value("sqlserver")
        app.button(key=f"atlas-source-submit-{project.id}").click().run()
        self.assertNoExceptions(app)
        sources = self.service.list_data_sources(project.id)
        self.assertEqual([(item.name, item.platform) for item in sources], [("CRM", "sqlserver")])

        # AppTest does not submit a second form after a st.rerun() triggered by the first one.
        app = self._app("Atlas", project.id)
        app.text_input(key=f"atlas-use-case-name-{project.id}").input("Pipeline")
        app.multiselect(key=f"atlas-use-case-sources-{project.id}").set_value([sources[0].source_id])
        app.button(key=f"atlas-use-case-submit-{project.id}").click().run()
        self.assertNoExceptions(app)
        use_cases = self.service.get_project(project.id).use_cases
        self.assertEqual([(item.name, item.source_ids) for item in use_cases], [("Pipeline", [sources[0].source_id])])

        app = self._app("Atlas", project.id)
        app.button(key=f"atlas-generate-{project.id}").click().run()
        self.assertNoExceptions(app)
        self.assertEqual(len(self.service.list_atlas_assessments(project.id)), 1)

    def test_atlas_semantic_action_success_and_provider_failure(self) -> None:
        from ontology_workbench.context_scanner import LlmSettings
        from ontology_workbench.models import Concept

        project = self.service.create_project("Contraste UI")
        project.concepts = [Concept(id="entity", name="Pedidos", tags=["table"])]
        self.service.store.save_project(project)
        self.service.upload_context_document(project.id, "pedidos.md",
            b"Pedidos de venta. Una fila por pedido. Clave pedido_id.", "functional_docs", "text/markdown")
        settings = LlmSettings(provider="ollama", model="controlled-fixture", api_key_present=False)

        def response(messages, configured):
            payload = json.loads(messages[1]["content"])
            chunk_id = payload["evidence"][0]["chunk_id"]
            quotes = {"significado": "Pedidos de venta.", "granularidad": "Una fila por pedido.", "identificacion": "Clave pedido_id."}
            return {"evaluations": [{"element_id": item["element_id"], "reason": "Respaldo controlado por aspecto.",
                "supports": [{"aspect": aspect, "chunk_id": chunk_id, "quote": quotes[aspect]} for aspect in item["required_aspects"]],
                "contradictions": []} for item in payload["elements"]]}

        with patch("ontology_workbench.service.load_llm_settings", return_value=settings), patch(
            "onto_ui.atlas.load_llm_settings", return_value=settings), patch(
            "ontology_workbench.explanatory_analysis.call_llm_json", side_effect=response) as provider:
            app = self._app("Atlas", project.id)
            app.button(key=f"atlas-semantic-evaluate-{project.id}").click().run()
            self.assertNoExceptions(app)
            self.assertEqual(next(item.value for item in app.metric if item.label == "Entidades"), "100%")
            self.assertTrue(any("Análisis completo" in item.value for item in app.caption))
            self.assertTrue(any("pendientes de revisión humana" in item.value for item in app.caption))
            self.assertEqual(provider.call_count, 1)
        self.service.upload_context_document(project.id, "nueva.md", b"Otra evidencia.", "functional_docs", "text/markdown")
        with patch("ontology_workbench.service.load_llm_settings", return_value=settings), patch(
            "onto_ui.atlas.load_llm_settings", return_value=settings), patch(
            "ontology_workbench.explanatory_analysis.call_llm_json", side_effect=RuntimeError("provider unavailable")):
            app = self._app("Atlas", project.id)
            app.button(key=f"atlas-semantic-evaluate-{project.id}").click().run()
            self.assertNoExceptions(app)
            self.assertTrue(any("Análisis con fallos" in item.value for item in app.caption))
            self.assertEqual(next(item.value for item in app.metric if item.label == "Entidades"), "Sin evaluar")
            coverage = self.service.get_atlas_assessment(project.id,
                self.service.list_atlas_assessments(project.id)[0]["run_id"])["explanatory_coverage"]
            self.assertEqual(coverage["groups"]["entity"]["failed"], 1)
            self.assertEqual(coverage["groups"]["entity"]["counts"]["unexplained"], 0)

    def test_atlas_semantic_disabled_is_visible_without_calls(self) -> None:
        with patch("ontology_workbench.explanatory_analysis.call_llm_json") as provider:
            app = self._app("Atlas", self.empty_project_id)
            app.button(key=f"atlas-semantic-evaluate-{self.empty_project_id}").click().run()
            self.assertNoExceptions(app)
            provider.assert_not_called()
            self.assertTrue(any("Proveedor no habilitado" in item.value for item in app.caption))

    def test_nexo_decision_requires_session_reviewer(self) -> None:
        draft = self.service.get_nexo_draft(self.project_id, self.pending_draft_id)
        candidate_id = next(str(item["candidate_id"]) for item in draft["candidates"] if item["status"] == "pending_review")
        button_key = f"nexo-decide-approved-{self.pending_draft_id}-{candidate_id}"

        app = self._app("Nexo")
        self.assertNoExceptions(app)
        app.button(key=button_key).click().run()
        self.assertTrue(any("Revisor/a de esta sesión" in item.value for item in app.warning))
        self._assert_candidate_status(candidate_id, "pending_review")

        app = self._app("Nexo", reviewer="Ana")
        app.button(key=button_key).click().run()
        self.assertNoExceptions(app)
        self._assert_candidate_status(candidate_id, "approved")

    def test_nexo_tabs_render_actions(self) -> None:
        app = self._app("Nexo", reviewer="Ana")
        app.button(key=f"nexo-consolidate-{self.pending_draft_id}").click().run()
        self.assertNoExceptions(app)
        app.button(key=f"nexo-propose-bindings-{self.pending_draft_id}").click().run()
        self.assertNoExceptions(app)
        app.button(key=f"nexo-diff-run-{self.pending_draft_id}").click().run()
        self.assertNoExceptions(app)
        self.assertTrue(any(item.label == "Agregados" for item in app.metric))

    def test_nexo_delivery_generates_platform_package(self) -> None:
        for target in ("fabric", "databricks"):
            with self.subTest(target=target):
                app = self._app("Nexo", reviewer="Ana")
                app.button_group(key=f"nexo-delivery-target-{self.pending_draft_id}").set_value(target).run()
                submit = next(button for button in app.button if button.label == "Generar paquete para la plataforma")
                submit.click().run()
                self.assertNoExceptions(app)
                metrics = {item.label: item.value for item in app.metric}
                self.assertIn("Ruta recomendada", metrics)
                self.assertTrue(any("Descargar paquete" in str(item.proto.label) for item in app.get("download_button")))

    def test_argos_chat_answers_and_abstains(self) -> None:
        app = self._app("Argos")
        self.assertNoExceptions(app)
        app.chat_input(key=f"argos-chat-input-{self.project_id}").set_value("¿Qué es Cliente activo?").run()
        self.assertNoExceptions(app)
        app.chat_input(key=f"argos-chat-input-{self.project_id}").set_value("¿Qué planeta es más grande?").run()
        self.assertNoExceptions(app)
        self.assertGreaterEqual(len(app.chat_message), 4)
        self.assertTrue(app.warning, "La abstención debe mostrarse como advertencia")

        app.button(key=f"argos-clear-{self.project_id}").click().run()
        self.assertNoExceptions(app)
        self.assertEqual(len(app.chat_message), 0)

    def test_argos_evaluation_battery(self) -> None:
        app = self._app("Argos")
        app.text_area(key=f"argos-evaluation-cases-{self.project_id}").input(
            "¿Qué es Cliente activo? | answered |\n¿Qué planeta es más grande? | abstained |"
        )
        app.button(key=f"argos-evaluation-run-{self.project_id}").click().run()
        self.assertNoExceptions(app)
        metrics = {item.label: item.value for item in app.metric}
        self.assertEqual(metrics["Casos"], "2")

        app.text_area(key=f"argos-evaluation-cases-{self.project_id}").input("Mal | quizas")
        app.button(key=f"argos-evaluation-run-{self.project_id}").click().run()
        self.assertTrue(any("Formato inválido" in item.value for item in app.error))

    def test_argos_without_release_explains_next_step(self) -> None:
        app = self._app("Argos", self.empty_project_id)
        self.assertNoExceptions(app)
        self.assertTrue(any("release" in item.value for item in app.info))

    def _assert_candidate_status(self, candidate_id: str, status: str) -> None:
        draft = self.service.get_nexo_draft(self.project_id, self.pending_draft_id)
        candidate = next(item for item in draft["candidates"] if str(item["candidate_id"]) == candidate_id)
        self.assertEqual(candidate["status"], status)


if __name__ == "__main__":
    unittest.main()
