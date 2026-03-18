"""SkillAlias model — canonical mapping for skill name normalization."""
import uuid
from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from careeros.database.base import Base, TimestampMixin


class SkillAlias(Base, TimestampMixin):
    __tablename__ = "skill_aliases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    alias: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    canonical: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)


# 50+ seed aliases for common terms
SKILL_ALIAS_SEEDS = [
    # AI/ML
    ("large language models", "LLMs", "AI/ML"),
    ("large language model", "LLMs", "AI/ML"),
    ("llm", "LLMs", "AI/ML"),
    ("generative ai", "GenAI", "AI/ML"),
    ("generative artificial intelligence", "GenAI", "AI/ML"),
    ("retrieval augmented generation", "RAG", "AI/ML"),
    ("retrieval-augmented generation", "RAG", "AI/ML"),
    ("natural language processing", "NLP", "AI/ML"),
    ("machine learning", "ML", "AI/ML"),
    ("deep learning", "Deep Learning", "AI/ML"),
    ("neural networks", "Neural Networks", "AI/ML"),
    ("transformer models", "Transformers", "AI/ML"),
    ("fine tuning", "Fine-tuning", "AI/ML"),
    ("fine-tuning llms", "Fine-tuning", "AI/ML"),
    ("vector database", "Vector DB", "AI/ML"),
    ("vector databases", "Vector DB", "AI/ML"),
    ("embedding models", "Embeddings", "AI/ML"),
    ("langchain", "LangChain", "AI/ML"),
    ("langgraph", "LangGraph", "AI/ML"),
    ("openai api", "OpenAI API", "AI/ML"),
    ("anthropic claude", "Claude", "AI/ML"),
    ("prompt engineering", "Prompt Engineering", "AI/ML"),
    # Cloud
    ("amazon web services", "AWS", "Cloud"),
    ("google cloud platform", "GCP", "Cloud"),
    ("google cloud", "GCP", "Cloud"),
    ("microsoft azure", "Azure", "Cloud"),
    ("azure cloud", "Azure", "Cloud"),
    ("aws lambda", "AWS Lambda", "Cloud"),
    ("amazon s3", "Amazon S3", "Cloud"),
    ("kubernetes", "Kubernetes", "Cloud"),
    ("k8s", "Kubernetes", "Cloud"),
    ("docker containers", "Docker", "Cloud"),
    ("containerization", "Docker", "Cloud"),
    # Languages
    ("python3", "Python", "Language"),
    ("python 3", "Python", "Language"),
    ("typescript", "TypeScript", "Language"),
    ("javascript", "JavaScript", "Language"),
    ("golang", "Go", "Language"),
    ("rust lang", "Rust", "Language"),
    # Frameworks
    ("fastapi", "FastAPI", "Framework"),
    ("django rest framework", "Django REST", "Framework"),
    ("react.js", "React", "Framework"),
    ("reactjs", "React", "Framework"),
    ("next.js", "Next.js", "Framework"),
    ("nextjs", "Next.js", "Framework"),
    ("node.js", "Node.js", "Framework"),
    ("nodejs", "Node.js", "Framework"),
    # Databases
    ("postgresql", "PostgreSQL", "Database"),
    ("postgres", "PostgreSQL", "Database"),
    ("mongodb", "MongoDB", "Database"),
    ("redis cache", "Redis", "Database"),
    ("elasticsearch", "Elasticsearch", "Database"),
    ("pgvector", "pgvector", "Database"),
    # Tools
    ("git version control", "Git", "Tool"),
    ("ci/cd pipelines", "CI/CD", "Tool"),
    ("github actions", "GitHub Actions", "Tool"),
    ("terraform", "Terraform", "Tool"),
    ("apache kafka", "Kafka", "Tool"),
    ("message queue", "Message Queue", "Tool"),
]
