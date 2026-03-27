"use client";

import { Result } from "@/lib/types";

const PLATFORMS = ["携程", "去哪儿", "同程"];

interface Props {
  results: Result[];
}

interface PlatformComparison {
  platform: string;
  buResult: Result | undefined;
  paResult: Result | undefined;
  winner: "browser-use" | "page-agent" | "tie" | "none";
}

function formatDuration(seconds: number | null): string {
  if (seconds == null) return "-";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${mins}m ${secs}s`;
}

function formatPrice(price: number | null): string {
  if (price == null) return "-";
  return `¥${price}`;
}

export default function EngineComparisonTable({ results }: Props) {
  const buResults = results.filter((r) => r.engine === "browser-use");
  const paResults = results.filter((r) => r.engine === "page-agent");

  // Need at least one result from each engine to show comparison
  if (buResults.length === 0 && paResults.length === 0) return null;

  const comparisons: PlatformComparison[] = PLATFORMS.map((platform) => {
    const buResult = buResults.find((r) => r.platform === platform);
    const paResult = paResults.find((r) => r.platform === platform);

    let winner: PlatformComparison["winner"] = "none";
    const buPrice = buResult?.lowest_price;
    const paPrice = paResult?.lowest_price;

    if (buPrice != null && paPrice != null) {
      if (buPrice < paPrice) winner = "browser-use";
      else if (paPrice < buPrice) winner = "page-agent";
      else winner = "tie";
    } else if (buPrice != null && (paResult == null || paResult.error)) {
      winner = "browser-use";
    } else if (paPrice != null && (buResult == null || buResult.error)) {
      winner = "page-agent";
    }

    return { platform, buResult, paResult, winner };
  });

  // Summary stats
  const buWins = comparisons.filter((c) => c.winner === "browser-use").length;
  const paWins = comparisons.filter((c) => c.winner === "page-agent").length;
  const ties = comparisons.filter((c) => c.winner === "tie").length;

  const buDurations = buResults
    .map((r) => r.duration_seconds)
    .filter((d): d is number => d != null);
  const paDurations = paResults
    .map((r) => r.duration_seconds)
    .filter((d): d is number => d != null);

  const buAvgSpeed =
    buDurations.length > 0
      ? buDurations.reduce((a, b) => a + b, 0) / buDurations.length
      : null;
  const paAvgSpeed =
    paDurations.length > 0
      ? paDurations.reduce((a, b) => a + b, 0) / paDurations.length
      : null;

  const overallWinner =
    buWins > paWins
      ? "Browser-Use"
      : paWins > buWins
        ? "Page-Agent"
        : "平手";

  return (
    <div className="mt-8">
      <h2 className="text-xl font-bold mb-4">引擎对比结果</h2>

      <div className="overflow-hidden rounded-xl border border-gray-200">
        <table className="w-full text-left">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-sm font-medium text-gray-500">
                平台
              </th>
              <th className="px-4 py-3 text-sm font-medium text-gray-500">
                Browser-Use 价格
              </th>
              <th className="px-4 py-3 text-sm font-medium text-gray-500">
                Page-Agent 价格
              </th>
              <th className="px-4 py-3 text-sm font-medium text-gray-500">
                BU 耗时
              </th>
              <th className="px-4 py-3 text-sm font-medium text-gray-500">
                PA 耗时
              </th>
              <th className="px-4 py-3 text-sm font-medium text-gray-500">
                胜出
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {comparisons.map((c) => {
              const buHasLower = c.winner === "browser-use";
              const paHasLower = c.winner === "page-agent";

              return (
                <tr key={c.platform}>
                  <td className="px-4 py-3 font-medium">{c.platform}</td>
                  <td
                    className={`px-4 py-3 font-bold text-lg ${
                      buHasLower ? "text-green-700" : "text-gray-700"
                    }`}
                  >
                    {c.buResult?.error
                      ? "失败"
                      : formatPrice(c.buResult?.lowest_price ?? null)}
                  </td>
                  <td
                    className={`px-4 py-3 font-bold text-lg ${
                      paHasLower ? "text-green-700" : "text-gray-700"
                    }`}
                  >
                    {c.paResult?.error
                      ? "失败"
                      : formatPrice(c.paResult?.lowest_price ?? null)}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {formatDuration(c.buResult?.duration_seconds ?? null)}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">
                    {formatDuration(c.paResult?.duration_seconds ?? null)}
                  </td>
                  <td className="px-4 py-3">
                    {c.winner === "browser-use" && (
                      <span className="text-sm font-medium text-blue-600">
                        Browser-Use
                      </span>
                    )}
                    {c.winner === "page-agent" && (
                      <span className="text-sm font-medium text-purple-600">
                        Page-Agent
                      </span>
                    )}
                    {c.winner === "tie" && (
                      <span className="text-sm text-gray-500">平手</span>
                    )}
                    {c.winner === "none" && (
                      <span className="text-sm text-gray-400">-</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Summary */}
      <div className="mt-4 p-4 bg-gray-50 rounded-xl border border-gray-200">
        <div className="flex flex-wrap gap-6 text-sm">
          <div>
            <span className="text-gray-500">综合胜出: </span>
            <span className="font-bold text-gray-800">{overallWinner}</span>
          </div>
          <div>
            <span className="text-gray-500">Browser-Use 胜出: </span>
            <span className="font-medium text-blue-600">{buWins} 平台</span>
          </div>
          <div>
            <span className="text-gray-500">Page-Agent 胜出: </span>
            <span className="font-medium text-purple-600">{paWins} 平台</span>
          </div>
          {ties > 0 && (
            <div>
              <span className="text-gray-500">平手: </span>
              <span className="font-medium">{ties} 平台</span>
            </div>
          )}
          {buAvgSpeed != null && (
            <div>
              <span className="text-gray-500">BU 平均耗时: </span>
              <span className="font-medium">{formatDuration(buAvgSpeed)}</span>
            </div>
          )}
          {paAvgSpeed != null && (
            <div>
              <span className="text-gray-500">PA 平均耗时: </span>
              <span className="font-medium">{formatDuration(paAvgSpeed)}</span>
            </div>
          )}
          {buAvgSpeed != null && paAvgSpeed != null && (
            <div>
              <span className="text-gray-500">速度差: </span>
              <span className="font-medium">
                {buAvgSpeed < paAvgSpeed
                  ? `BU 快 ${formatDuration(paAvgSpeed - buAvgSpeed)}`
                  : paAvgSpeed < buAvgSpeed
                    ? `PA 快 ${formatDuration(buAvgSpeed - paAvgSpeed)}`
                    : "相同"}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
