"""Vault API schemas."""
from datetime import date
from pydantic import BaseModel


class ProfileUpdate(BaseModel):
    full_name: str | None = None
    headline: str | None = None
    summary: str | None = None
    location: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
    target_roles: list[str] | None = None
    target_domains: list[str] | None = None
    tone_preferences: dict | None = None


class ProfileResponse(BaseModel):
    id: str
    full_name: str
    headline: str | None
    summary: str | None
    location: str | None
    linkedin_url: str | None
    github_url: str | None
    portfolio_url: str | None
    target_roles: list[str]
    target_domains: list[str]
    tone_preferences: dict


class ExperienceCreate(BaseModel):
    company: str
    title: str
    employment_type: str | None = None
    start_date: date
    end_date: date | None = None
    is_current: bool = False
    location: str | None = None
    domain: str | None = None
    description: str | None = None


class ExperienceResponse(BaseModel):
    id: str
    company: str
    title: str
    employment_type: str | None
    start_date: str
    end_date: str | None
    is_current: bool
    location: str | None
    domain: str | None
    description: str | None


class BulletCreate(BaseModel):
    content: str
    metrics: list[str] = []
    skills_used: list[str] = []
    impact_level: str = "medium"


class BulletResponse(BaseModel):
    id: str
    content: str
    metrics: list[str]
    skills_used: list[str]
    impact_level: str
    usage_count: int


class SkillCreate(BaseModel):
    name: str
    category: str | None = None
    proficiency: str = "proficient"
    years_used: float | None = None


class SkillResponse(BaseModel):
    id: str
    name: str
    category: str | None
    proficiency: str
    years_used: float | None


class VaultHealthResponse(BaseModel):
    completeness_score: float
    warnings: list[str]
    has_summary: bool
    experiences_count: int
    skills_count: int
    has_master_resume: bool
