-- Migration 001: Enable pgvector extension
-- Must run before any table that uses vector columns

CREATE EXTENSION IF NOT EXISTS vector;
