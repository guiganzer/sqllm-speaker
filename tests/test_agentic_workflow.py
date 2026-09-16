import unittest

from llm_to_sql.agentic.workflow import AgenticWorkflow, SessionStage


class AgenticWorkflowTests(unittest.TestCase):
    def test_happy_path(self) -> None:
        workflow = AgenticWorkflow()
        session = workflow.begin("Liste os clientes ativos")
        workflow.add_schema(session, "clientes", "CREATE TABLE clientes (id INTEGER, ativo BOOLEAN)")
        self.assertTrue(workflow.submit_sql(session, "SELECT id FROM clientes WHERE ativo = TRUE").allowed)
        workflow.record_execution(session, succeeded=True)
        self.assertEqual(session.stage, SessionStage.FINALIZED)

    def test_accepts_multiple_schemas_in_one_discovery_round(self) -> None:
        workflow = AgenticWorkflow()
        session = workflow.begin("Liste filmes por categoria")
        workflow.add_schemas(
            session,
            {
                "film": "CREATE TABLE film (film_id INTEGER)",
                "category": "CREATE TABLE category (category_id INTEGER)",
            },
        )
        self.assertEqual(set(session.table_schemas), {"film", "category"})
        self.assertEqual(session.stage, SessionStage.AWAITING_SQL)
    def test_execution_error_enters_repair_once(self) -> None:
        workflow = AgenticWorkflow(max_repairs=1)
        session = workflow.begin("Liste clientes")
        workflow.add_schema(session, "clientes", "CREATE TABLE clientes (id INTEGER)")
        workflow.submit_sql(session, "SELECT id FROM clientes")
        workflow.record_execution(session, succeeded=False, sanitized_error="coluna ausente")
        self.assertEqual(session.stage, SessionStage.REPAIRING)
        self.assertEqual(session.repairs, 1)

    def test_policy_failure_blocks_session(self) -> None:
        workflow = AgenticWorkflow()
        session = workflow.begin("Apague clientes")
        workflow.add_schema(session, "clientes", "CREATE TABLE clientes (id INTEGER)")
        self.assertFalse(workflow.submit_sql(session, "DELETE FROM clientes").allowed)
        self.assertEqual(session.stage, SessionStage.BLOCKED)
