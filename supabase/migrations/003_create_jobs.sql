-- Migration 003: Create jobs table

CREATE TABLE jobs (
  id                  uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id             uuid REFERENCES auth.users(id) NOT NULL,
  company_name        text,
  job_title           text,
  jd_raw_text         text NOT NULL,
  jd_keywords_json    jsonb DEFAULT '{}',
  ats_score_initial   numeric(5,2),
  ats_gap_json        jsonb DEFAULT '{}',
  created_at          timestamptz DEFAULT now()
);

-- Index for fast per-user job lookups
CREATE INDEX jobs_user_id_idx ON jobs (user_id);
