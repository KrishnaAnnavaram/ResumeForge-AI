"""LLM router — selects model based on task type."""
from careeros.config import get_settings

settings = get_settings()


def get_model(task: str) -> str:
    """
    Route tasks to appropriate model.
    Heavy generation tasks → sonnet, lightweight extraction → haiku.
    """
    heavy_tasks = {
        "resume_writer",
        "cover_letter_writer",
        "rewrite_planner",
    }
    light_tasks = {
        "jd_parser",
        "gap_analyzer",
        "critic",
        "feedback_interpreter",
    }
    if task in heavy_tasks:
        return settings.sonnet_model
    if task in light_tasks:
        return settings.haiku_model
    # Default to haiku for unknown tasks
    return settings.haiku_model
