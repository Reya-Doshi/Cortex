import React, { useEffect, useRef } from "react";
import { Terminal, Trash2 } from "lucide-react";

export interface LogEntry {
  text: string;
  type: "Planning" | "Execution" | "Visualization" | "Analysis" | "System" | "Error";
}

interface TerminalLogsProps {
  logs: LogEntry[];
  onClear: () => void;
}

export const TerminalLogs: React.FC<TerminalLogsProps> = ({ logs, onClear }) => {
  const terminalEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Autoscroll to bottom when logs stream in
    terminalEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const getBadgeColor = (type: string) => {
    switch (type) {
      case "Planning":
        return "text-amber-400 bg-amber-400/10 border-amber-500/20";
      case "Execution":
        return "text-sky-400 bg-sky-400/10 border-sky-500/20";
      case "Visualization":
        return "text-purple-400 bg-purple-400/10 border-purple-500/20";
      case "Analysis":
        return "text-emerald-400 bg-emerald-400/10 border-emerald-500/20";
      case "Error":
        return "text-red-400 bg-red-400/10 border-red-500/20 animate-pulse";
      default:
        return "text-gray-400 bg-gray-400/10 border-gray-500/10";
    }
  };

  return (
    <div className="h-56 bg-[#05070B] border-t border-brand-border flex flex-col font-mono text-xs">
      {/* Console Header */}
      <div className="px-6 py-2.5 bg-[#090D14] border-b border-brand-border/60 flex items-center justify-between">
        <div className="flex items-center gap-2 text-gray-400">
          <Terminal className="w-4 h-4 text-blue-500" />
          <span className="font-semibold text-[10px] uppercase tracking-wider">
            Agent Console Logs
          </span>
        </div>
        <button
          onClick={onClear}
          disabled={logs.length === 0}
          className="text-gray-600 hover:text-gray-400 transition-colors p-1 cursor-pointer disabled:opacity-30 disabled:pointer-events-none"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Terminal Stream */}
      <div className="flex-1 p-5 overflow-y-auto scrollbar-thin space-y-2.5">
        {logs.length === 0 ? (
          <div className="text-gray-700 italic text-[11px] h-full flex items-center justify-center select-none">
            &gt; Waiting for agent execution...
          </div>
        ) : (
          <>
            {logs.map((log, idx) => (
              <div key={idx} className="flex items-start gap-3.5 leading-relaxed tracking-wide">
                <span className="text-gray-700 select-none">&gt;</span>
                <span
                  className={`px-2 py-0.5 rounded border text-[9px] font-bold select-none shrink-0 tracking-wider uppercase ${getBadgeColor(
                    log.type
                  )}`}
                >
                  {log.type}
                </span>
                <span className="text-gray-300 break-all">{log.text}</span>
              </div>
            ))}
            <div ref={terminalEndRef} />
          </>
        )}
      </div>
    </div>
  );
};
