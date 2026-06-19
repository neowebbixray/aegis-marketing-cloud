"""AI agent execution tasks."""
from app.tasks import celery_app


@celery_app.task(bind=True, max_retries=3)
def execute_agent(self, agent_id: str, input_data: dict) -> dict:
    """Execute an AI agent with given input."""
    from app.services.ai import execute_agent

    return execute_agent(agent_id=agent_id, input_data=input_data)


@celery_app.task(bind=True, max_retries=3)
def index_knowledge_document(self, document_id: str) -> bool:
    """Index a knowledge document for RAG."""
    from app.services.ai import index_document

    return index_document(document_id=document_id)
