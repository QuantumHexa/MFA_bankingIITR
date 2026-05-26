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

const COLORS = ["#0c2d57", "#c9a227", "#059669", "#dc2626", "#7c3aed"];

export function AdminCharts({ data }: { data: Analytics | null }) {
  if (!data) return null;

  const factorData = Object.entries(data.factor_usage).map(([name, value]) => ({ name, value }));
  const hourlyData = Object.entries(data.hourly_events).map(([hour, count]) => ({ hour, count }));
  const outcomeData = [
    { name: "Success", value: data.success_count },
    { name: "Failed", value: data.failed_count },
  ];

  return (
    <div className="mt-6 grid gap-6 lg:grid-cols-3">
      <div className="bank-card rounded-2xl p-5">
        <h3 className="mb-4 text-sm font-semibold">Auth Outcomes (24h)</h3>
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie data={outcomeData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={70} label>
              {outcomeData.map((_, i) => (
                <Cell key={i} fill={COLORS[i % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      </div>

      <div className="bank-card rounded-2xl p-5">
        <h3 className="mb-4 text-sm font-semibold">Factor Usage (24h)</h3>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={factorData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="name" tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} />
            <Tooltip />
            <Bar dataKey="value" fill="#0c2d57" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="bank-card rounded-2xl p-5">
        <h3 className="mb-4 text-sm font-semibold">Events by Hour</h3>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={hourlyData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="hour" tick={{ fontSize: 9 }} />
            <YAxis tick={{ fontSize: 10 }} />
            <Tooltip />
            <Bar dataKey="count" fill="#c9a227" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
