"use client";

import { useMemo } from "react";
import { StepLog, Result } from "@/lib/types";
import PlatformCard from "@/components/PlatformCard";

const PLATFORMS = ["携程", "去哪儿", "同程"];

interface Props {
  steps: StepLog[];
  results: Result[];
  isRunning: boolean;
}

interface EngineColumnProps {
  engineLabel: string;
  engineKey: "browser-use" | "page-agent";
  steps: StepLog[];
  results: Result[];
  isRunning: boolean;
}

function EngineColumn({
  engineLabel,
  engineKey,
  steps,
  results,
  isRunning,
}: EngineColumnProps) {
  const engineSteps = useMemo(
    () => steps.filter((s) => s.engine === engineKey),
    [steps, engineKey]
  );
  const engineResults = useMemo(
    () => results.filter((r) => r.engine === engineKey),
    [results, engineKey]
  );
  const hasAnyActivity = engineSteps.length > 0 || engineResults.length > 0;

  return (
    <div className="flex-1 min-w-0">
      <div className="flex items-center gap-2 mb-4">
        <h2 className="text-lg font-bold text-gray-800">{engineLabel}</h2>
        <span
          className={`text-xs px-2 py-0.5 rounded-full ${
            hasAnyActivity
              ? "bg-green-100 text-green-700"
              : isRunning
                ? "bg-amber-100 text-amber-700"
                : "bg-gray-100 text-gray-500"
          }`}
        >
          {hasAnyActivity
            ? engineResults.length === PLATFORMS.length
              ? "已完成"
              : "运行中"
            : isRunning
              ? "等待启动"
              : "待执行"}
        </span>
      </div>
      <div className="grid grid-cols-1 gap-4">
        {PLATFORMS.map((p) => (
          <PlatformCard
            key={`${engineKey}-${p}`}
            platform={p}
            steps={engineSteps.filter((s) => s.platform === p)}
            result={engineResults.find((r) => r.platform === p)}
            isRunning={isRunning}
          />
        ))}
      </div>
    </div>
  );
}

export default function DualEngineView({ steps, results, isRunning }: Props) {
  return (
    <div className="mt-8">
      <div className="flex items-center gap-2 mb-6">
        <div className="h-px flex-1 bg-gray-200" />
        <span className="text-sm font-medium text-gray-500 px-3">
          双引擎对比模式
        </span>
        <div className="h-px flex-1 bg-gray-200" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <EngineColumn
          engineLabel="Browser-Use"
          engineKey="browser-use"
          steps={steps}
          results={results}
          isRunning={isRunning}
        />
        <EngineColumn
          engineLabel="Page-Agent"
          engineKey="page-agent"
          steps={steps}
          results={results}
          isRunning={isRunning}
        />
      </div>
    </div>
  );
}
