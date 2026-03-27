"use client";

import { StepLog } from "@/lib/types";

interface Props {
  steps: StepLog[];
  selectedStepNum: number | null;
  onStepSelect: (stepNum: number) => void;
  isSearching: boolean;
}

function isPositiveEvaluation(evaluation: string | null): boolean {
  if (!evaluation) return false;
  const lower = evaluation.toLowerCase();
  return (
    lower.includes("success") ||
    lower.includes("good") ||
    lower.includes("correct") ||
    lower.includes("completed") ||
    lower.includes("found") ||
    lower.includes("done")
  );
}

export default function StepTimeline({
  steps,
  selectedStepNum,
  onStepSelect,
  isSearching,
}: Props) {
  if (steps.length === 0) return null;

  const lastStepNum = steps[steps.length - 1].step_num;

  return (
    <div className="px-3 py-2 flex items-center gap-1.5 overflow-x-auto">
      {steps.map((step) => {
        const isCurrent = isSearching && step.step_num === lastStepNum;
        const isSelected = step.step_num === selectedStepNum;
        const positive = isPositiveEvaluation(step.evaluation);

        let dotColor = "bg-gray-300";
        if (isCurrent) {
          dotColor = "bg-blue-500";
        } else if (positive) {
          dotColor = "bg-green-500";
        } else if (step.evaluation) {
          dotColor = "bg-gray-400";
        }

        return (
          <button
            key={step.step_num}
            onClick={() => onStepSelect(step.step_num)}
            className={`group relative shrink-0 w-3 h-3 rounded-full transition-all duration-200 cursor-pointer ${dotColor} ${
              isCurrent ? "animate-pulse scale-125" : ""
            } ${isSelected ? "ring-2 ring-blue-400 ring-offset-1" : ""}`}
            title={`Step ${step.step_num}`}
          >
            <span className="absolute -top-7 left-1/2 -translate-x-1/2 bg-gray-800 text-white text-[10px] px-1.5 py-0.5 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
              Step {step.step_num}
            </span>
          </button>
        );
      })}
    </div>
  );
}
