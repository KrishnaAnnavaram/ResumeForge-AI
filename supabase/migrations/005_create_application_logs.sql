-- Migration 005: Create application_logs table

CREATE TABLE application_logs (
  id               uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id          uuid REFERENCES auth.users(id) NOT NULL,
  job_id           uuid REFERENCES jobs(id) NOT NULL,
  resume_id        uuid REFERENCES resumes(id) NOT NULL,
  cover_letter_id  uuid REFERENCES cover_letters(id),   -- nullable: user may skip cover letter
  applied          boolean DEFAULT false,
  applied_on       date,
  feedback_rating  smallint CHECK (feedback_rating BETWEEN 1 AND 5),
  feedback_notes   text,
  logged_at        timestamptz DEFAULT now()
);

CREATE INDEX application_logs_user_id_idx ON application_logs (user_id);
