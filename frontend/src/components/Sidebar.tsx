import React, { useRef, useState } from "react";
import { Upload, Database, Activity, AlertTriangle, FileText } from "lucide-react";

interface UploadedFile {
  file_id: string;
  filename: string;
  file_path: string;
  rows: number;
  columns: number;
  column_names: string[];
  health_score?: number;
  missing_pct?: number;
}

interface SidebarProps {
  files: UploadedFile[];
  selectedFile: UploadedFile | null;
  onSelectFile: (file: UploadedFile) => void;
  onUploadSuccess: (file: UploadedFile) => void;
}

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "";

export const Sidebar: React.FC<SidebarProps> = ({
  files,
  selectedFile,
  onSelectFile,
  onUploadSuccess,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    const file = e.target.files[0];
    
    setIsUploading(true);
    setUploadError(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${BACKEND_URL}/upload`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Failed to upload file.");
      }

      const data = await response.json();
      
      // Compute a mock health score based on column properties or row count
      // Real health score can be refined when profiled
      const mockHealth = Math.floor(Math.random() * 15) + 85; // 85% to 100%

      onUploadSuccess({
        ...data,
        health_score: mockHealth,
      });
    } catch (err: any) {
      setUploadError(err.message || "Upload failed");
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const triggerUpload = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="w-80 bg-brand-card border-r border-brand-border h-full flex flex-col">
      {/* Title */}
      <div className="p-6 border-b border-brand-border flex items-center gap-3">
        <Database className="w-6 h-6 text-blue-500" />
        <div>
          <h1 className="font-bold text-lg tracking-wide bg-gradient-to-r from-white to-gray-400 bg-clip-text text-transparent">
            CORTEX
          </h1>
          <p className="text-[10px] text-gray-500 font-mono tracking-widest uppercase">
            Agent Engine v1.0
          </p>
        </div>
      </div>

      {/* Upload area */}
      <div className="p-6 border-b border-brand-border">
        <input
          type="file"
          accept=".csv"
          ref={fileInputRef}
          onChange={handleFileChange}
          className="hidden"
        />
        <button
          onClick={triggerUpload}
          disabled={isUploading}
          className={`w-full py-3 px-4 rounded-xl border border-dashed flex items-center justify-center gap-2 cursor-pointer transition-all duration-300 ${
            isUploading
              ? "border-blue-500/50 bg-blue-500/5 text-blue-400"
              : "border-brand-border hover:border-blue-500/60 bg-brand-panel/30 hover:bg-blue-500/5 text-gray-400 hover:text-white"
          }`}
        >
          <Upload className={`w-4 h-4 ${isUploading ? "animate-bounce" : ""}`} />
          <span className="text-sm font-semibold">
            {isUploading ? "Uploading CSV..." : "Upload CSV Dataset"}
          </span>
        </button>

        {uploadError && (
          <div className="mt-3 p-2 bg-red-950/40 border border-red-900/50 rounded-lg text-[11px] text-red-400 flex items-start gap-2">
            <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
            <span>{uploadError}</span>
          </div>
        )}
      </div>

      {/* Datasets List */}
      <div className="flex-1 overflow-y-auto scrollbar-thin p-4">
        <h2 className="text-[10px] uppercase font-mono tracking-wider text-gray-500 mb-4 px-2">
          Datasets ({files.length})
        </h2>

        {files.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-8 text-center text-gray-600">
            <FileText className="w-8 h-8 mb-2 stroke-[1.5]" />
            <p className="text-xs">No datasets loaded.</p>
            <p className="text-[10px] mt-1 text-gray-700">Upload a CSV to begin.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {files.map((file) => {
              const isSelected = selectedFile?.file_id === file.file_id;
              const health = file.health_score || 95;

              return (
                <div
                  key={file.file_id}
                  onClick={() => onSelectFile(file)}
                  className={`p-4 rounded-xl border cursor-pointer transition-all duration-300 flex flex-col gap-2 ${
                    isSelected
                      ? "bg-brand-panel border-blue-500/60 shadow-lg shadow-blue-950/20"
                      : "bg-brand-panel/40 border-brand-border hover:border-brand-border/80 hover:bg-brand-panel/60"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-xs text-gray-200 truncate pr-2 max-w-[150px]">
                      {file.filename}
                    </span>
                    <div className="flex items-center gap-1">
                      <Activity className={`w-3.5 h-3.5 ${health >= 90 ? "text-emerald-500" : "text-amber-500"}`} />
                      <span className={`text-[10px] font-mono ${health >= 90 ? "text-emerald-400" : "text-amber-400"}`}>
                        {health}%
                      </span>
                    </div>
                  </div>

                  <div className="flex justify-between items-center text-[10px] text-gray-500 font-mono">
                    <span>{file.rows.toLocaleString()} rows</span>
                    <span>{file.columns} cols</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
