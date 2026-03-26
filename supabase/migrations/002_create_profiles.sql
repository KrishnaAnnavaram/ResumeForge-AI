-- Migration 002: Create profiles table

CREATE TABLE profiles (
  id          uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id     uuid REFERENCES auth.users(id) UNIQUE NOT NULL,
  full_name   text,
  email       text,
  phone       text,
  linkedin_url          text,
  raw_resume_text       text,
  skills_json           jsonb DEFAULT '[]',
  soft_skills_json      jsonb DEFAULT '[]',
  experience_json       jsonb DEFAULT '[]',
  education_json        jsonb DEFAULT '[]',
  certifications_json   jsonb DEFAULT '[]',
  master_resume_url     text,
  embedding             vector(1536),
  created_at  timestamptz DEFAULT now(),
  updated_at  timestamptz DEFAULT now()
);

-- ivfflat index for fast cosine-similarity search on profile embeddings
CREATE INDEX profiles_embedding_idx
  ON profiles USING ivfflat (embedding vector_cosine_ops);

-- Automatically keep updated_at current
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER profiles_updated_at
  BEFORE UPDATE ON profiles
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
