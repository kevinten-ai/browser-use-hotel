"use client";

import { useEffect, useState, useCallback, useRef, useMemo } from "react";
import { supabase } from "@/lib/supabase";
import { StepLog, Result } from "@/lib/types";
import SearchForm from "@/components/SearchForm";
import PlatformCard from "@/components/PlatformCard";
import ComparisonTable from "@/components/ComparisonTable";
import DualEngineView from "@/components/DualEngineView";
import EngineComparisonTable from "@/components/EngineComparisonTable";

const PLATFORMS = ["携程", "去哪儿", "同程"];
const POLL_INTERVAL = 3000;

export default function Home() {
  const [taskId, setTaskId] = useState<string | null>(null);
  const [engine, setEngine] = useState<string>("browser-use");
  const [steps, setSteps] = useState<StepLog[]>([]);
  const [results, setResults] = useState<Result[]>([]);
  const [taskStatus, setTaskStatus] = useState<string>("idle");
  const stepsRef = useRef<StepLog[]>([]);
  const resultsRef = useRef<Result[]>([]);

  const handleTaskCreated = useCallback((id: string, eng?: string) => {
    setTaskId(id);
    setEngine(eng || "browser-use");
    setSteps([]);
    setResults([]);
    stepsRef.current = [];
    resultsRef.current = [];
    setTaskStatus("running");
  }, []);

  // Polling fallback: fetch step_logs, results, and task status every 3s
  useEffect(() => {
    if (!taskId) return;

    const poll = async () => {
      try {
        // Fetch step_logs
        const { data: newSteps, error: stepsErr } = await supabase
          .from("step_logs")
          .select("*")
          .eq("task_id", taskId)
          .order("created_at", { ascending: true });

        if (stepsErr) {
          console.error("Failed to fetch steps:", stepsErr.message);
        } else if (newSteps && newSteps.length > stepsRef.current.length) {
          const typed = newSteps as StepLog[];
          stepsRef.current = typed;
          setSteps(typed);
        }

        // Fetch results
        const { data: newResults, error: resultsErr } = await supabase
          .from("results")
          .select("*")
          .eq("task_id", taskId);

        if (resultsErr) {
          console.error("Failed to fetch results:", resultsErr.message);
        } else if (newResults && newResults.length > resultsRef.current.length) {
          const typed = newResults as Result[];
          resultsRef.current = typed;
          setResults(typed);
        }

        // Fetch task status
        const { data: taskData, error: taskErr } = await supabase
          .from("tasks")
          .select("status")
          .eq("id", taskId)
          .single();

        if (taskErr) {
          console.error("Failed to fetch task status:", taskErr.message);
        } else if (taskData) {
          setTaskStatus(taskData.status);
        }
      } catch (err) {
        console.error("Polling error:", err);
      }
    };

    // Run first poll immediately
    poll();
    const interval = setInterval(poll, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [taskId]);

  const isRunning = taskStatus === "running";
  const isDual = engine === "dual";

  // For single-engine mode, filter steps and results by the selected engine
  const filteredSteps = useMemo(
    () =>
      isDual ? steps : steps.filter((s) => !s.engine || s.engine === engine),
    [isDual, steps, engine]
  );
  const filteredResults = useMemo(
    () =>
      isDual ? results : results.filter((r) => !r.engine || r.engine === engine),
    [isDual, results, engine]
  );

  const platformCardsData = useMemo(
    () =>
      PLATFORMS.map((p) => ({
        platform: p,
        steps: filteredSteps.filter((s) => s.platform === p),
        result: filteredResults.find((r) => r.platform === p),
      })),
    [filteredSteps, filteredResults]
  );

  return (
    <main
      className={`${isDual ? "max-w-7xl" : "max-w-5xl"} mx-auto px-4 py-8`}
    >
      <h1 className="text-3xl font-bold mb-2">酒店跨平台比价</h1>
      <p className="text-gray-500 mb-6">
        {isDual
          ? "双引擎对比模式 — Browser-Use (服务端) vs Page-Agent (Chrome 插件) 并行搜索"
          : "基于 browser-use Agent — AI 自动操控浏览器搜索三大平台，实时截图直播"}
      </p>

      <SearchForm onTaskCreated={handleTaskCreated} disabled={isRunning} />

      {taskId && (
        <>
          {isDual ? (
            /* Dual engine: side-by-side view */
            <DualEngineView
              steps={filteredSteps}
              results={filteredResults}
              isRunning={isRunning}
            />
          ) : (
            /* Single engine: original 3-column grid */
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8">
              {platformCardsData.map(({ platform, steps, result }) => (
                <PlatformCard
                  key={platform}
                  platform={platform}
                  steps={steps}
                  result={result}
                  isRunning={isRunning}
                />
              ))}
            </div>
          )}

          {taskStatus === "completed" &&
            (isDual ? (
              <EngineComparisonTable results={filteredResults} />
            ) : (
              <ComparisonTable results={filteredResults} />
            ))}

          {isRunning && (
            <p className="mt-4 text-center text-gray-400 animate-pulse">
              {isDual
                ? "双引擎并行搜索中... 截图实时更新"
                : "Agent 正在搜索中... 截图实时更新"}
            </p>
          )}
        </>
      )}
    </main>
  );
}
