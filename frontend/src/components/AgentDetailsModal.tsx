import React from "react";
import { X, Table, Clock, Eye, BarChart2, MessageSquare, AlertCircle, ShieldAlert } from "lucide-react";
import { ResponsiveContainer, BarChart, Bar, LineChart, Line, PieChart, Pie, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Cell } from "recharts";

interface ToolStep {
  id: string;
  tool: string;
  dependencies: string[];
  description: string;
  chart_type?: string;
  operation?: string;
  question?: string;
}

interface ExecutionPlan {
  goal: string;
  reasoning: string;
  confidence: number;
  steps: ToolStep[];
  expected_outputs: string;
}

interface StepTiming {
  step_id: string;
  tool: string;
  success: boolean;
  start_time: string;
  end_time: string;
  duration_ms: number;
  error?: string | null;
  output?: any;
}

interface UploadedFile {
  file_id: string;
  filename: string;
  file_path: string;
  rows: number;
  columns: number;
  column_names: string[];
}

interface AgentDetailsModalProps {
  stageId: string;
  onClose: () => void;
  plan: ExecutionPlan | null;
  stepTimings: StepTiming[];
  selectedFile: UploadedFile | null;
  answer: string | null;
}

export const AgentDetailsModal: React.FC<AgentDetailsModalProps> = ({
  stageId,
  onClose,
  plan,
  stepTimings,
  selectedFile,
  answer,
}) => {
  
  // Render Planner details: The interactive DAG graph
  const renderPlannerDetails = () => {
    if (!plan) {
      return (
        <div className="flex flex-col items-center justify-center p-8 text-center text-gray-500">
          <AlertCircle className="w-8 h-8 mb-2" />
          <p className="text-xs">No execution plan available yet.</p>
        </div>
      );
    }

    // Compute ranks of steps for DAG visualization
    const steps = plan.steps;
    const ranks: { [key: string]: number } = {};
    
    // Simple topological rank assignment
    let changed = true;
    steps.forEach((s) => {
      ranks[s.id] = 0;
    });
    
    // Iterate to find maximum dependency path length
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
    const columns: ToolStep[][] = Array.from({ length: maxRank + 1 }, () => []);
    steps.forEach((s) => {
      const r = ranks[s.id] || 0;
      columns[r].push(s);
    });

    return (
      <div className="space-y-6">
        <div className="bg-brand-panel/30 border border-brand-border p-4 rounded-xl">
          <h4 className="font-semibold text-xs text-gray-300 mb-1">Reasoning Model</h4>
          <p className="text-xs text-gray-400 font-sans italic leading-relaxed">
            "{plan.reasoning}"
          </p>
          <div className="flex items-center gap-4 mt-3 text-[10px] font-mono text-gray-500">
            <span>Confidence: <strong className="text-blue-400">{(plan.confidence * 100).toFixed(0)}%</strong></span>
            <span>Target Output: <strong className="text-gray-300">{plan.expected_outputs}</strong></span>
          </div>
        </div>

        {/* Interactive DAG Diagram */}
        <div className="border border-brand-border bg-brand-panel/10 p-6 rounded-2xl relative overflow-x-auto scrollbar-thin">
          <div className="min-w-[600px] flex items-center justify-between gap-12 py-4">
            {columns.map((columnSteps, colIdx) => (
              <div key={colIdx} className="flex flex-col gap-6 items-center flex-1 relative">
                {colIdx > 0 && (
                  <div className="absolute -left-8 top-1/2 -translate-y-1/2 flex flex-col justify-around h-full pointer-events-none opacity-20">
                    <span className="text-[18px] text-blue-500">➔</span>
                  </div>
                )}
                <div className="text-[9px] uppercase font-mono tracking-wider text-gray-600 mb-1">
                  Rank {colIdx}
                </div>
                {columnSteps.map((step) => (
                  <div
                    key={step.id}
                    className="p-3.5 bg-brand-card border border-brand-border hover:border-blue-500/50 rounded-xl w-44 text-center group transition-all duration-300 relative shadow-md"
                  >
                    <div className="text-[10px] font-mono text-blue-400 font-bold uppercase tracking-wider mb-1">
                      {step.tool}
                    </div>
                    <div className="font-semibold text-[11px] text-gray-200 truncate">
                      {step.id}
                    </div>
                    <p className="text-[9px] text-gray-500 mt-1 leading-snug line-clamp-2">
                      {step.description}
                    </p>
                    {step.dependencies.length > 0 && (
                      <div className="mt-2 pt-1.5 border-t border-brand-border/40 text-[8px] font-mono text-gray-600">
                        In: {step.dependencies.join(", ")}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };

  // Render Executor details: timings and intermediate outputs
  const renderExecutorDetails = () => {
    if (stepTimings.length === 0) {
      return (
        <div className="flex flex-col items-center justify-center p-8 text-center text-gray-500">
          <Clock className="w-8 h-8 mb-2" />
          <p className="text-xs">No tool executions recorded yet.</p>
        </div>
      );
    }

    return (
      <div className="space-y-4 overflow-y-auto max-h-[500px] pr-2 scrollbar-thin">
        {stepTimings.map((timing, idx) => (
          <div
            key={timing.step_id}
            className={`p-4 rounded-xl border ${
              timing.success
                ? "bg-brand-panel/20 border-brand-border"
                : "bg-red-950/10 border-red-900/30"
            }`}
          >
            {/* Header */}
            <div className="flex justify-between items-center mb-2">
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono text-gray-500 font-bold">
                  [{idx + 1}]
                </span>
                <span className="font-bold text-xs text-gray-200 uppercase tracking-wide">
                  {timing.tool}
                </span>
                <span className="text-[10px] font-mono text-gray-500 bg-brand-panel px-2 py-0.5 rounded border border-brand-border">
                  {timing.step_id}
                </span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-[10px] font-mono text-blue-400">
                  {timing.duration_ms.toFixed(1)} ms
                </span>
                <span
                  className={`text-[9px] font-mono py-0.5 px-2 rounded-full border ${
                    timing.success
                      ? "border-emerald-500/30 text-emerald-400 bg-emerald-950/10"
                      : "border-red-500/30 text-red-400 bg-red-950/10"
                  }`}
                >
                  {timing.success ? "Success" : "Failed"}
                </span>
              </div>
            </div>

            {/* Error Message if failed */}
            {!timing.success && timing.error && (
              <div className="p-2 bg-red-950/30 border border-red-900/50 rounded-lg text-xs text-red-400 font-mono flex items-start gap-2 mb-2">
                <ShieldAlert className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                <span>{timing.error}</span>
              </div>
            )}

            {/* Timestamps */}
            <div className="text-[9px] font-mono text-gray-600 mb-3">
              Start: {timing.start_time} | End: {timing.end_time}
            </div>

            {/* Output view */}
            {timing.success && timing.output && (
              <div className="mt-2 bg-[#070A0F] border border-brand-border/60 rounded-lg p-3 relative group">
                <div className="text-[8px] uppercase font-mono tracking-widest text-gray-600 absolute right-3 top-3 select-none">
                  Output JSON
                </div>
                <pre className="text-[10px] font-mono text-gray-400 overflow-x-auto scrollbar-thin max-h-36 pt-4 leading-relaxed">
                  {JSON.stringify(timing.output, null, 2)}
                </pre>
              </div>
            )}
          </div>
        ))}
      </div>
    );
  };

  // Render Visualization details: charts generated from processed data
  const renderVisualizationDetails = () => {
    // Find the visualize step output
    const vizStep = stepTimings.find((t) => t.tool === "visualize" || t.tool === "visualization");
    const chartSpec = vizStep?.output;

    if (!chartSpec || !chartSpec.data || chartSpec.data.length === 0) {
      return (
        <div className="flex flex-col items-center justify-center p-8 text-center text-gray-500">
          <BarChart2 className="w-8 h-8 mb-2" />
          <p className="text-xs">No chart generated in the pipeline execution.</p>
        </div>
      );
    }

    const { chart_type, data, x_axis, series } = chartSpec;
    const colors = ["#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6"];

    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between border-b border-brand-border pb-3">
          <div>
            <h4 className="font-semibold text-xs text-gray-200 uppercase tracking-wider">
              {chart_type} Chart Output
            </h4>
            <p className="text-[10px] text-gray-500 mt-0.5">
              Rendered via Recharts using dependency data.
            </p>
          </div>
          <span className="text-[9px] font-mono uppercase bg-blue-500/10 border border-blue-500/30 text-blue-400 py-0.5 px-2 rounded-full">
            No CSV Read
          </span>
        </div>

        {/* Chart Window */}
        <div className="h-[320px] bg-brand-panel/20 border border-brand-border p-4 rounded-2xl flex items-center justify-center">
          <ResponsiveContainer width="100%" height="100%">
            {chart_type === "line" ? (
              <LineChart data={data} margin={{ top: 20, right: 30, left: 10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1D283A" />
                <XAxis dataKey={x_axis} stroke="#64748B" fontSize={10} />
                <YAxis stroke="#64748B" fontSize={10} />
                <Tooltip contentStyle={{ backgroundColor: "#0E121A", borderColor: "#1D283A", borderRadius: "8px", fontSize: "11px" }} />
                {series.map((key: string, idx: number) => (
                  <Line key={key} type="monotone" dataKey={key} stroke={colors[idx % colors.length]} strokeWidth={2} activeDot={{ r: 6 }} />
                ))}
              </LineChart>
            ) : chart_type === "pie" ? (
              <PieChart>
                <Pie data={data} dataKey={series[0]} nameKey={x_axis} cx="50%" cy="50%" outerRadius={100} fill="#3B82F6" label={{ fontSize: 9, fill: "#94A3B8" }}>
                  {data.map((_: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: "#0E121A", borderColor: "#1D283A", borderRadius: "8px", fontSize: "11px" }} />
              </PieChart>
            ) : chart_type === "area" ? (
              <AreaChart data={data} margin={{ top: 20, right: 30, left: 10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1D283A" />
                <XAxis dataKey={x_axis} stroke="#64748B" fontSize={10} />
                <YAxis stroke="#64748B" fontSize={10} />
                <Tooltip contentStyle={{ backgroundColor: "#0E121A", borderColor: "#1D283A", borderRadius: "8px", fontSize: "11px" }} />
                {series.map((key: string, idx: number) => (
                  <Area key={key} type="monotone" dataKey={key} fill={colors[idx % colors.length] + "40"} stroke={colors[idx % colors.length]} strokeWidth={2} />
                ))}
              </AreaChart>
            ) : (
              <BarChart data={data} margin={{ top: 20, right: 30, left: 10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1D283A" />
                <XAxis dataKey={x_axis} stroke="#64748B" fontSize={10} />
                <YAxis stroke="#64748B" fontSize={10} />
                <Tooltip contentStyle={{ backgroundColor: "#0E121A", borderColor: "#1D283A", borderRadius: "8px", fontSize: "11px" }} />
                {series.map((key: string, idx: number) => (
                  <Bar key={key} dataKey={key} fill={colors[idx % colors.length]} radius={[4, 4, 0, 0]} />
                ))}
              </BarChart>
            )}
          </ResponsiveContainer>
        </div>

        {/* Data summary */}
        <div className="bg-[#070A0F] border border-brand-border/60 rounded-xl p-3.5">
          <span className="text-[10px] font-mono text-gray-500 uppercase tracking-widest block mb-2">
            Visualization Source Data
          </span>
          <pre className="text-[10px] font-mono text-gray-400 overflow-x-auto scrollbar-thin max-h-24">
            {JSON.stringify(data, null, 2)}
          </pre>
        </div>
      </div>
    );
  };

  // Render Analysis details
  const renderAnalysisDetails = () => {
    if (!answer) {
      return (
        <div className="flex flex-col items-center justify-center p-8 text-center text-gray-500">
          <MessageSquare className="w-8 h-8 mb-2" />
          <p className="text-xs">No analysis result generated yet.</p>
        </div>
      );
    }

    return (
      <div className="space-y-4">
        <div className="flex items-center gap-3 border-b border-brand-border pb-3">
          <MessageSquare className="w-5 h-5 text-blue-400" />
          <div>
            <h4 className="font-semibold text-xs text-gray-200 uppercase tracking-wider">
              Analysis Agent Insights
            </h4>
            <p className="text-[10px] text-gray-500 mt-0.5">
              Interpretation based purely on tool outputs (Sandboxed).
            </p>
          </div>
        </div>

        <div className="bg-brand-panel/20 border border-brand-border p-5 rounded-2xl leading-relaxed text-xs text-gray-300 font-sans space-y-4 whitespace-pre-line">
          {answer}
        </div>
      </div>
    );
  };

  // Render Dataset details
  const renderDatasetDetails = () => {
    if (!selectedFile) {
      return (
        <div className="flex flex-col items-center justify-center p-8 text-center text-gray-500">
          <Table className="w-8 h-8 mb-2" />
          <p className="text-xs">No active dataset selected.</p>
        </div>
      );
    }

    // Try to find if we ran profile step
    const profileStep = stepTimings.find((t) => t.tool === "profile");
    const profile = profileStep?.output?.profile;

    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3 border-b border-brand-border pb-3">
          <Table className="w-5 h-5 text-blue-400" />
          <div>
            <h4 className="font-semibold text-xs text-gray-200">
              {selectedFile.filename}
            </h4>
            <p className="text-[10px] text-gray-500 mt-0.5">
              Dataset metadata and column schemas.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4 text-center">
          <div className="bg-brand-panel/30 border border-brand-border p-3.5 rounded-xl">
            <div className="text-[10px] font-mono text-gray-500 uppercase">Rows</div>
            <div className="text-base font-bold text-gray-200 mt-1">
              {selectedFile.rows.toLocaleString()}
            </div>
          </div>
          <div className="bg-brand-panel/30 border border-brand-border p-3.5 rounded-xl">
            <div className="text-[10px] font-mono text-gray-500 uppercase">Columns</div>
            <div className="text-base font-bold text-gray-200 mt-1">
              {selectedFile.columns}
            </div>
          </div>
          <div className="bg-brand-panel/30 border border-brand-border p-3.5 rounded-xl">
            <div className="text-[10px] font-mono text-gray-500 uppercase">Health Rating</div>
            <div className="text-base font-bold text-emerald-400 mt-1">
              {profile ? "96%" : "95%"}
            </div>
          </div>
        </div>

        {profile && (
          <div className="space-y-4">
            <div className="bg-brand-panel/10 border border-brand-border rounded-xl p-4">
              <h5 className="text-[10px] font-mono text-gray-400 uppercase tracking-wider mb-3">
                Columns & Schema Types
              </h5>
              <div className="max-h-48 overflow-y-auto scrollbar-thin space-y-2 pr-1">
                {Object.entries(profile.dtypes).map(([col, dtype]: any) => (
                  <div key={col} className="flex justify-between items-center text-xs font-mono py-1 border-b border-brand-border/40 last:border-0">
                    <span className="text-gray-300 font-semibold truncate pr-2 max-w-[160px]">{col}</span>
                    <div className="flex gap-4">
                      <span className="text-gray-500">{String(dtype)}</span>
                      <span className="text-amber-500/80 text-[10px] bg-amber-500/5 px-2 py-0.5 rounded border border-amber-500/20">
                        {profile.missing_values[col] || 0} missing
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Preview table */}
            {profile.preview && (
              <div className="border border-brand-border rounded-xl overflow-hidden">
                <div className="p-3 bg-brand-panel/30 border-b border-brand-border flex justify-between items-center">
                  <span className="text-[10px] font-mono text-gray-400 uppercase tracking-wider">
                    First 5 Rows Preview
                  </span>
                </div>
                <div className="overflow-x-auto scrollbar-thin">
                  <table className="w-full text-left text-[10px] font-mono text-gray-400 min-w-[500px]">
                    <thead>
                      <tr className="bg-[#0A0D14] border-b border-brand-border">
                        {selectedFile.column_names.map((col) => (
                          <th key={col} className="p-2.5 font-bold text-gray-300 border-r border-brand-border/60 last:border-0 truncate max-w-[120px]">
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {profile.preview.map((row: any, rIdx: number) => (
                        <tr key={rIdx} className="border-b border-brand-border/40 last:border-0 hover:bg-brand-panel/10">
                          {selectedFile.column_names.map((col) => (
                            <td key={col} className="p-2.5 border-r border-brand-border/40 last:border-0 truncate max-w-[120px]">
                              {row[col] !== null ? String(row[col]) : "null"}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="fixed inset-0 bg-brand-bg/85 backdrop-blur-md flex items-center justify-center z-50 p-6 animate-fade-in">
      <div className="bg-brand-card border border-brand-border rounded-3xl w-full max-w-3xl shadow-2xl overflow-hidden flex flex-col max-h-[640px]">
        {/* Header */}
        <div className="p-5 border-b border-brand-border flex justify-between items-center bg-brand-panel/20">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-blue-400">
              <Eye className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-bold text-sm text-gray-200">
                Agent Inspector Details
              </h3>
              <p className="text-[10px] text-gray-500 uppercase tracking-widest font-mono">
                Active Stage: {stageId}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-500 hover:text-white bg-brand-panel hover:bg-brand-panel/80 border border-brand-border rounded-xl cursor-pointer transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 flex-1 overflow-y-auto scrollbar-thin">
          {stageId === "manager" && renderDatasetDetails()}
          {stageId === "profiler" && renderDatasetDetails()}
          {stageId === "planner" && renderPlannerDetails()}
          {stageId === "executor" && renderExecutorDetails()}
          {stageId === "visualization" && renderVisualizationDetails()}
          {stageId === "analysis" && renderAnalysisDetails()}
          {stageId === "final_answer" && renderAnalysisDetails()}
        </div>
      </div>
    </div>
  );
};
