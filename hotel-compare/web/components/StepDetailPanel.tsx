"use client";

import { StepLog } from "@/lib/types";

interface Props {
  step: StepLog;
  maxSteps?: number;
}

function formatActionKey(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function StepDetailPanel({ step, maxSteps = 15 }: Props) {
  const progressPercent = Math.min(
    Math.round((step.step_num / maxSteps) * 100),
    100
  );

  return (
    <div className="border-t border-gray-100 bg-gray-50 px-4 py-3 text-sm space-y-3">
      {/* Progress bar */}
      <div>
        <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
          <span>
            Step {step.step_num} / {maxSteps}
          </span>
          <span>{progressPercent}%</span>
        </div>
        <div className="w-full h-1.5 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-blue-500 rounded-full transition-all duration-500"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>

      {/* Thinking */}
      {step.thinking && (
        <div>
          <p className="text-xs font-medium text-gray-500 mb-1">Thinking</p>
          <pre className="text-xs bg-white border border-gray-200 rounded p-2 whitespace-pre-wrap break-words font-mono text-gray-700 max-h-32 overflow-y-auto">
            {step.thinking}
          </pre>
        </div>
      )}

      {/* Evaluation */}
      {step.evaluation && (
        <div>
          <p className="text-xs font-medium text-gray-500 mb-1">Evaluation</p>
          <span
            className={`inline-block text-xs px-2 py-0.5 rounded-full font-medium ${
              step.evaluation.toLowerCase().includes("success") ||
              step.evaluation.toLowerCase().includes("good") ||
              step.evaluation.toLowerCase().includes("correct")
                ? "bg-green-100 text-green-700"
                : step.evaluation.toLowerCase().includes("fail") ||
                    step.evaluation.toLowerCase().includes("error")
                  ? "bg-red-100 text-red-700"
                  : "bg-yellow-100 text-yellow-700"
            }`}
          >
            {step.evaluation}
          </span>
        </div>
      )}

      {/* Memory */}
      {step.memory && (
        <div>
          <p className="text-xs font-medium text-gray-500 mb-1">Memory</p>
          <p className="text-xs text-gray-600 bg-white border border-gray-200 rounded p-2 max-h-20 overflow-y-auto">
            {step.memory}
          </p>
        </div>
      )}

      {/* Actions */}
      {step.actions && step.actions.length > 0 && (
        <div>
          <p className="text-xs font-medium text-gray-500 mb-1">
            Actions ({step.actions.length})
          </p>
          <ul className="space-y-1">
            {step.actions.map((action, idx) => (
              <li
                key={idx}
                className="text-xs bg-white border border-gray-200 rounded p-2 text-gray-700"
              >
                {Object.entries(action).map(([key, value]) => (
                  <span key={key} className="block">
                    <span className="font-medium text-gray-500">
                      {formatActionKey(key)}:
                    </span>{" "}
                    {typeof value === "string"
                      ? value
                      : JSON.stringify(value)}
                  </span>
                ))}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* URL */}
      {step.url && (
        <div>
          <p className="text-xs font-medium text-gray-500 mb-1">URL</p>
          <p className="text-xs text-blue-600 truncate" title={step.url}>
            {step.url}
          </p>
        </div>
      )}
    </div>
  );
}
