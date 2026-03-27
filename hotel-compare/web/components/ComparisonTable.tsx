import { Result } from "@/lib/types";

interface Props {
  results: Result[];
}

export default function ComparisonTable({ results }: Props) {
  const valid = results
    .filter((r) => r.lowest_price != null)
    .sort((a, b) => a.lowest_price! - b.lowest_price!);

  if (valid.length === 0) return null;

  const cheapest = valid[0];

  return (
    <div className="mt-8">
      <h2 className="text-xl font-bold mb-4">比价结果</h2>
      <div className="overflow-hidden rounded-xl border border-gray-200">
        <table className="w-full text-left">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-sm font-medium text-gray-500">
                平台
              </th>
              <th className="px-4 py-3 text-sm font-medium text-gray-500">
                最低价
              </th>
              <th className="px-4 py-3 text-sm font-medium text-gray-500">
                房型
              </th>
              <th className="px-4 py-3 text-sm font-medium text-gray-500">
                酒店名
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {valid.map((r) => (
              <tr
                key={r.platform}
                className={r.id === cheapest.id ? "bg-green-50" : ""}
              >
                <td className="px-4 py-3 font-medium">
                  {r.id === cheapest.id && "🏆 "}
                  {r.platform}
                </td>
                <td className="px-4 py-3 font-bold text-lg">
                  ¥{r.lowest_price}
                </td>
                <td className="px-4 py-3 text-gray-600">
                  {r.room_type || "-"}
                </td>
                <td className="px-4 py-3 text-gray-600 text-sm">
                  {r.hotel_name || "-"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {valid.length >= 2 && (
        <p className="mt-3 text-green-700 font-medium">
          最低价: {cheapest.platform} ¥{cheapest.lowest_price} (比最高价低 ¥
          {valid[valid.length - 1].lowest_price! - cheapest.lowest_price!})
        </p>
      )}
    </div>
  );
}
