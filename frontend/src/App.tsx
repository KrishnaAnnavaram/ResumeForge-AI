import { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate, NavLink } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { supabase } from "./lib/supabase";
import { useAppStore } from "./store/appStore";
import { ErrorBoundary } from "./components/ErrorBoundary";
import JDInput from "./components/JDInput";
import ATSDashboard from "./components/ATSDashboard";
import ResumePreview from "./components/ResumePreview";
import CoverLetter from "./components/CoverLetter";
import LogTable from "./components/LogTable";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 2 * 60 * 1000,
    },
  },
});

function AppShell() {
  const setUserId = useAppStore((s) => s.setUserId);
  const userId = useAppStore((s) => s.userId);

  // Sync Supabase auth session to Zustand
  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setUserId(data.session?.user.id ?? null);
    });
    const { data: listener } = supabase.auth.onAuthStateChange((_event, session) => {
      setUserId(session?.user.id ?? null);
    });
    return () => listener.subscription.unsubscribe();
  }, [setUserId]);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top nav — only show when logged in */}
      {userId && (
        <nav className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
          <NavLink to="/" className="font-bold text-brand-700 text-lg">
            ResumeForge AI
          </NavLink>
          <div className="flex items-center gap-5 text-sm">
            <NavLink
              to="/"
              className={({ isActive }) =>
                isActive ? "text-brand-700 font-medium" : "text-gray-500 hover:text-gray-900"
              }
            >
              New Application
            </NavLink>
            <NavLink
              to="/logs"
              className={({ isActive }) =>
                isActive ? "text-brand-700 font-medium" : "text-gray-500 hover:text-gray-900"
              }
            >
              Application Log
            </NavLink>
            <button
              onClick={() => supabase.auth.signOut()}
              className="text-gray-400 hover:text-gray-700 transition"
            >
              Sign out
            </button>
          </div>
        </nav>
      )}

      <Routes>
        <Route
          path="/"
          element={
            <ErrorBoundary>
              <JDInput />
            </ErrorBoundary>
          }
        />
        <Route
          path="/ats"
          element={
            <ErrorBoundary>
              <ATSDashboard />
            </ErrorBoundary>
          }
        />
        <Route
          path="/resume"
          element={
            <ErrorBoundary>
              <ResumePreview />
            </ErrorBoundary>
          }
        />
        <Route
          path="/cover-letter"
          element={
            <ErrorBoundary>
              <CoverLetter />
            </ErrorBoundary>
          }
        />
        <Route
          path="/logs"
          element={
            <ErrorBoundary>
              <LogTable />
            </ErrorBoundary>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppShell />
      </BrowserRouter>
    </QueryClientProvider>
  );
}
