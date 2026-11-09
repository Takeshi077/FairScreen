"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ErrorBar,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const axisStyle = { fill: "var(--muted)", fontSize: 12 };
const tooltipStyle = {
  background: "var(--surface)",
  border: "1px solid var(--line)",
  borderRadius: "0.5rem",
  color: "var(--ink)",
  fontSize: 12,
};

export interface WhiskerDatum {
  label: string;
  gap: number;
  error: [number, number];
  low: number;
  high: number;
  significant: boolean;
  n: number;
}

export function GapWhiskerChart({ data }: { data: WhiskerDatum[] }) {
  return (
    <div className="h-[22rem] w-full sm:h-[26rem]">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 10, right: 24, bottom: 10, left: 8 }}>
          <CartesianGrid horizontal={false} stroke="var(--line)" />
          <XAxis
            type="number"
            dataKey="gap"
            domain={[-1, 1]}
            tick={{ ...axisStyle, fontSize: 11 }}
            tickFormatter={(value: number) => value.toFixed(1)}
            stroke="var(--line)"
            label={{
              value: "Score gap (points)",
              position: "insideBottom",
              offset: -2,
              fill: "var(--muted)",
              fontSize: 12,
            }}
          />
          <YAxis
            type="category"
            dataKey="label"
            width={158}
            tick={{ ...axisStyle, fontSize: 11 }}
            stroke="var(--line)"
          />
          <ReferenceLine x={0} stroke="var(--ink)" strokeDasharray="4 4" />
          <Tooltip
            contentStyle={tooltipStyle}
            cursor={{ strokeDasharray: "3 3" }}
            formatter={(value, name, item) => {
              if (name === "gap") {
                const row = item.payload as WhiskerDatum;
                return [
                  `${row.gap.toFixed(2)} pts (${row.low.toFixed(2)} to ${row.high.toFixed(2)}), n=${row.n}`,
                  row.significant ? "Gap beyond 95% CI" : "Inside 95% CI",
                ];
              }
              return [String(value), String(name)];
            }}
          />
          <Scatter data={data} dataKey="gap">
            {data.map((entry) => (
              <Cell
                key={entry.label}
                fill={entry.significant ? "var(--coral)" : "var(--teal)"}
              />
            ))}
            <ErrorBar
              dataKey="error"
              direction="x"
              width={5}
              strokeWidth={2}
              stroke="var(--ink)"
            />
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}

export interface BeforeAfterDatum {
  label: string;
  before: number;
  after: number;
}

export function BeforeAfterChart({ data }: { data: BeforeAfterDatum[] }) {
  return (
    <div className="h-[19rem] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 10, right: 16, bottom: 10, left: 0 }}>
          <CartesianGrid vertical={false} stroke="var(--line)" />
          <XAxis dataKey="label" tick={axisStyle} stroke="var(--line)" />
          <YAxis
            tick={axisStyle}
            stroke="var(--line)"
            label={{
              value: "Mean absolute gap (points)",
              angle: -90,
              position: "insideLeft",
              fill: "var(--muted)",
              fontSize: 12,
            }}
          />
          <Tooltip
            contentStyle={tooltipStyle}
            formatter={(value) => `${Number(value).toFixed(2)} pts`}
          />
          <Legend wrapperStyle={{ fontSize: 12, color: "var(--muted)" }} />
          <Bar name="Baseline gap" dataKey="before" fill="var(--amber)" radius={[4, 4, 0, 0]} />
          <Bar name="After mitigation" dataKey="after" fill="var(--teal)" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export interface ModelComparisonDatum {
  label: string;
  [model: string]: string | number;
}

export function ModelComparisonChart({
  data,
  models,
  colors,
}: {
  data: ModelComparisonDatum[];
  models: string[];
  colors: string[];
}) {
  return (
    <div className="h-[28rem] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 10, right: 24, bottom: 10, left: 8 }}
        >
          <CartesianGrid horizontal={false} stroke="var(--line)" />
          <XAxis
            type="number"
            domain={[-1, 1]}
            tick={axisStyle}
            tickFormatter={(value: number) => value.toFixed(1)}
            stroke="var(--line)"
          />
          <YAxis
            type="category"
            dataKey="label"
            width={158}
            tick={{ ...axisStyle, fontSize: 11 }}
            stroke="var(--line)"
          />
          <ReferenceLine x={0} stroke="var(--ink)" strokeDasharray="4 4" />
          <Tooltip
            contentStyle={tooltipStyle}
            formatter={(value) => `${Number(value).toFixed(2)} pts`}
          />
          <Legend wrapperStyle={{ fontSize: 12, color: "var(--muted)" }} />
          {models.map((model, index) => (
            <Bar
              key={model}
              name={model}
              dataKey={model}
              fill={colors[index % colors.length]}
              radius={[0, 3, 3, 0]}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export interface ShortlistDatum {
  label: string;
  ratio: number;
  gap: number;
}

export function ShortlistChart({ data }: { data: ShortlistDatum[] }) {
  return (
    <div className="h-[22rem] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 10, right: 24, bottom: 10, left: 8 }}
        >
          <CartesianGrid horizontal={false} stroke="var(--line)" />
          <XAxis
            type="number"
            domain={[0, 1.2]}
            tick={axisStyle}
            stroke="var(--line)"
          />
          <YAxis
            type="category"
            dataKey="label"
            width={158}
            tick={{ ...axisStyle, fontSize: 11 }}
            stroke="var(--line)"
          />
          <ReferenceLine
            x={0.8}
            stroke="var(--amber)"
            strokeDasharray="5 4"
            label={{
              value: "0.8 reference",
              position: "top",
              fill: "var(--amber)",
              fontSize: 11,
            }}
          />
          <Tooltip
            contentStyle={tooltipStyle}
            formatter={(value) => Number(value).toFixed(2)}
          />
          <Bar dataKey="ratio" name="Shortlist ratio" radius={[0, 4, 4, 0]}>
            {data.map((entry) => (
              <Cell
                key={entry.label}
                fill={entry.ratio < 0.8 ? "var(--coral)" : "var(--teal)"}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export interface AccuracyDatum {
  label: string;
  accuracy: number;
}

export function AccuracyChart({
  data,
  afterTone = "teal",
}: {
  data: AccuracyDatum[];
  afterTone?: "teal" | "coral";
}) {
  return (
    <div className="h-[18rem] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 10, right: 16, bottom: 10, left: 0 }}>
          <CartesianGrid vertical={false} stroke="var(--line)" />
          <XAxis dataKey="label" tick={axisStyle} stroke="var(--line)" />
          <YAxis
            domain={[0, 1]}
            tick={axisStyle}
            tickFormatter={(value: number) => `${Math.round(value * 100)}%`}
            stroke="var(--line)"
          />
          <Tooltip
            contentStyle={tooltipStyle}
            formatter={(value) => `${(Number(value) * 100).toFixed(1)} percent`}
          />
          <Bar dataKey="accuracy" name="Pairwise accuracy" radius={[4, 4, 0, 0]}>
            {data.map((entry, index) => (
              <Cell
                key={entry.label}
                fill={
                  index === 0
                    ? "var(--muted)"
                    : afterTone === "coral"
                      ? "var(--coral)"
                      : "var(--teal)"
                }
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

