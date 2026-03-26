import { create } from "zustand";
import type { AtsGap, JdKeywords } from "../lib/api";

type Screen = "jd" | "ats" | "resume" | "cover" | "logs";

interface AppStore {
  // Navigation
  runId: string | null;
  currentScreen: Screen;
  userId: string | null;
  jobId: string | null;

  // ATS state
  atsScore: number | null;
  atsGap: AtsGap | null;
  jdKeywords: JdKeywords | null;

  // Resume state
  resumeText: string | null;
  resumeVersion: number | null;
  resumeId: string | null;
  resumePdfUrl: string | null;

  // Cover letter state
  coverLetterText: string | null;
  coverLetterId: string | null;

  // Job context
  companyName: string;
  jobTitle: string;

  // Actions
  setRunId: (id: string) => void;
  setScreen: (screen: Screen) => void;
  setUserId: (id: string | null) => void;
  setJobId: (id: string) => void;
  setAtsState: (score: number, gap: AtsGap, keywords: JdKeywords) => void;
  setResumeState: (text: string, version: number, id: string) => void;
  setCoverLetterState: (text: string, id: string) => void;
  setJobContext: (company: string, title: string) => void;
  reset: () => void;
}

const initialState = {
  runId: null,
  currentScreen: "jd" as Screen,
  userId: null,
  jobId: null,
  atsScore: null,
  atsGap: null,
  jdKeywords: null,
  resumeText: null,
  resumeVersion: null,
  resumeId: null,
  resumePdfUrl: null,
  coverLetterText: null,
  coverLetterId: null,
  companyName: "",
  jobTitle: "",
};

export const useAppStore = create<AppStore>((set) => ({
  ...initialState,

  setRunId: (id) => set({ runId: id }),
  setScreen: (screen) => set({ currentScreen: screen }),
  setUserId: (id) => set({ userId: id }),
  setJobId: (id) => set({ jobId: id }),

  setAtsState: (score, gap, keywords) =>
    set({ atsScore: score, atsGap: gap, jdKeywords: keywords }),

  setResumeState: (text, version, id) =>
    set({ resumeText: text, resumeVersion: version, resumeId: id }),

  setCoverLetterState: (text, id) =>
    set({ coverLetterText: text, coverLetterId: id }),

  setJobContext: (company, title) =>
    set({ companyName: company, jobTitle: title }),

  reset: () => set(initialState),
}));
