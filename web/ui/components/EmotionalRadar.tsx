/**
 * Emotional Radar Component
 * 
 * Live emotional/cognitive state visualization using radar chart.
 * Displays real-time metrics from ASTRA's internal monitoring.
 */

import React from "react";
import {
  Radar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Tooltip,
  Legend
} from "recharts";

/**
 * Signal data point for radar chart
 */
export interface EmotionalSignal {
  /** Signal label (e.g., "Calm", "Focus") */
  label: string;
  /** Signal value normalized 0.0-1.0 */
  value: number;
  /** Optional threshold for alert (0.0-1.0) */
  threshold?: number;
}

/**
 * Props for EmotionalRadar component
 */
export interface EmotionalRadarProps {
  /** Array of emotional/cognitive signals */
  signals: EmotionalSignal[];
  /** Chart title (optional) */
  title?: string;
  /** Enable live updates (optional) */
  live?: boolean;
  /** Update interval in ms (optional, default: 1000) */
  updateInterval?: number;
  /** Custom color scheme (optional) */
  colorScheme?: {
    stroke?: string;
    fill?: string;
    grid?: string;
    text?: string;
  };
  /** Show thresholds on chart (optional) */
  showThresholds?: boolean;
}

/**
 * EmotionalRadar Component
 * 
 * Renders a radar chart visualization of emotional/cognitive signals.
 * Supports live updates and customizable theming.
 * 
 * @example
 * ```tsx
 * <EmotionalRadar
 *   signals={[
 *     { label: "Calm", value: 0.72 },
 *     { label: "Focus", value: 0.81 },
 *     { label: "Fatigue", value: 0.18 }
 *   ]}
 *   title="Cognitive State"
 *   live={true}
 * />
 * ```
 */
export default function EmotionalRadar({
  signals,
  title = "Emotional Radar",
  live = false,
  updateInterval = 1000,
  colorScheme = {
    stroke: "#a78bfa",
    fill: "#a78bfa",
    grid: "#ffffff20",
    text: "#ffffff90"
  },
  showThresholds = false
}: EmotionalRadarProps) {
  // Convert signals to format Recharts expects
  const chartData = signals.map(signal => ({
    label: signal.label,
    value: signal.value * 100, // Convert to 0-100 scale
    fullMark: 100,
    threshold: signal.threshold ? signal.threshold * 100 : undefined
  }));

  // Calculate overall state
  const avgValue = signals.reduce((sum, s) => sum + s.value, 0) / signals.length;
  const overallState = avgValue >= 0.7 ? "optimal" : avgValue >= 0.4 ? "moderate" : "low";
  
  const stateColors = {
    optimal: "#10b981",
    moderate: "#f59e0b",
    low: "#ef4444"
  };

  return (
    <div className="rounded-2xl p-4 bg-neutral-950/70 ring-1 ring-white/10 backdrop-blur-sm">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-white/90 text-sm font-medium">{title}</h3>
        <div className="flex items-center gap-2">
          {live && (
            <span className="flex items-center gap-1.5 text-xs text-white/60">
              <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              Live
            </span>
          )}
          <span 
            className="text-xs px-2 py-0.5 rounded-full"
            style={{
              backgroundColor: `${stateColors[overallState]}20`,
              color: stateColors[overallState]
            }}
          >
            {overallState.toUpperCase()}
          </span>
        </div>
      </div>

      {/* Radar Chart */}
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={chartData}>
            <PolarGrid 
              stroke={colorScheme.grid}
              strokeDasharray="3 3"
            />
            <PolarAngleAxis
              dataKey="label"
              tick={{ fill: colorScheme.text, fontSize: 11 }}
            />
            <PolarRadiusAxis
              angle={90}
              domain={[0, 100]}
              tick={{ fill: colorScheme.text, fontSize: 10 }}
              tickCount={6}
            />
            
            {/* Main signal line */}
            <Radar
              name="Signal"
              dataKey="value"
              stroke={colorScheme.stroke}
              fill={colorScheme.fill}
              fillOpacity={0.35}
              strokeWidth={2}
            />
            
            {/* Threshold overlay if enabled */}
            {showThresholds && (
              <Radar
                name="Threshold"
                dataKey="threshold"
                stroke="#ef444480"
                fill="transparent"
                strokeDasharray="4 4"
                strokeWidth={1}
              />
            )}
            
            <Tooltip
              contentStyle={{
                backgroundColor: "#18181bdd",
                border: "1px solid #ffffff20",
                borderRadius: "8px",
                padding: "8px 12px"
              }}
              labelStyle={{ color: "#ffffff90", fontSize: "12px" }}
              itemStyle={{ color: colorScheme.stroke, fontSize: "11px" }}
              formatter={(value: number) => `${(value / 100).toFixed(2)}`}
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      {/* Signal Details */}
      <div className="mt-3 pt-3 border-t border-white/10">
        <div className="grid grid-cols-2 gap-2">
          {signals.map((signal, idx) => {
            const isAlert = signal.threshold && signal.value < signal.threshold;
            return (
              <div
                key={idx}
                className="flex items-center justify-between text-xs"
              >
                <span className="text-white/60">{signal.label}</span>
                <span
                  className={`font-mono font-medium ${
                    isAlert ? "text-red-400" : "text-white/90"
                  }`}
                >
                  {(signal.value * 100).toFixed(0)}%
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Sacred Code */}
      <div className="mt-2 text-center text-[10px] text-white/30 font-mono">
        333 ∞
      </div>
    </div>
  );
}
