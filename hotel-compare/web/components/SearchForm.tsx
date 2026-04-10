"use client";

import { useState } from "react";
import { supabase } from "@/lib/supabase";

type EngineOption = "browser-use" | "page-agent" | "dual";

interface Props {
  onTaskCreated: (taskId: string, engine?: string) => void;
  disabled?: boolean;
}

const engineOptions: { value: EngineOption; label: string }[] = [
  { value: "browser-use", label: "Browser-Use" },
  { value: "page-agent", label: "Page-Agent" },
  { value: "dual", label: "Both (对比模式)" },
];

export default function SearchForm({ onTaskCreated, disabled }: Props) {
  const [hotel, setHotel] = useState("北京国贸大酒店");
  const [checkin, setCheckin] = useState("2026-04-15");
  const [checkout, setCheckout] = useState("2026-04-17");
  const [engine, setEngine] = useState<EngineOption>("browser-use");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    const { data, error } = await supabase
      .from("tasks")
      .insert({ hotel, checkin, checkout, engine })
      .select("id")
      .single();
    setLoading(false);
    if (data) onTaskCreated(data.id, engine);
    if (error) alert("Failed to create task: " + error.message);
  }

  const isDisabled = disabled || loading;

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="flex flex-col sm:flex-row gap-3 items-end">
        <div className="flex-1">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            酒店名称
          </label>
          <input
            type="text"
            value={hotel}
            onChange={(e) => setHotel(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="输入酒店名称"
            required
            disabled={isDisabled}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            入住
          </label>
          <input
            type="date"
            value={checkin}
            onChange={(e) => setCheckin(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            required
            disabled={isDisabled}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            离店
          </label>
          <input
            type="date"
            value={checkout}
            onChange={(e) => setCheckout(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            required
            disabled={isDisabled}
          />
        </div>
        <button
          type="submit"
          disabled={isDisabled}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
        >
          {loading ? "提交中..." : "开始比价"}
        </button>
      </div>

      {/* Engine selector */}
      <div className="flex items-center gap-1">
        <span className="text-sm font-medium text-gray-700 mr-2">引擎选择:</span>
        {engineOptions.map((opt) => (
          <label
            key={opt.value}
            aria-disabled={isDisabled}
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-colors border ${
              engine === opt.value
                ? "bg-blue-50 border-blue-300 text-blue-700"
                : "bg-white border-gray-200 text-gray-600 hover:bg-gray-50"
            } ${isDisabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
          >
            <input
              type="radio"
              name="engine"
              value={opt.value}
              checked={engine === opt.value}
              onChange={() => setEngine(opt.value)}
              disabled={isDisabled}
              className="sr-only"
            />
            <span
              className={`w-3 h-3 rounded-full border-2 flex-shrink-0 ${
                engine === opt.value
                  ? "border-blue-500 bg-blue-500"
                  : "border-gray-400"
              }`}
            >
              {engine === opt.value && (
                <span className="block w-1.5 h-1.5 bg-white rounded-full m-[1px]" />
              )}
            </span>
            {opt.label}
          </label>
        ))}
      </div>
    </form>
  );
}
