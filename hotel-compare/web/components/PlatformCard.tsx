"use client";

import { useState, useMemo, useCallback } from "react";
import Image from "next/image";
import { StepLog, Result } from "@/lib/types";
import BootAnimation from "./BootAnimation";
import StepTimeline from "./StepTimeline";
import StepDetailPanel from "./StepDetailPanel";

interface Props {
  platform: string;
  steps: StepLog[];
  result?: Result | null;
  isRunning?: boolean;
}

const MAX_STEPS = 15;

export default function PlatformCard({
  platform,
  steps,
  result,
  isRunning,
}: Props) {
  const [selectedStepNum, setSelectedStepNum] = useState<number | null>(null);
  const [showDetail, setShowDetail] = useState(false);
  const [showThinking, setShowThinking] = useState(false);

  const latestStep = useMemo(() => steps[steps.length - 1], [steps]);
  const isSearching = useMemo(
    () => steps.length > 0 && !result,
    [steps.length, result]
  );
  const hasError = result?.error;
  const isBooting = !steps.length && !result && isRunning;

  // Resolve the selected step (default to latest)
  const effectiveStepNum = selectedStepNum ?? latestStep?.step_num ?? null;
  const selectedStep = useMemo(() => {
    if (effectiveStepNum) {
      return steps.find((s) => s.step_num === effectiveStepNum) ?? latestStep;
    }
    return latestStep;
  }, [effectiveStepNum, steps, latestStep]);

  const progressPercent = useMemo(
    () =>
      latestStep
        ? Math.min(Math.round((latestStep.step_num / MAX_STEPS) * 100), 100)
        : 0,
    [latestStep]
  );

  const toggleThinking = useCallback(
    () => setShowThinking((v) => !v),
    []
  );
  const toggleDetail = useCallback(() => setShowDetail((v) => !v), []);
  const handleStepSelect = useCallback(
    (num: number) => setSelectedStepNum(num),
    []
  );

  return (
    <div className="border border-gray-200 rounded-xl overflow-hidden bg-white shadow-sm">
      {/* Header */}
      <div className="px-4 py-3 bg-gray-50 border-b flex items-center justify-between">
        <h3 className="font-semibold text-lg">{platform}</h3>
        <span className="text-sm">
          {isBooting && (
            <span className="text-amber-500 animate-pulse">Agent 启动中</span>
          )}
          {!steps.length && !result && !isRunning && (
            <span className="text-gray-400">等待中...</span>
          )}
          {isSearching && (
            <span className="text-blue-600 animate-pulse">
              Step {latestStep.step_num}
            </span>
          )}
          {result && !hasError && (
            <span className="text-green-600 font-bold">
              ¥{result.lowest_price}
            </span>
          )}
          {hasError && <span className="text-red-500">失败</span>}
        </span>
      </div>

      {/* Thin progress bar under header */}
      {steps.length > 0 && (
        <div className="h-1 bg-gray-100">
          <div
            className={`h-full transition-all duration-700 ease-out ${
              result && !hasError
                ? "bg-green-500"
                : hasError
                  ? "bg-red-400"
                  : "bg-blue-500"
            }`}
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      )}

      {/* Screenshot area */}
      <div className="aspect-video bg-gray-100 relative overflow-hidden">
        {isBooting ? (
          <BootAnimation platform={platform} />
        ) : latestStep?.screenshot_url ? (
          <Image
            src={latestStep.screenshot_url}
            alt={`${platform} Step ${latestStep.step_num}`}
            fill
            className="object-cover object-top"
            unoptimized
          />
        ) : (
          <div className="flex items-center justify-center h-full text-gray-400 text-sm">
            {isSearching ? "截图加载中..." : "等待搜索"}
          </div>
        )}

        {/* Thinking overlay */}
        {showThinking && selectedStep?.thinking && (
          <div className="absolute inset-0 bg-black/70 text-white text-xs p-3 overflow-y-auto font-mono leading-relaxed">
            {selectedStep.thinking}
          </div>
        )}

        {/* Goal bar */}
        {isSearching && latestStep?.goal && !showThinking && (
          <div className="absolute bottom-0 left-0 right-0 bg-black/60 text-white text-xs px-3 py-1.5 truncate">
            {latestStep.goal}
          </div>
        )}

        {/* Thinking toggle button */}
        {selectedStep?.thinking && (
          <button
            onClick={toggleThinking}
            className={`absolute top-2 right-2 w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-colors ${
              showThinking
                ? "bg-white text-gray-800 shadow"
                : "bg-black/40 text-white hover:bg-black/60"
            }`}
            title={showThinking ? "隐藏思考过程" : "查看思考过程"}
          >
            T
          </button>
        )}
      </div>

      {/* Step Timeline */}
      {steps.length > 0 && (
        <StepTimeline
          steps={steps}
          selectedStepNum={effectiveStepNum}
          onStepSelect={handleStepSelect}
          isSearching={isSearching}
        />
      )}

      {/* Detail toggle */}
      {steps.length > 0 && (
        <div className="px-3 pb-2">
          <button
            onClick={toggleDetail}
            className="text-xs text-gray-500 hover:text-gray-700 transition-colors flex items-center gap-1"
          >
            <span
              className={`inline-block transition-transform duration-200 ${
                showDetail ? "rotate-90" : ""
              }`}
            >
              ▶
            </span>
            {showDetail ? "收起详情" : "展开详情"}
          </button>
        </div>
      )}

      {/* Step Detail Panel */}
      {showDetail && selectedStep && (
        <StepDetailPanel step={selectedStep} maxSteps={MAX_STEPS} />
      )}

      {/* Result footer */}
      {result && !hasError && (
        <div className="px-4 py-3 bg-green-50 border-t">
          <p className="font-bold text-green-800 text-xl">
            ¥{result.lowest_price}
          </p>
          <p className="text-sm text-gray-600">{result.room_type || "-"}</p>
          <p className="text-xs text-gray-400 truncate">
            {result.hotel_name || "-"}
          </p>
        </div>
      )}
      {hasError && (
        <div className="px-4 py-3 bg-red-50 border-t">
          <p className="text-sm text-red-600">搜索失败: {result!.error}</p>
        </div>
      )}
    </div>
  );
}
