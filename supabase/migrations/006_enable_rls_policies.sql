-- Migration 006: Enable Row Level Security and create per-user policies

-- Enable RLS on every table
ALTER TABLE profiles          ENABLE ROW LEVEL SECURITY;
ALTER TABLE jobs              ENABLE ROW LEVEL SECURITY;
ALTER TABLE resumes           ENABLE ROW LEVEL SECURITY;
ALTER TABLE cover_letters     ENABLE ROW LEVEL SECURITY;
ALTER TABLE application_logs  ENABLE ROW LEVEL SECURITY;

-- profiles
CREATE POLICY "Users see own profiles"
  ON profiles FOR ALL
  USING (user_id = auth.uid());

-- jobs
CREATE POLICY "Users see own jobs"
  ON jobs FOR ALL
  USING (user_id = auth.uid());

-- resumes
CREATE POLICY "Users see own resumes"
  ON resumes FOR ALL
  USING (user_id = auth.uid());

-- cover_letters
CREATE POLICY "Users see own cover letters"
  ON cover_letters FOR ALL
  USING (user_id = auth.uid());

-- application_logs
CREATE POLICY "Users see own logs"
  ON application_logs FOR ALL
  USING (user_id = auth.uid());
