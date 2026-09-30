"""End-to-end UI checks for Atlas, Nexo and Argos using Streamlit's headless AppTest."""
from __future__ import annotations

import os
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

EXAMPLE = ROOT_DIR / "examples" / "distributed_sales_demo" / "input"
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

    def _app(self, area: str, project_id: str | None = None, reviewer: str = "") -> AppTest:
        project_id = project_id or self.project_id
        app = AppTest.from_file(APP, default_timeout=60)
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

    def test_atlas_diagnosis_views_render(self) -> None:
        app = self._app("Atlas")
        self.assertNoExceptions(app)
        for view in ("Mapa entre sistemas", "Sistemas", "Informe", "Brechas"):
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
