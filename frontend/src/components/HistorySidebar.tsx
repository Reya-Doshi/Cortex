import React, { useEffect, useState } from "react";
import { History, X, Clock, Award, FileSpreadsheet, Calendar, CornerDownLeft } from "lucide-react";

interface HistoryItem {
  id: string;
  timestamp: string;
  question: string;
  datasets: string[];
  steps_count: number;
  total_duration_ms: number;
  confidence: number;
}

interface HistorySidebarProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectRun: (runId: string) => void;
}

export const HistorySidebar: React.FC<HistorySidebarProps> = ({
  isOpen,
  onClose,
  onSelectRun,
}) => {
  const [historyList, setHistoryList] = useState<HistoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen) {
      fetchHistory();
    }
  }, [isOpen]);

  const fetchHistory = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch("/history");
      if (!response.ok) throw new Error("Failed to load history list.");
      const data = await response.json();
      setHistoryList(data.history || []);
    } catch (err: any) {
      setError(err.message || "Failed to load history");
    } finally {
      setIsLoading(false);
    }
  };

  const formatDate = (isoString: string) => {
    try {
      const date = new Date(isoString);
      return date.toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return isoString;
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-y-0 right-0 w-80 bg-brand-card border-l border-brand-border h-full flex flex-col z-40 animate-slide-in shadow-2xl">
      {/* Header */}
      <div className="p-6 border-b border-brand-border flex items-center justify-between bg-brand-panel/20">
        <div className="flex items-center gap-2">
          <History className="w-5 h-5 text-blue-500" />
          <h3 className="font-bold text-sm text-gray-200">Investigation Logs</h3>
        </div>
        <button
          onClick={onClose}
          className="p-1 text-gray-500 hover:text-white hover:bg-brand-panel border border-brand-border/60 rounded-lg cursor-pointer"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto scrollbar-thin p-4 space-y-4">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center p-12 text-center text-gray-600">
            <span className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mb-2" />
            <p className="text-xs">Loading logs...</p>
          </div>
        ) : error ? (
          <div className="p-4 bg-red-950/20 border border-red-900/40 rounded-xl text-center text-xs text-red-400">
            {error}
          </div>
        ) : historyList.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-8 text-center text-gray-600 italic text-xs">
            No past investigations recorded.
          </div>
        ) : (
          historyList.map((run) => (
            <div
              key={run.id}
              onClick={() => onSelectRun(run.id)}
              className="p-4 bg-brand-panel/40 border border-brand-border hover:border-blue-500/40 rounded-xl cursor-pointer hover:bg-brand-panel/80 transition-all duration-300 group flex flex-col gap-2 relative"
            >
              {/* Question */}
              <p className="text-xs font-semibold text-gray-200 line-clamp-2 pr-6 group-hover:text-blue-400 transition-colors">
                "{run.question}"
              </p>

              {/* Hover arrow */}
              <CornerDownLeft className="w-3.5 h-3.5 text-blue-500 absolute right-4 bottom-4 opacity-0 group-hover:opacity-100 transition-opacity" />

              {/* Timestamp & Files */}
              <div className="flex items-center gap-1.5 text-[9px] text-gray-500 font-mono">
                <Calendar className="w-3 h-3 shrink-0" />
                <span>{formatDate(run.timestamp)}</span>
              </div>

              {/* Metrics row */}
              <div className="flex justify-between items-center text-[9px] text-gray-600 font-mono mt-1 pt-1.5 border-t border-brand-border/40">
                <span className="flex items-center gap-1">
                  <Clock className="w-2.5 h-2.5" />
                  {run.total_duration_ms.toFixed(0)}ms
                </span>
                <span className="flex items-center gap-1">
                  <Award className="w-2.5 h-2.5 text-blue-500/80" />
                  {(run.confidence * 100).toFixed(0)}%
                </span>
                <span className="flex items-center gap-1 max-w-[80px] truncate">
                  <FileSpreadsheet className="w-2.5 h-2.5" />
                  {run.datasets.map((d) => d.split("/").pop()).join(", ")}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
