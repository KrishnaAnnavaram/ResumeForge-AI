-- Migration 004: Create resumes and cover_letters tables

CREATE TABLE resumes (
  id              uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id         uuid REFERENCES auth.users(id) NOT NULL,
  job_id          uuid REFERENCES jobs(id) NOT NULL,
  version         integer NOT NULL DEFAULT 1,
  generated_text  text,
  ats_score_final numeric(5,2),
  pdf_url         text,
  is_active       boolean DEFAULT true,
  is_confirmed    boolean DEFAULT false,
  confirmed_at    timestamptz,
  embedding       vector(1536),
  created_at      timestamptz DEFAULT now()
);

-- ivfflat index for cosine-similarity search on resume embeddings
CREATE INDEX resumes_embedding_idx
  ON resumes USING ivfflat (embedding vector_cosine_ops);

-- Composite index: fast lookup of all versions for a given job
CREATE INDEX resumes_job_id_user_id_idx ON resumes (job_id, user_id);

-- ---------------------------------------------------------------

CREATE TABLE cover_letters (
  id               uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id          uuid REFERENCES auth.users(id) NOT NULL,
  resume_id        uuid REFERENCES resumes(id) NOT NULL,
  job_id           uuid REFERENCES jobs(id) NOT NULL,
  generated_text   text,
  soft_skills_used jsonb DEFAULT '[]',
  pdf_url          text,
  created_at       timestamptz DEFAULT now()
);

CREATE INDEX cover_letters_user_id_idx ON cover_letters (user_id);
