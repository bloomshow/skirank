import type { ForecastDay } from "../lib/types";

interface ForecastTableProps {
  forecast: ForecastDay[];
}

const WMO_LABELS: Record<number, string> = {
  0: "Clear", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
  45: "Fog", 48: "Rime fog",
  51: "Light drizzle", 53: "Moderate drizzle", 55: "Heavy drizzle",
  61: "Light rain", 63: "Rain", 65: "Heavy rain",
  71: "Light snow", 73: "Snow", 75: "Heavy snow", 77: "Snow grains",
  80: "Showers", 85: "Snow showers", 86: "Heavy snow showers",
  95: "Thunderstorm", 96: "Thunderstorm + hail", 99: "Thunderstorm + heavy hail",
};

function wmoLabel(code: number | null): string {
  if (code === null) return "—";
  return WMO_LABELS[code] ?? `Code ${code}`;
}

export default function ForecastTable({ forecast }: ForecastTableProps) {
  if (!forecast.length) {
    return <p className="text-sm text-slate-400">No forecast data available.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200 text-slate-500 text-left">
            <th className="py-2 pr-4 font-medium">Date</th>
            <th className="py-2 pr-4 font-medium">Snow</th>
            <th className="py-2 pr-4 font-medium">Temp range</th>
            <th className="py-2 pr-4 font-medium">Wind max</th>
            <th className="py-2 pr-4 font-medium">Precip %</th>
            <th className="py-2 font-medium">Condition</th>
          </tr>
        </thead>
        <tbody>
          {forecast.map((day) => (
            <tr key={day.forecast_date} className="border-b border-slate-100 hover:bg-slate-50">
              <td className="py-2 pr-4 font-medium text-slate-700">
                {new Date(day.forecast_date).toLocaleDateString("en-GB", {
                  weekday: "short", month: "short", day: "numeric",
                })}
              </td>
              <td className="py-2 pr-4 text-blue-600 font-medium">
                {day.snowfall_cm !== null ? `${day.snowfall_cm}cm` : "—"}
              </td>
              <td className="py-2 pr-4 text-slate-600">
                {day.temperature_min_c !== null && day.temperature_max_c !== null
                  ? `${day.temperature_min_c}° / ${day.temperature_max_c}°C`
                  : "—"}
              </td>
              <td className="py-2 pr-4 text-slate-600">
                {day.wind_speed_max_kmh !== null ? `${day.wind_speed_max_kmh} km/h` : "—"}
              </td>
              <td className="py-2 pr-4 text-slate-600">
                {day.precipitation_prob_pct !== null ? `${day.precipitation_prob_pct}%` : "—"}
              </td>
              <td className="py-2 text-slate-500 text-xs">{wmoLabel(day.weather_code)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
