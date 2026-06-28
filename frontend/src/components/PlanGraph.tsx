import React from "react";
import { PlayCircle, CheckCircle2, XCircle, Clock, Database, Code, BarChart2, MessageSquare, HelpCircle } from "lucide-react";

interface ToolStep {
  id: string;
  tool: string;
  dependencies: string[];
  description: string;
  chart_type?: string;
  operation?: string;
  question?: string;
}

interface StepTiming {
  step_id: string;
  tool: string;
  success: boolean;
  duration_ms: number;
  error?: string | null;
  output?: any;
}

interface PlanGraphProps {
  steps: ToolStep[];
  stepTimings: StepTiming[];
  activeStepId?: string | null;
  onNodeClick: (stepId: string) => void;
}

export const PlanGraph: React.FC<PlanGraphProps> = ({
  steps,
  stepTimings,
  onNodeClick,
}) => {
  if (!steps || steps.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-center text-gray-500 h-64 select-none">
        <HelpCircle className="w-10 h-10 mb-3 stroke-[1.2]" />
        <p className="text-xs">No active execution graph model loaded.</p>
      </div>
    );
  }

  // 1. Calculate ranks for columns
  const ranks: { [key: string]: number } = {};
  steps.forEach((s) => {
    ranks[s.id] = 0;
  });

  let changed = true;
  for (let iter = 0; iter < 10 && changed; iter++) {
    changed = false;
    steps.forEach((s) => {
      const currentRank = ranks[s.id];
      let maxDepRank = -1;
      s.dependencies.forEach((depId) => {
        if (ranks[depId] !== undefined) {
          maxDepRank = Math.max(maxDepRank, ranks[depId]);
        }
      });
      const newRank = maxDepRank + 1;
      if (newRank > currentRank) {
        ranks[s.id] = newRank;
        changed = true;
      }
    });
  }

  // Group steps by rank
  const maxRank = Math.max(...Object.values(ranks), 0);
  const cols: ToolStep[][] = Array.from({ length: maxRank + 1 }, () => []);
  steps.forEach((s) => {
    const r = ranks[s.id] || 0;
    cols[r].push(s);
  });

  // 2. Assign coordinates (Larger DAG Grid Layout)
  const cardWidth = 210;
  const cardHeight = 90;
  const gapX = 100;
  const gapY = 55;
  
  const colWidth = cardWidth + gapX;
  const rowHeight = cardHeight + gapY;

  const nodePositions: { [id: string]: { x: number; y: number } } = {};
  
  cols.forEach((colSteps, colIdx) => {
    colSteps.forEach((step, rowIdx) => {
      nodePositions[step.id] = {
        x: colIdx * colWidth + 30,
        y: rowIdx * rowHeight + 40,
      };
    });
  });

  // Calculate container dimensions
  const maxRows = Math.max(...cols.map((c) => c.length), 0);
  const containerWidth = cols.length * colWidth + 60;
  const containerHeight = maxRows * rowHeight + 60;

  // Retrieve step status
  const getStepStatus = (stepId: string) => {
    const timing = stepTimings.find((t) => t.step_id === stepId);
    if (!timing) return "pending";
    if (timing.duration_ms > 0) {
      return timing.success ? "completed" : "failed";
    }
    return "running";
  };

  const getToolIcon = (tool: string) => {
    switch (tool) {
      case "profile":
        return <Database className="w-3.5 h-3.5" />;
      case "visualize":
      case "visualization":
        return <BarChart2 className="w-3.5 h-3.5" />;
      case "analyze":
        return <MessageSquare className="w-3.5 h-3.5" />;
      default:
        return <Code className="w-3.5 h-3.5" />;
    }
  };

  // Color-code agents: Green (Dataset), Blue (Planner), Purple (Executor), Orange (Analysis), Red (Visualization)
  const getColorStyles = (tool: string, status: string) => {
    let colorName = "gray";
    if (tool === "profile") {
      colorName = "green"; // Green (Dataset)
    } else if (tool === "execute_python" || tool === "python_analysis") {
      colorName = "purple"; // Purple (Executor)
    } else if (tool === "visualize") {
      colorName = "red"; // Red (Visualization)
    } else if (tool === "analyze") {
      colorName = "orange"; // Orange (Analysis)
    }

    if (status === "pending") {
      return {
        borderClass: "border-brand-border bg-brand-card/90 opacity-60",
        textClass: "text-gray-500",
        badgeBg: "bg-brand-panel text-gray-500 border-brand-border/40",
        iconColor: "text-gray-600",
        arrowColor: "#1D283A"
      };
    }

    if (status === "running") {
      return {
        borderClass: "border-blue-500 bg-blue-950/20 shadow-[0_0_15px_rgba(59,130,246,0.3)] animate-pulse",
        textClass: "text-blue-300",
        badgeBg: "bg-blue-500/10 text-blue-400 border-blue-500/30",
        iconColor: "text-blue-400",
        arrowColor: "#3B82F6"
      };
    }

    if (status === "failed") {
      return {
        borderClass: "border-red-500/50 bg-red-950/10 hover:border-red-500",
        textClass: "text-red-400",
        badgeBg: "bg-red-500/10 text-red-400 border-red-500/30",
        iconColor: "text-red-400",
        arrowColor: "#EF4444"
      };
    }

    // Status Completed (Color-coded based on agent type)
    switch (colorName) {
      case "green":
        return {
          borderClass: "border-emerald-500/40 bg-emerald-950/5 hover:border-emerald-500",
          textClass: "text-emerald-300 font-semibold",
          badgeBg: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
          iconColor: "text-emerald-400",
          arrowColor: "#10B981"
        };
      case "purple":
        return {
          borderClass: "border-purple-500/40 bg-purple-950/5 hover:border-purple-500",
          textClass: "text-purple-300 font-semibold",
          badgeBg: "bg-purple-500/10 text-purple-400 border-purple-500/20",
          iconColor: "text-purple-400",
          arrowColor: "#8B5CF6"
        };
      case "red":
        return {
          borderClass: "border-rose-500/40 bg-rose-950/5 hover:border-rose-500",
          textClass: "text-rose-300 font-semibold",
          badgeBg: "bg-rose-500/10 text-rose-400 border-rose-500/20",
          iconColor: "text-rose-400",
          arrowColor: "#EF4444"
        };
      case "orange":
        return {
          borderClass: "border-amber-500/40 bg-amber-950/5 hover:border-amber-500",
          textClass: "text-amber-300 font-semibold",
          badgeBg: "bg-amber-500/10 text-amber-400 border-amber-500/20",
          iconColor: "text-amber-400",
          arrowColor: "#F59E0B"
        };
      default:
        return {
          borderClass: "border-brand-border bg-brand-card hover:border-brand-border/80",
          textClass: "text-gray-300",
          badgeBg: "bg-brand-panel text-gray-400 border-brand-border",
          iconColor: "text-gray-400",
          arrowColor: "#1D283A"
        };
    }
  };

  const getFriendlyLabels = (step: ToolStep) => {
    let agentName = "Tool Executor";
    let subLabel = step.id;

    if (step.tool === "profile") {
      agentName = "Dataset Profiler";
      subLabel = "Ingest Schema";
    } else if (step.tool === "execute_python" || step.tool === "python_analysis") {
      agentName = "Python Execution";
      subLabel = step.operation ? `Run: ${step.operation}` : "Data Transform";
    } else if (step.tool === "visualize") {
      agentName = "Visualization Agent";
      subLabel = step.chart_type ? `${step.chart_type.toUpperCase()} Chart` : "Render Chart";
    } else if (step.tool === "analyze") {
      agentName = "Analysis Agent";
      subLabel = "Business Insights";
    }

    return { agentName, subLabel };
  };

  return (
    <div className="w-full overflow-x-auto scrollbar-thin py-6 relative bg-[#07090F]/45 border border-brand-border/60 rounded-3xl">
      <div 
        className="relative mx-auto select-none"
        style={{ width: containerWidth, height: containerHeight }}
      >
        {/* SVG connectors layer */}
        <svg 
          className="absolute inset-0 pointer-events-none z-0"
          style={{ width: containerWidth, height: containerHeight }}
        >
          <defs>
            <marker
              id="arrow"
              viewBox="0 0 10 10"
              refX="6"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#1D283A" />
            </marker>
            <marker
              id="arrow-active"
              viewBox="0 0 10 10"
              refX="6"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#3B82F6" />
            </marker>
          </defs>

          {/* Draw dependency lines */}
          {steps.map((step) => {
            const endPos = nodePositions[step.id];
            if (!endPos) return null;

            return step.dependencies.map((depId) => {
              const startPos = nodePositions[depId];
              if (!startPos) return null;

              const x1 = startPos.x + cardWidth;
              const y1 = startPos.y + cardHeight / 2;

              const x2 = endPos.x;
              const y2 = endPos.y + cardHeight / 2;

              const cx1 = x1 + gapX / 2;
              const cy1 = y1;
              const cx2 = x2 - gapX / 2;
              const cy2 = y2;

              const status = getStepStatus(step.id);
              const parentStatus = getStepStatus(depId);
              const isActive = parentStatus === "completed" && status === "running";

              return (
                <path
                  key={`${depId}-${step.id}`}
                  d={`M ${x1} ${y1} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${x2} ${y2}`}
                  fill="none"
                  stroke={isActive ? "#3B82F6" : "#1D283A"}
                  strokeWidth={isActive ? 2 : 1.5}
                  markerEnd={`url(#${isActive ? "arrow-active" : "arrow"})`}
                  strokeDasharray={isActive ? "5, 5" : "none"}
                  className={isActive ? "animate-[dash_1s_linear_infinite]" : ""}
                  style={{
                    strokeDashoffset: isActive ? 20 : 0,
                  }}
                />
              );
            });
          })}
        </svg>

        {/* Nodes Layer */}
        {steps.map((step) => {
          const pos = nodePositions[step.id];
          if (!pos) return null;

          const status = getStepStatus(step.id);
          const timing = stepTimings.find((t) => t.step_id === step.id);
          const duration = timing?.duration_ms || 0;

          const { borderClass, textClass, badgeBg, iconColor } = getColorStyles(step.tool, status);
          const { agentName, subLabel } = getFriendlyLabels(step);

          return (
            <div
              key={step.id}
              onClick={() => onNodeClick(step.id)}
              className={`absolute p-3.5 rounded-2xl border flex flex-col justify-between cursor-pointer transition-all duration-300 z-10 hover:scale-[1.02] hover:shadow-lg ${borderClass}`}
              style={{
                left: pos.x,
                top: pos.y,
                width: cardWidth,
                height: cardHeight,
              }}
            >
              {/* Card Header (Category & Status) */}
              <div className="flex justify-between items-center">
                <span className={`text-[9px] font-mono font-bold uppercase tracking-wider flex items-center gap-1.5 ${textClass}`}>
                  <span className={iconColor}>{getToolIcon(step.tool)}</span>
                  {agentName}
                </span>
                {status === "running" && (
                  <PlayCircle className="w-4.5 h-4.5 text-blue-400 animate-spin" />
                )}
                {status === "completed" && (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                )}
                {status === "failed" && (
                  <XCircle className="w-4 h-4 text-red-400" />
                )}
              </div>

              {/* Node Friendly Objective Label */}
              <div className="font-bold text-[11px] text-gray-200 truncate mt-1 leading-normal">
                {subLabel}
              </div>

              {/* Card Footer: duration / dependencies */}
              <div className="flex justify-between items-center text-[9px] text-gray-600 font-mono mt-1 pt-1.5 border-t border-brand-border/30">
                <span className={`px-1.5 py-0.5 rounded border text-[8px] font-mono leading-none ${badgeBg}`}>
                  {step.id}
                </span>
                {duration > 0 && (
                  <span className="text-blue-400/80 flex items-center gap-0.5 font-bold">
                    <Clock className="w-2.5 h-2.5" />
                    {duration.toFixed(0)}ms
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
      
      <style>{`
        @keyframes dash {
          to {
            stroke-dashoffset: -20;
          }
        }
      `}</style>
    </div>
  );
};
