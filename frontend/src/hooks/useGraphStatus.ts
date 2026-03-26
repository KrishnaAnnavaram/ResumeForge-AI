import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { useAppStore } from "../store/appStore";

const POLL_INTERVAL_MS = 2000;

/**
 * useGraphStatus — polls /api/graph/status/{run_id} every 2s.
 *
 * On interrupt → updates Zustand state and navigates to the correct screen.
 * On complete → navigates to /logs.
 * On error → stops polling.
 */
export function useGraphStatus() {
  const runId = useAppStore((s) => s.runId);
  const setAtsState = useAppStore((s) => s.setAtsState);
  const setResumeState = useAppStore((s) => s.setResumeState);
  const setCoverLetterState = useAppStore((s) => s.setCoverLetterState);
  const setJobId = useAppStore((s) => s.setJobId);
  const setScreen = useAppStore((s) => s.setScreen);

  const navigate = useNavigate();
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const isPollingRef = useRef(false);

  const stopPolling = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    isPollingRef.current = false;
  };

  useEffect(() => {
    if (!runId) return;

    isPollingRef.current = true;

    const poll = async () => {
      if (!isPollingRef.current) return;
      try {
        const data = await api.graph.status(runId);
        const { status, interrupt_node, state } = data;

        // Update Zustand with latest state values
        if (state.job_id) setJobId(state.job_id);
        if (state.ats_score !== undefined && state.ats_gap && state.jd_keywords) {
          setAtsState(state.ats_score, state.ats_gap, state.jd_keywords);
        }
        if (state.resume_text && state.resume_version !== undefined && state.resume_id) {
          setResumeState(state.resume_text, state.resume_version, state.resume_id);
        }
        if (state.cover_letter_text && state.cover_letter_id) {
          setCoverLetterState(state.cover_letter_text, state.cover_letter_id);
        }

        // Navigation based on status
        if (status === "interrupted") {
          stopPolling();
          if (interrupt_node === "show_ats") {
            setScreen("ats");
            navigate("/ats");
          } else if (interrupt_node === "show_resume") {
            setScreen("resume");
            navigate("/resume");
          } else if (interrupt_node === "cover_letter_ask" || interrupt_node === "show_cover_letter") {
            setScreen("cover");
            navigate("/cover-letter");
          }
        } else if (status === "complete") {
          stopPolling();
          setScreen("logs");
          navigate("/logs");
        }
      } catch (err) {
        console.error("Graph status poll error:", err);
        stopPolling();
      }
    };

    // Immediate first poll
    poll();
    intervalRef.current = setInterval(poll, POLL_INTERVAL_MS);

    return stopPolling;
  }, [runId]);
}
