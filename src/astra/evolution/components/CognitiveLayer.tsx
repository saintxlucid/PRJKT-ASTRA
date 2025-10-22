import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Brain, Activity, Layers, WifiOff } from "lucide-react";
import * as d3 from 'd3';
import { useCognitiveStream, useCognitiveSSE, type CognitiveMetrics } from '../hooks/useCognitiveStream';

// Attention Head Heatmap
const AttentionHeatmap: React.FC<{
  headData: CognitiveMetrics['heads'][0];
  width: number;
  height: number;
}> = ({ headData, width, height }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear canvas
    ctx.clearRect(0, 0, width, height);

    // Calculate cell dimensions
    const tokenCount = headData.values.length;
    const cellWidth = width / tokenCount;
    const cellHeight = height;

    // Draw attention values
    headData.values.forEach((value, i) => {
      // Map -1..1 to color
      const normalizedValue = (value + 1) / 2; // -1..1 -> 0..1
      const r = Math.round(255 * normalizedValue);
      const b = Math.round(255 * (1 - normalizedValue));
      const g = 64; // Fixed green component for consistency

      ctx.fillStyle = `rgb(${r},${g},${b})`;
      ctx.fillRect(i * cellWidth, 0, cellWidth, cellHeight);
    });

    // Add grid lines
    ctx.strokeStyle = 'rgba(255,255,255,0.1)';
    ctx.lineWidth = 0.5;
    for (let i = 0; i <= tokenCount; i++) {
      ctx.beginPath();
      ctx.moveTo(i * cellWidth, 0);
      ctx.lineTo(i * cellWidth, height);
      ctx.stroke();
    }
  }, [headData, width, height]);

  return (
    <canvas 
      ref={canvasRef}
      width={width}
      height={height}
      className="rounded-lg border border-zinc-800"
    />
  );
};

// Memory Weight Bars
const MemoryWeightBars: React.FC<{
  weights: CognitiveMetrics['memoryWeights'];
  width: number;
  height: number;
}> = ({ weights, width, height }) => {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!svgRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const margin = { top: 10, right: 20, bottom: 20, left: 60 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    const x = d3.scaleLinear()
      .domain([0, 1])
      .range([0, innerWidth]);

    const y = d3.scaleBand()
      .domain(weights.map(w => w.key))
      .range([0, innerHeight])
      .padding(0.1);

    const g = svg.append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    // Add bars
    g.selectAll("rect")
      .data(weights)
      .enter()
      .append("rect")
      .attr("y", d => y(d.key) || 0)
      .attr("height", y.bandwidth())
      .attr("width", d => x(d.weight))
      .attr("fill", "rgb(99, 102, 241)") // Indigo-500
      .attr("rx", 2);

    // Add labels
    g.selectAll("text")
      .data(weights)
      .enter()
      .append("text")
      .attr("y", d => (y(d.key) || 0) + y.bandwidth() / 2)
      .attr("x", -5)
      .attr("dy", "0.35em")
      .attr("text-anchor", "end")
      .attr("fill", "currentColor")
      .attr("font-size", "12px")
      .text(d => d.key);

    // Add weight values
    g.selectAll(".weight-label")
      .data(weights)
      .enter()
      .append("text")
      .attr("class", "weight-label")
      .attr("y", d => (y(d.key) || 0) + y.bandwidth() / 2)
      .attr("x", d => x(d.weight) + 5)
      .attr("dy", "0.35em")
      .attr("fill", "currentColor")
      .attr("font-size", "12px")
      .text(d => d.weight.toFixed(2));

  }, [weights, width, height]);

  return (
    <svg 
      ref={svgRef}
      width={width}
      height={height}
      className="text-zinc-400"
    />
  );
};

// Module Activation Lines
const ModuleActivations: React.FC<{
  activations: CognitiveMetrics['moduleActivations'];
  width: number;
  height: number;
}> = ({ activations, width, height }) => {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!svgRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const margin = { top: 10, right: 30, bottom: 20, left: 40 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;

    const x = d3.scaleLinear()
      .domain([0, activations.length - 1])
      .range([0, innerWidth]);

    const y = d3.scaleLinear()
      .domain([0, 1])
      .range([innerHeight, 0]);

    interface ModuleData {
    t: number;
    value: number;
  }
  
  const line = d3.line<ModuleData>()
      .x((d: ModuleData) => x(d.t))
      .y((d: ModuleData) => y(d.value))
      .curve(d3.curveMonotoneX);

    const g = svg.append("g")
      .attr("transform", `translate(${margin.left},${margin.top})`);

    // Add grid lines
    g.append("g")
      .attr("class", "grid")
      .attr("opacity", 0.1)
      .call(d3.axisLeft(y).ticks(5).tickSize(-innerWidth));

    // Draw lines for each module
      const modules = ['planner', 'memory', 'tools'] as const;
    type ModuleName = typeof modules[number];
    
    const colors: Record<ModuleName, string> = {
      planner: 'rgb(99, 102, 241)', // Indigo-500
      memory: 'rgb(236, 72, 153)',  // Pink-500
      tools: 'rgb(34, 197, 94)'     // Green-500
    };

    modules.forEach(module => {
      const moduleData = activations.map((a: CognitiveMetrics['moduleActivations'][0]) => ({
        t: a.t,
        value: a[module]
      }));      // Add line
      g.append("path")
        .datum(moduleData)
        .attr("fill", "none")
        .attr("stroke", colors[module])
        .attr("stroke-width", 2)
        .attr("d", line);

      // Add dots
      g.selectAll(`.dot-${module}`)
        .data(moduleData)
        .enter()
        .append("circle")
        .attr("class", `dot-${module}`)
        .attr("cx", (d: ModuleData) => x(d.t))
        .attr("cy", (d: ModuleData) => y(d.value))
        .attr("r", 3)
        .attr("fill", colors[module]);
    });

    // Add legend
    const legend = g.append("g")
      .attr("font-size", "10px")
      .attr("text-anchor", "start")
      .selectAll("g")
      .data(modules)
      .enter()
      .append("g")
      .attr("transform", (d: ModuleName, i: number) => `translate(${i * 80},${-margin.top})`);

    legend.append("circle")
      .attr("cx", 0)
      .attr("cy", 0)
      .attr("r", 3)
      .attr("fill", (d: ModuleName) => colors[d]);

    legend.append("text")
      .attr("x", 8)
      .attr("y", 0)
      .attr("dy", "0.32em")
      .text((d: ModuleName) => d);

  }, [activations, width, height]);

  return (
    <svg 
      ref={svgRef}
      width={width}
      height={height}
      className="text-zinc-400"
    />
  );
};

interface CognitiveLayerProps {
  mode?: 'websocket' | 'sse';
  animationSpeed?: number;
}

export const CognitiveLayer: React.FC<CognitiveLayerProps> = ({
  mode = 'websocket',
  animationSpeed = 1000,
}) => {
  const [metrics, setMetrics] = useState<CognitiveMetrics | null>(null);
  const isLive = true;

  // Set up streaming connection
  const { isConnected, error } = mode === 'websocket'
    ? useCognitiveStream({
        onMetrics: setMetrics,
        onError: console.error
      })
    : useCognitiveSSE({
        onMetrics: setMetrics,
        onError: console.error
      });

  // If no metrics yet or error, show appropriate state
  if (!metrics) {
    return (
      <div className="flex flex-col items-center justify-center p-6 space-y-4">
        {error ? (
          <>
            <WifiOff className="w-12 h-12 text-red-500" />
            <p className="text-red-500">Failed to connect: {error.message}</p>
          </>
        ) : (
          <div className="animate-pulse text-zinc-400">
            <Activity className="w-12 h-12" />
            <p>Connecting to cognitive stream...</p>
          </div>
        )}
      </div>
    );
  }
  const [selectedHead, setSelectedHead] = useState(0);
  
  return (
    <div className="space-y-6 p-6">
      {/* Status Badge */}
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <Brain className="w-5 h-5" />
          Cognitive Layer
        </h3>
        {isLive && (
          <Badge variant="outline" className="animate-pulse bg-green-500/10">
            <Activity className="w-3 h-3 mr-1" />
            Live Stream
          </Badge>
        )}
      </div>

      {/* Attention Head Section */}
      <Card className="bg-black/50 border-zinc-800">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">Attention Head Heatmap</CardTitle>
            <Select 
              value={selectedHead.toString()} 
              onValueChange={(v: string) => setSelectedHead(parseInt(v, 10))}
            >
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {metrics.heads.map((head: CognitiveMetrics['heads'][0]) => (
                  <SelectItem key={head.index} value={head.index.toString()}>
                    Head {head.index}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          <AttentionHeatmap 
            headData={metrics.heads[selectedHead]} 
            width={600}
            height={60}
          />
        </CardContent>
      </Card>

      {/* Memory Weights Section */}
      <Card className="bg-black/50 border-zinc-800">
        <CardHeader>
          <CardTitle className="text-base">Memory Weight Distribution</CardTitle>
        </CardHeader>
        <CardContent>
          <MemoryWeightBars 
            weights={metrics.memoryWeights} 
            width={600}
            height={200}
          />
        </CardContent>
      </Card>

      {/* Module Activations Section */}
      <Card className="bg-black/50 border-zinc-800">
        <CardHeader>
          <CardTitle className="text-base">Module Activation Timeline</CardTitle>
        </CardHeader>
        <CardContent>
          <ModuleActivations 
            activations={metrics.moduleActivations} 
            width={600}
            height={200}
          />
        </CardContent>
      </Card>
    </div>
  );
};