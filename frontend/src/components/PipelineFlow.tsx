import React from "react";
import { Play, CheckCircle, XCircle, Loader2, Cpu } from "lucide-react";
import { motion } from "framer-motion";

export type StageStatus = "pending" | "running" | "completed" | "failed";

export interface PipelineStage {
  id: string;
  name: string;
  agent: string;
  description: string;
  status: StageStatus;
  icon: React.ReactNode;
}

interface PipelineFlowProps {
  stages: PipelineStage[];
  selectedStageId: string | null;
  onSelectStage: (stageId: string) => void;
}

export const PipelineFlow: React.FC<PipelineFlowProps> = ({
  stages,
  selectedStageId,
  onSelectStage,
}) => {
  return (
    <div className="flex flex-col items-center py-6 w-full max-w-lg mx-auto overflow-y-auto h-full scrollbar-thin px-4">
      <div className="text-center mb-6">
        <h3 className="text-xs uppercase font-mono tracking-widest text-gray-500 flex items-center justify-center gap-2">
          <Cpu className="w-4 h-4 text-blue-500 animate-pulse" />
          Autonomous Agent Execution Pipeline
        </h3>
        <p className="text-[11px] text-gray-500 mt-1">
          Click any completed stage to inspect its logs, schemas, or graph models.
        </p>
      </div>

      <div className="relative w-full flex flex-col items-center gap-4">
        {/* Draw vertical connecting line behind stages */}
        <div className="absolute left-[34px] top-4 bottom-4 w-0.5 bg-gradient-to-b from-blue-500/10 via-blue-500/30 to-brand-border z-0" />

        {stages.map((stage, idx) => {
          const isSelected = selectedStageId === stage.id;
          const status = stage.status;
          
          let statusColor = "border-brand-border bg-brand-panel/20 text-gray-500";
          let statusText = "Pending";
          let statusIcon = <Play className="w-3.5 h-3.5 opacity-40" />;

          if (status === "running") {
            statusColor = "border-blue-500 bg-blue-950/20 text-blue-400 animate-glow";
            statusText = "Running";
            statusIcon = <Loader2 className="w-3.5 h-3.5 animate-spin" />;
          } else if (status === "completed") {
            statusColor = "border-emerald-500/50 bg-emerald-950/10 text-emerald-400";
            statusText = "Completed";
            statusIcon = <CheckCircle className="w-3.5 h-3.5" />;
          } else if (status === "failed") {
            statusColor = "border-red-500/50 bg-red-950/10 text-red-400";
            statusText = "Failed";
            statusIcon = <XCircle className="w-3.5 h-3.5" />;
          }

          const canInspect = status === "completed" || status === "running" || stage.id === "planner" || stage.id === "executor";

          return (
            <motion.div
              key={stage.id}
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.05 }}
              onClick={() => canInspect && onSelectStage(stage.id)}
              className={`w-full flex items-center gap-6 p-3.5 rounded-2xl border transition-all duration-300 relative z-10 ${
                isSelected
                  ? "bg-brand-panel border-blue-500/70 shadow-lg shadow-blue-950/20"
                  : canInspect
                  ? "bg-brand-panel/40 border-brand-border/60 hover:border-brand-border hover:bg-brand-panel/75 cursor-pointer"
                  : "bg-brand-panel/10 border-brand-border/20 opacity-60 pointer-events-none"
              }`}
            >
              {/* Icon Circle */}
              <div
                className={`w-10 h-10 rounded-xl flex items-center justify-center border shrink-0 transition-colors duration-300 ${
                  status === "running"
                    ? "bg-blue-500/10 border-blue-500 text-blue-400"
                    : status === "completed"
                    ? "bg-emerald-500/10 border-emerald-500/50 text-emerald-400"
                    : status === "failed"
                    ? "bg-red-500/10 border-red-500/50 text-red-400"
                    : "bg-brand-panel/30 border-brand-border text-gray-500"
                }`}
              >
                {stage.icon}
              </div>

              {/* Text Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <h4 className="font-semibold text-xs text-gray-200">
                    {stage.name}
                  </h4>
                  <span className="text-[9px] font-mono text-gray-500 uppercase tracking-wider">
                    {stage.agent}
                  </span>
                </div>
                <p className="text-[11px] text-gray-500 truncate mt-0.5">
                  {stage.description}
                </p>
              </div>

              {/* Status Badge */}
              <div
                className={`py-1 px-2.5 rounded-full border text-[9px] font-mono flex items-center gap-1.5 shrink-0 ${statusColor}`}
              >
                {statusIcon}
                <span>{statusText}</span>
              </div>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
};
