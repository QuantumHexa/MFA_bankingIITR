"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type Analytics = {
  factor_usage: Record<string, number>;
  hourly_events: Record<string, number>;
  success_count: number;
  failed_count: number;
  total_24h: number;
};

const CHART_PRIMARY = "#0D7377";
const CHART_SECONDARY = "#5B6B76";
const CHART_SUCCESS = "#1A7A4C";
const CHART_ERROR = "#B91C1C";
const CHART_GRID = "#E3E9EC";

export function AdminCharts({ data }: { data: Analytics | null }) {
  if (!data) return null;

  const factorData = Object.entries(data.factor_usage).map(([name, value]) => ({ name, value }));
  const hourlyData = Object.entries(data.hourly_events).map(([hour, count]) => ({ hour, count }));
  const outcomeData = [
    { name: "Success", value: data.success_count },
    { name: "Failed", value: data.failed_count },
  ];
  const outcomeColors = [CHART_SUCCESS, CHART_ERROR];

  return (
    <div className="mt-6 grid gap-6 lg:grid-cols-3">
      <div className="bank-card p-5">
        <h3 className="mb-4 text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">Auth Outcomes (24h)</h3>
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie data={outcomeData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={70} label>
              {outcomeData.map((_, i) => (
                <Cell key={i} fill={outcomeColors[i]} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      </div>

      <div className="bank-card p-5">
        <h3 className="mb-4 text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">Factor Usage (24h)</h3>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={factorData}>
            <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID} />
            <XAxis dataKey="name" tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} />
            <Tooltip />
            <Bar dataKey="value" fill={CHART_PRIMARY} radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="bank-card p-5">
        <h3 className="mb-4 text-xs font-semibold uppercase tracking-wide text-[var(--text-secondary)]">Events by Hour</h3>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={hourlyData}>
            <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID} />
            <XAxis dataKey="hour" tick={{ fontSize: 9 }} />
            <YAxis tick={{ fontSize: 10 }} />
            <Tooltip />
            <Bar dataKey="count" fill={CHART_SECONDARY} radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
