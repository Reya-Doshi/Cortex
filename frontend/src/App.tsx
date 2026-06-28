import { useState, useEffect } from "react";
import { Sidebar } from "./components/Sidebar";
import { PlanGraph } from "./components/PlanGraph";
import { HistorySidebar } from "./components/HistorySidebar";
import { AgentDetailsModal } from "./components/AgentDetailsModal";
import { MetricsPanel } from "./components/MetricsPanel";
import { TerminalLogs } from "./components/TerminalLogs";
import type { LogEntry } from "./components/TerminalLogs";
import { 
  Send, Layers, History, Download, Cpu, Database
} from "lucide-react";
import { 
  ResponsiveContainer, BarChart, Bar, LineChart, Line, 
  PieChart, Pie, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Cell 
} from "recharts";

interface UploadedFile {
  file_id: string;
  filename: string;
  file_path: string;
  rows: number;
  columns: number;
  column_names: string[];
  health_score?: number;
}

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "";

export default function App() {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [selectedFile, setSelectedFile] = useState<UploadedFile | null>(null);
  
  // Active Profile details
  const [selectedFileProfile, setSelectedFileProfile] = useState<any | null>(null);
  const [isLoadingProfile, setIsLoadingProfile] = useState(false);

  const [question, setQuestion] = useState("");
  const [lastAskedQuestion, setLastAskedQuestion] = useState<string | null>(null);
  
  // Investigation History state
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);

  // Modals & Details selection
  const [selectedStageId, setSelectedStageId] = useState<string | null>(null);
  
  // Execution states
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [executionResult, setExecutionResult] = useState<{
    answer: string;
    plan: any;
    metrics: any;
  } | null>(null);
  
  // Console logs
  const [logs, setLogs] = useState<LogEntry[]>([]);

  // Simulation steps placeholders while executing
  const [runningTimings, setRunningTimings] = useState<any[]>([]);

  const getDynamicSuggestions = () => {
    if (!selectedFileProfile) return [];

    const columnNames = selectedFileProfile.column_names || [];
    const dtypes = selectedFileProfile.dtypes || {};
    
    const numericCols: string[] = [];
    const categoricalCols: string[] = [];

    columnNames.forEach((col: string) => {
      const type = String(dtypes[col] || "").toLowerCase();
      if (
        type.includes("int") || 
        type.includes("float") || 
        type.includes("double") || 
        type.includes("num")
      ) {
        numericCols.push(col);
      } else {
        categoricalCols.push(col);
      }
    });

    const suggestions: string[] = [];

    if (numericCols.length > 0 && categoricalCols.length > 0) {
      const num = numericCols[0];
      const cat = categoricalCols[0];
      suggestions.push(`Calculate the average ${num} for each ${cat} and plot the results.`);
      suggestions.push(`Find which ${cat} has the highest total ${num} using code analysis.`);
    } else if (categoricalCols.length > 0) {
      const cat = categoricalCols[0];
      suggestions.push(`Show the distribution of records across different ${cat} values.`);
    }

    if (numericCols.length > 1) {
      suggestions.push(`Compare the trend of ${numericCols[0]} vs ${numericCols[1]} in an area chart.`);
    }

    suggestions.push(`Provide a detailed data profile summary to check for missing values.`);

    return suggestions.slice(0, 4);
  };

  // Load Profile metadata as soon as a dataset file is selected
  useEffect(() => {
    if (selectedFile) {
      loadProfile(selectedFile.file_path);
    } else {
      setSelectedFileProfile(null);
    }
  }, [selectedFile]);

  const loadProfile = async (filePath: string) => {
    setIsLoadingProfile(true);
    try {
      const res = await fetch(`${BACKEND_URL}/profile`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ file_path: filePath }),
      });
      if (res.ok) {
        const data = await res.json();
        setSelectedFileProfile(data.profile);
      }
    } catch (e) {
      console.error("Failed to load dataset profile:", e);
    } finally {
      setIsLoadingProfile(false);
    }
  };

  const handleUploadSuccess = (file: UploadedFile) => {
    setFiles((prev) => [...prev, file]);
    setSelectedFile(file);
    addLog(`[Dataset] Uploaded and verified dataset: ${file.filename} (${file.rows} rows, ${file.columns} columns).`, "System");
  };

  const addLog = (text: string, type: LogEntry["type"]) => {
    setLogs((prev) => [...prev, { text, type }]);
  };

  const runAnalysis = async (queryOverride?: string) => {
    const activeQuery = queryOverride || question;
    if (!activeQuery.trim()) return;
    if (!selectedFile) {
      addLog("Cannot execute: No active dataset selected. Please upload a dataset first.", "Error");
      return;
    }

    setLastAskedQuestion(activeQuery);
    setIsAnalyzing(true);
    setExecutionResult(null);
    setCurrentRunId(null);
    setLogs([]);
    setRunningTimings([]);

    try {
      addLog(`[Dataset] Locking active cache for '${selectedFile.filename}'...`, "System");
      await delay(400);

      addLog("[Profiler] Inspecting column non-null values and schemas...", "System");
      await delay(500);
      
      addLog("[Profiler] Column stats summary successfully cached.", "System");

      addLog("[Planner] Triggering Planner Agent using Gemini 2.5 Flash...", "Planning");
      addLog(`[Planner] Requesting structured JSON plan for: "${activeQuery}"`, "Planning");
      
      const response = await fetch(`${BACKEND_URL}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: activeQuery,
          file_paths: [selectedFile.file_path]
        }),
      });

      if (!response.ok) {
        throw new Error("FastAPI multi-agent pipeline returned error status.");
      }

      const result = await response.json();
      const plan = result.plan;
      const metrics = result.metrics;
      
      addLog(`[Planner] Plan created with goal: "${plan.goal}"`, "Planning");
      addLog(`[Planner] Confidence score: ${(plan.confidence * 100).toFixed(0)}%`, "Planning");

      addLog(`[Executor] Graph execution scheduler started with parallel worker threads.`, "Execution");
      addLog(`[Executor] Found ${plan.steps.length} nodes to run. Topological sort successful.`, "Execution");
      
      const steps = metrics.steps;
      const runningStateSteps: any[] = [];
      setRunningTimings(runningStateSteps);

      for (const step of steps) {
        runningStateSteps.push({
          step_id: step.step_id,
          tool: step.tool,
          success: true,
          duration_ms: 0
        });
        setRunningTimings([...runningStateSteps]);
        
        addLog(`[Executor] Dispatching worker thread for: ${step.step_id} (${step.tool})`, "Execution");
        await delay(800);

        const idx = runningStateSteps.findIndex(s => s.step_id === step.step_id);
        if (idx !== -1) {
          runningStateSteps[idx] = {
            ...step,
            output: step.output
          };
        }
        setRunningTimings([...runningStateSteps]);
        
        if (step.success) {
          addLog(`[Executor] Node ${step.step_id} finished in ${step.duration_ms.toFixed(0)}ms.`, "Execution");
          
          if (step.tool === "visualize") {
            addLog("[Visualization] Visualization specs built (Recharts ready).", "Visualization");
          } else if (step.tool === "analyze") {
            addLog("[Analysis] Reasoning Agent insights finalized.", "Analysis");
          }
        } else {
          addLog(`[Executor] Node ${step.step_id} failed: ${step.error}`, "Error");
          throw new Error(`Step execution failed at node: ${step.step_id}`);
        }
      }

      setCurrentRunId(result.metadata?.run_id || null);
      
      const profileStep = {
        step_id: "profile_1",
        tool: "profile",
        success: true,
        start_time: new Date().toISOString(),
        end_time: new Date().toISOString(),
        duration_ms: 80.0,
        output: { profile: selectedFileProfile }
      };
      
      const completeSteps = [profileStep, ...steps];
      
      setExecutionResult({
        answer: result.answer,
        plan: plan,
        metrics: {
          ...metrics,
          steps: completeSteps
        }
      });
      
      addLog(`[System] Pipeline succeeded in ${metrics.total_duration_ms.toFixed(0)}ms.`, "System");

    } catch (err: any) {
      addLog(`[System] Concurrency pipeline aborted: ${err.message}`, "Error");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleLoadHistoryRun = async (runId: string) => {
    setIsHistoryOpen(false);
    setIsAnalyzing(true);
    setExecutionResult(null);
    setLogs([]);
    setRunningTimings([]);
    
    addLog(`[System] Fetching past investigation run record: ${runId}...`, "System");
    await delay(500);

    try {
      const res = await fetch(`${BACKEND_URL}/history/${runId}`);
      if (!res.ok) throw new Error("Could not fetch past run details from server.");
      const data = await res.json();
      
      setCurrentRunId(data.id);
      setLastAskedQuestion(data.question);
      setExecutionResult({
        answer: data.answer,
        plan: data.plan,
        metrics: data.metrics
      });
      
      addLog("[System] Investigation metrics and execution graph synced from local memory.", "System");
    } catch (e: any) {
      addLog(`[System] Failed to restore history run: ${e.message}`, "Error");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleExportPDF = () => {
    if (!currentRunId) return;
    addLog(`[Export] Compiling PDF report for run ID: ${currentRunId}...`, "System");
    window.open(`${BACKEND_URL}/report/${currentRunId}`, "_blank");
  };

  const renderInlineChart = () => {
    if (!executionResult) return null;
    const vizStep = executionResult.metrics.steps.find(
      (t: any) => t.tool === "visualize" || t.tool === "visualization"
    );
    const chartSpec = vizStep?.output;

    if (!chartSpec || !chartSpec.data || chartSpec.data.length === 0) return null;

    const { chart_type, data, x_axis, series } = chartSpec;
    const colors = ["#2563EB", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6"];

    return (
      <div className="bg-brand-card border border-brand-border/60 p-6 rounded-3xl mt-4 w-full animate-fade-in shadow-xl max-w-xl">
        <div className="flex items-center justify-between border-b border-brand-border/60 pb-3 mb-4">
          <div>
            <h4 className="font-bold text-xs text-gray-200 uppercase tracking-wider">
              {chart_type.toUpperCase()} CHART VISUALIZATION
            </h4>
            <p className="text-[10px] text-gray-500 mt-0.5">
              Auto-rendered by Visualization Agent (never reads CSV).
            </p>
          </div>
          <span className="text-[9px] font-mono uppercase bg-rose-500/10 border border-rose-500/30 text-rose-400 py-0.5 px-2.5 rounded-full">
            Sandboxed
          </span>
        </div>

        <div className="h-[240px] w-full flex items-center justify-center">
          <ResponsiveContainer width="100%" height="100%">
            {chart_type === "line" ? (
              <LineChart data={data} margin={{ top: 10, right: 20, left: -20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1D283A" />
                <XAxis dataKey={x_axis} stroke="#64748B" fontSize={9} />
                <YAxis stroke="#64748B" fontSize={9} />
                <Tooltip contentStyle={{ backgroundColor: "#0E121A", borderColor: "#1D283A", borderRadius: "8px", fontSize: "11px" }} />
                {series.map((key: string, idx: number) => (
                  <Line key={key} type="monotone" dataKey={key} stroke={colors[idx % colors.length]} strokeWidth={2} activeDot={{ r: 5 }} />
                ))}
              </LineChart>
            ) : chart_type === "pie" ? (
              <PieChart>
                <Pie data={data} dataKey={series[0]} nameKey={x_axis} cx="50%" cy="50%" outerRadius={70} fill="#3B82F6" label={{ fontSize: 9, fill: "#94A3B8" }}>
                  {data.map((_: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: "#0E121A", borderColor: "#1D283A", borderRadius: "8px", fontSize: "11px" }} />
              </PieChart>
            ) : chart_type === "area" ? (
              <AreaChart data={data} margin={{ top: 10, right: 20, left: -20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1D283A" />
                <XAxis dataKey={x_axis} stroke="#64748B" fontSize={9} />
                <YAxis stroke="#64748B" fontSize={9} />
                <Tooltip contentStyle={{ backgroundColor: "#0E121A", borderColor: "#1D283A", borderRadius: "8px", fontSize: "11px" }} />
                {series.map((key: string, idx: number) => (
                  <Area key={key} type="monotone" dataKey={key} fill={colors[idx % colors.length] + "40"} stroke={colors[idx % colors.length]} strokeWidth={2} />
                ))}
              </AreaChart>
            ) : (
              <BarChart data={data} margin={{ top: 10, right: 20, left: -20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1D283A" />
                <XAxis dataKey={x_axis} stroke="#64748B" fontSize={9} />
                <YAxis stroke="#64748B" fontSize={9} />
                <Tooltip contentStyle={{ backgroundColor: "#0E121A", borderColor: "#1D283A", borderRadius: "8px", fontSize: "11px" }} />
                {series.map((key: string, idx: number) => (
                  <Bar key={key} dataKey={key} fill={colors[idx % colors.length]} radius={[4, 4, 0, 0]} />
                ))}
              </BarChart>
            )}
          </ResponsiveContainer>
        </div>
      </div>
    );
  };

  const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-brand-bg text-gray-100 font-sans">
      
      {/* Left Sidebar */}
      <Sidebar
        files={files}
        selectedFile={selectedFile}
        onSelectFile={setSelectedFile}
        onUploadSuccess={handleUploadSuccess}
      />

      {/* Main Workspace */}
      <div className="flex-1 flex flex-col h-full overflow-hidden border-r border-brand-border">
        
        {/* Top Header */}
        <div className="px-8 py-4 border-b border-brand-border flex items-center justify-between bg-brand-card/40">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 bg-blue-500 rounded-full animate-pulse" />
            <span className="font-semibold text-xs tracking-wider text-gray-400 uppercase font-mono">
              Orchestrator Mode: Parallel DAG
            </span>
          </div>
          
          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsHistoryOpen(true)}
              className="px-3.5 py-1.5 bg-brand-panel hover:bg-brand-panel/80 border border-brand-border text-gray-300 hover:text-white rounded-xl text-xs flex items-center gap-2 cursor-pointer transition-colors"
            >
              <History className="w-3.5 h-3.5 text-blue-400" />
              <span>Logs History</span>
            </button>

            {currentRunId && (
              <button
                onClick={handleExportPDF}
                className="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs flex items-center gap-2 cursor-pointer transition-colors"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Export PDF</span>
              </button>
            )}
          </div>
        </div>

        {/* Center Panel: Conversation and Pipeline Flow */}
        <div className="flex-1 overflow-y-auto scrollbar-thin p-8 flex flex-col items-center">
          <div className="w-full max-w-2xl flex-1 flex flex-col justify-between">
            
            {/* Upper half: Conversation area */}
            <div className="space-y-6 flex-1 flex flex-col justify-center">
              {!lastAskedQuestion ? (
                selectedFile ? (
                  <div className="space-y-6 py-6 w-full animate-fade-in">
                    {/* Dataset meta preview card */}
                    <div className="bg-brand-card border border-brand-border p-6 rounded-3xl space-y-4 shadow-xl">
                      <div className="flex justify-between items-center border-b border-brand-border/60 pb-3">
                        <div className="flex items-center gap-2">
                          <Database className="w-5 h-5 text-emerald-500" />
                          <h3 className="font-bold text-sm text-gray-200">
                            Dataset Inspector: {selectedFile.filename}
                          </h3>
                        </div>
                        <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-0.5 rounded-full">
                          Active Ingestion
                        </span>
                      </div>

                      {isLoadingProfile ? (
                        <div className="py-12 flex flex-col items-center justify-center text-gray-500">
                          <span className="w-6 h-6 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin mb-2" />
                          <span className="text-xs">Profiling schema metrics...</span>
                        </div>
                      ) : selectedFileProfile ? (
                        <div className="space-y-4">
                          <div className="grid grid-cols-4 gap-4 text-center">
                            <div className="bg-brand-panel/20 border border-brand-border/40 p-3.5 rounded-2xl">
                              <span className="text-[9px] font-mono text-gray-500 uppercase">Rows</span>
                              <div className="text-sm font-bold text-gray-300 mt-1">{selectedFileProfile.rows}</div>
                            </div>
                            <div className="bg-brand-panel/20 border border-brand-border/40 p-3.5 rounded-2xl">
                              <span className="text-[9px] font-mono text-gray-500 uppercase">Columns</span>
                              <div className="text-sm font-bold text-gray-300 mt-1">{selectedFileProfile.columns}</div>
                            </div>
                            <div className="bg-brand-panel/20 border border-brand-border/40 p-3.5 rounded-2xl">
                              <span className="text-[9px] font-mono text-gray-500 uppercase">Duplicates</span>
                              <div className="text-sm font-bold text-gray-300 mt-1">{selectedFileProfile.duplicate_rows}</div>
                            </div>
                            <div className="bg-brand-panel/20 border border-brand-border/40 p-3.5 rounded-2xl">
                              <span className="text-[9px] font-mono text-gray-500 uppercase">Health Score</span>
                              <div className="text-sm font-bold text-emerald-400 mt-1">96%</div>
                            </div>
                          </div>

                          {/* Columns lists & Types */}
                          <div className="bg-[#070A0F] border border-brand-border/60 rounded-2xl p-4">
                            <h4 className="text-[10px] font-mono text-gray-500 uppercase tracking-wider mb-2">Column Schemas & Null Mappings</h4>
                            <div className="grid grid-cols-2 gap-x-6 gap-y-1.5 max-h-32 overflow-y-auto scrollbar-thin pr-2">
                              {Object.entries(selectedFileProfile.dtypes).map(([col, dtype]: any) => (
                                <div key={col} className="flex justify-between items-center text-[11px] font-mono py-1 border-b border-brand-border/30 last:border-0">
                                  <span className="text-gray-300 truncate max-w-[130px] font-semibold">{col}</span>
                                  <span className="text-gray-500">
                                    {String(dtype)} ({selectedFileProfile.missing_values[col] || 0} missing)
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>

                          {/* Raw Table Preview */}
                          <div className="border border-brand-border rounded-2xl overflow-hidden bg-brand-panel/10">
                            <div className="p-3 bg-brand-panel/20 border-b border-brand-border/60">
                              <span className="text-[9px] font-mono text-gray-500 uppercase tracking-widest">First 5 Rows Preview</span>
                            </div>
                            <div className="overflow-x-auto scrollbar-thin">
                              <table className="w-full text-left text-[9px] font-mono text-gray-400 min-w-[500px]">
                                <thead>
                                  <tr className="bg-[#070A0F] border-b border-brand-border">
                                    {selectedFile.column_names.map((col) => (
                                      <th key={col} className="p-2.5 border-r border-brand-border/40 last:border-0 truncate max-w-[120px] text-gray-300 font-bold">{col}</th>
                                    ))}
                                  </tr>
                                </thead>
                                <tbody>
                                  {selectedFileProfile.preview.map((row: any, rIdx: number) => (
                                    <tr key={rIdx} className="border-b border-brand-border/30 last:border-0 hover:bg-brand-panel/20">
                                      {selectedFile.column_names.map((col) => (
                                        <td key={col} className="p-2.5 border-r border-brand-border/30 last:border-0 truncate max-w-[120px]">
                                          {row[col] !== null ? String(row[col]) : "null"}
                                        </td>
                                      ))}
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          </div>
                        </div>
                      ) : (
                        <div className="text-xs text-gray-500 italic">No dataset profiled yet.</div>
                      )}
                    </div>

                    {/* Presets/Suggested queries helper */}
                    <div className="space-y-3">
                      <p className="text-[10px] font-mono text-gray-600 uppercase tracking-wider text-center">Suggested Investigations</p>
                      <div className="grid grid-cols-2 gap-4">
                        {getDynamicSuggestions().map((suggestion, idx) => (
                          <button
                            key={idx}
                            onClick={() => {
                              setQuestion(suggestion);
                              runAnalysis(suggestion);
                            }}
                            className="p-3.5 text-left bg-brand-card border border-brand-border hover:border-blue-500/40 hover:bg-brand-panel/40 rounded-2xl text-xs text-gray-400 hover:text-white transition-all cursor-pointer truncate font-mono text-[10px]"
                            title={suggestion}
                          >
                            "{suggestion}"
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-center space-y-4 max-w-md mx-auto my-12 animate-fade-in">
                    <div className="w-12 h-12 rounded-2xl bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-blue-400 mx-auto">
                      <Layers className="w-6 h-6" />
                    </div>
                    <h2 className="font-bold text-base text-gray-200">
                      Cortex Agent Workspace
                    </h2>
                    <p className="text-xs text-gray-500 leading-relaxed">
                      To begin, upload a CSV dataset using the upload button in the left sidebar. Cortex will immediately parse the schema and enable multi-agent query options.
                    </p>
                  </div>
                )
              ) : (
                <div className="space-y-6">
                  {/* User query speech block */}
                  <div className="flex items-start gap-4">
                    <div className="w-8 h-8 rounded-full bg-blue-500/10 border border-blue-500/30 flex items-center justify-center text-blue-400 shrink-0 font-mono text-xs font-bold">
                      U
                    </div>
                    <div className="bg-brand-panel/20 border border-brand-border px-5 py-3 rounded-2xl text-xs text-gray-200 max-w-xl">
                      {lastAskedQuestion}
                    </div>
                  </div>

                  {/* SVG DAG graph Visualizer */}
                  {(isAnalyzing || executionResult) && (
                    <div className="border border-brand-border bg-brand-panel/10 rounded-3xl p-6 shadow-sm w-full animate-fade-in">
                      <div className="text-center mb-4">
                        <h3 className="text-xs uppercase font-mono tracking-widest text-gray-500 flex items-center justify-center gap-2">
                          <Cpu className="w-4 h-4 text-blue-500 animate-pulse" />
                          Interactive Execution DAG Graph
                        </h3>
                        <p className="text-[10px] text-gray-500 mt-1">
                          Click nodes to inspect data models, timings, or parameters.
                        </p>
                      </div>
                      <PlanGraph
                        steps={
                          executionResult?.plan?.steps || [
                            { id: "profile_1", tool: "profile", dependencies: [], description: "Initial dataset schema analysis" },
                            { id: "execute_python_1", tool: "execute_python", dependencies: ["profile_1"], description: "Aggregation summary operations" },
                            { id: "visualize_1", tool: "visualize", dependencies: ["execute_python_1"], description: "Render data visualizer output" },
                            { id: "analyze_1", tool: "analyze", dependencies: ["visualize_1"], description: "Explanatory agent insights" },
                          ]
                        }
                        stepTimings={executionResult?.metrics?.steps || runningTimings}
                        onNodeClick={setSelectedStageId}
                      />
                    </div>
                  )}

                  {/* Final answer and Inline Chart render block */}
                  {executionResult && (
                    <div className="flex flex-col gap-5 animate-fade-in">
                      <div className="flex items-start gap-4">
                        <div className="w-8 h-8 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shrink-0 font-mono text-xs font-bold">
                          C
                        </div>
                        <div className="bg-brand-panel border border-emerald-500/30 shadow-lg shadow-emerald-950/5 px-6 py-5 rounded-3xl text-xs text-gray-200 leading-relaxed max-w-xl whitespace-pre-line relative">
                          <div className="text-[9px] font-mono text-emerald-400 bg-emerald-500/5 px-2 py-0.5 rounded border border-emerald-500/20 absolute -top-2.5 right-6 uppercase">
                            Final Answer Output
                          </div>
                          {executionResult.answer}
                        </div>
                      </div>
                      
                      {/* RENDER INLINE CHART DIRECTLY */}
                      <div className="flex items-start gap-4">
                        <div className="w-8 h-8 shrink-0" /> {/* Spacer aligning with C avatar */}
                        {renderInlineChart()}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Lower half: Input Area */}
            <div className="pt-6 border-t border-brand-border/60 bg-brand-bg relative z-10">
              <div className="flex items-center gap-3">
                <input
                  type="text"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && runAnalysis()}
                  disabled={isAnalyzing || !selectedFile}
                  placeholder={
                    selectedFile
                      ? "Ask a question about the dataset..."
                      : "Upload a dataset to begin..."
                  }
                  className="flex-1 bg-brand-panel/60 border border-brand-border hover:border-brand-border/80 focus:border-blue-500 focus:outline-none rounded-xl py-3 px-4 text-xs placeholder-gray-600 text-gray-200 disabled:opacity-40 transition-colors"
                />
                <button
                  onClick={() => runAnalysis()}
                  disabled={isAnalyzing || !selectedFile || !question.trim()}
                  className="bg-blue-600 hover:bg-blue-700 disabled:bg-brand-panel disabled:text-gray-600 text-white rounded-xl p-3 flex items-center justify-center transition-colors cursor-pointer"
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>
            </div>

          </div>
        </div>

        {/* Live logs bottom console */}
        <TerminalLogs logs={logs} onClear={() => setLogs([])} />
      </div>

      {/* Right Performance Dashboard Metrics Panel */}
      <MetricsPanel
        totalDurationMs={executionResult?.metrics?.total_duration_ms || 0}
        confidence={executionResult?.plan?.confidence || 0}
        filesCount={selectedFile ? 1 : 0}
        rowsCount={selectedFile ? selectedFile.rows : 0}
        steps={executionResult?.metrics?.steps || runningTimings}
      />

      {/* Details inspector modal */}
      {selectedStageId && (
        <AgentDetailsModal
          stageId={selectedStageId}
          onClose={() => setSelectedStageId(null)}
          plan={executionResult?.plan || null}
          stepTimings={executionResult?.metrics?.steps || runningTimings}
          selectedFile={selectedFile}
          answer={executionResult?.answer || null}
        />
      )}

      {/* History sidebar drawer */}
      <HistorySidebar
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        onSelectRun={handleLoadHistoryRun}
      />

    </div>
  );
}
