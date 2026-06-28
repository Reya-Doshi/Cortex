import { Clock, Cpu, Award, FileSpreadsheet, HardDrive, BarChart2, Zap, Database } from "lucide-react";

interface StepTiming {
  step_id: string;
  tool: string;
  success: boolean;
  duration_ms: number;
}

interface MetricsPanelProps {
  totalDurationMs: number;
  confidence: number;
  filesCount: number;
  rowsCount: number;
  steps: StepTiming[];
}

export const MetricsPanel: React.FC<MetricsPanelProps> = ({
  totalDurationMs,
  confidence,
  filesCount,
  rowsCount,
  steps,
}) => {
  const successfulSteps = steps.filter((s) => s.success).length;

  // Calculate speedup
  const sequentialTime = steps.reduce((acc, step) => acc + step.duration_ms, 0);
  const speedup = totalDurationMs > 0 && sequentialTime > 0 ? (sequentialTime / totalDurationMs) : 1.0;

  return (
    <div className="w-80 bg-brand-card border-l border-brand-border h-full flex flex-col p-6 overflow-y-auto scrollbar-thin shrink-0">
      <h3 className="text-[10px] uppercase font-mono tracking-wider text-gray-500 mb-6 border-b border-brand-border pb-3 flex items-center gap-2">
        <Cpu className="w-4 h-4 text-blue-500" />
        Performance Dashboard
      </h3>

      <div className="space-y-6">
        {/* Core numbers */}
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-brand-panel/30 border border-brand-border p-4 rounded-2xl flex flex-col gap-1.5">
            <span className="text-[9px] font-mono text-gray-500 uppercase flex items-center gap-1">
              <Clock className="w-3.5 h-3.5 text-blue-400" /> Time
            </span>
            <span className="text-sm font-bold text-gray-200">
              {totalDurationMs > 0 ? `${totalDurationMs.toFixed(0)} ms` : "0.0 ms"}
            </span>
          </div>

          <div className="bg-brand-panel/30 border border-brand-border p-4 rounded-2xl flex flex-col gap-1.5">
            <span className="text-[9px] font-mono text-gray-500 uppercase flex items-center gap-1">
              <Award className="w-3.5 h-3.5 text-blue-400" /> Heuristic Confidence
            </span>
            <span className="text-sm font-bold text-gray-200">
              {confidence > 0 ? `${(confidence * 100).toFixed(0)}%` : "0%"}
            </span>
          </div>
        </div>

        {/* Speedup and concurrency metrics */}
        {totalDurationMs > 0 && steps.length > 1 && (
          <div className="bg-blue-500/5 border border-blue-500/20 p-4 rounded-2xl flex flex-col gap-1">
            <span className="text-[9px] font-mono text-blue-400 uppercase flex items-center gap-1">
              <Zap className="w-3.5 h-3.5" /> Parallel Speedup
            </span>
            <span className="text-sm font-bold text-blue-400">
              {speedup.toFixed(2)}x Speedup
            </span>
            <p className="text-[10px] text-gray-500 font-mono mt-1 leading-normal">
              Seq Time: {sequentialTime.toFixed(0)}ms
              <br />
              Par Time: {totalDurationMs.toFixed(0)}ms
            </p>
          </div>
        )}

        {/* Process Details */}
        <div className="bg-brand-panel/10 border border-brand-border p-4 rounded-2xl space-y-4">
          <div className="flex justify-between items-center text-xs">
            <span className="text-gray-500 flex items-center gap-2">
              <FileSpreadsheet className="w-4 h-4 text-gray-500" /> Files
            </span>
            <span className="font-mono font-semibold text-gray-300">{filesCount}</span>
          </div>

          <div className="flex justify-between items-center text-xs">
            <span className="text-gray-500 flex items-center gap-2">
              <Database className="w-4 h-4 text-gray-500" /> Rows Processed
            </span>
            <span className="font-mono font-semibold text-gray-300">
              {rowsCount.toLocaleString()}
            </span>
          </div>

          <div className="flex justify-between items-center text-xs">
            <span className="text-gray-500 flex items-center gap-2">
              <Cpu className="w-4 h-4 text-gray-500" /> Nodes Executed
            </span>
            <span className="font-mono font-semibold text-gray-300">
              {successfulSteps} / {steps.length}
            </span>
          </div>

          {/* Hardware metrics placeholders */}
          <div className="pt-3 border-t border-brand-border/60 space-y-3">
            <div className="flex flex-col gap-1.5">
              <div className="flex justify-between items-center text-xs">
                <span className="text-gray-500 flex items-center gap-2">
                  <HardDrive className="w-4 h-4 text-gray-500" /> Memory Usage
                </span>
                <span className="font-mono font-semibold text-blue-400 text-[10px]">
                  32.4 MB / 512 MB
                </span>
              </div>
              <div className="w-full h-1.5 bg-brand-border rounded-full overflow-hidden">
                <div className="h-full bg-blue-500 rounded-full" style={{ width: "6.3%" }} />
              </div>
            </div>

            <div className="flex flex-col gap-1.5">
              <div className="flex justify-between items-center text-xs">
                <span className="text-gray-500 flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-gray-500" /> CPU Usage (Mock)
                </span>
                <span className="font-mono font-semibold text-emerald-400 text-[10px]">
                  4.8% / 100%
                </span>
              </div>
              <div className="w-full h-1.5 bg-brand-border rounded-full overflow-hidden">
                <div className="h-full bg-emerald-500 rounded-full" style={{ width: "4.8%" }} />
              </div>
            </div>
          </div>
        </div>

        {/* Timing per tool step chart */}
        {steps.length > 0 && (
          <div className="space-y-3">
            <h4 className="text-[10px] uppercase font-mono tracking-wider text-gray-500 flex items-center gap-1.5">
              <BarChart2 className="w-4 h-4 text-gray-500" />
              Time Per Agent Step
            </h4>
            <div className="space-y-3.5 bg-brand-panel/20 border border-brand-border p-4 rounded-2xl">
              {steps.map((step) => {
                const totalStepsTime = steps.reduce((a, b) => a + b.duration_ms, 0);
                const pct = totalStepsTime > 0 ? (step.duration_ms / totalStepsTime) * 100 : 0;

                return (
                  <div key={step.step_id} className="space-y-1.5">
                    <div className="flex justify-between items-center text-[10px] font-mono">
                      <span className="text-gray-300 font-semibold truncate max-w-[150px] uppercase">
                        {step.tool}
                      </span>
                      <span className="text-gray-500">
                        {step.duration_ms.toFixed(0)}ms
                      </span>
                    </div>
                    <div className="w-full h-1 bg-brand-border rounded-full overflow-hidden">
                      <div
                        className="h-full bg-blue-500 rounded-full transition-all duration-500"
                        style={{ width: `${Math.max(pct, 2)}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
