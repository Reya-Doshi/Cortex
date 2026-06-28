"""PDF Report Generator — builds branded investigation reports using fpdf2."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from fpdf import FPDF
from backend.config import OUTPUTS_DIR
from backend.history_manager import history_manager

logger = logging.getLogger(__name__)


class CortexPDF(FPDF):
    """FPDF subclass defining custom branding, headers, and footers."""

    def header(self) -> None:
        """Render Cortex header bar on every page."""
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(37, 99, 235)  # #2563EB Blue
        self.cell(0, 8, "CORTEX DATA INVESTIGATION ENGINE", ln=True)
        
        self.set_font("Helvetica", "", 8)
        self.set_text_color(100, 116, 139)  # Slate Gray
        self.cell(0, 4, f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ln=True)
        
        # Horizontal rule line
        self.set_draw_color(226, 232, 240)  # Light border
        self.set_line_width(0.5)
        self.line(10, self.get_y() + 2, 200, self.get_y() + 2)
        self.ln(6)

    def footer(self) -> None:
        """Render page numbers and copyright details at footer."""
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(148, 163, 184)
        
        # Horizontal rule line
        self.set_draw_color(226, 232, 240)
        self.line(10, self.get_y() - 2, 200, self.get_y() - 2)
        
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}  |  Confidential  |  Cortex Multi-Agent Platform", align="C")


class ReportGenerator:
    """Creates professional PDF reports from past run data."""

    def generate_pdf(self, run_id: str) -> Path | None:
        """Generate a PDF report for a run ID and return the file path."""
        data = history_manager.get_run(run_id)
        if not data:
            logger.error("[Report] Run ID %s not found for PDF export", run_id)
            return None

        pdf = CortexPDF()
        pdf.alias_nb_pages()
        pdf.add_page()
        pdf.set_margins(15, 15, 15)

        # 1. Executive Summary
        pdf.set_font("Helvetica", "B", 16)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 10, "Executive Investigation Summary", ln=True)
        pdf.ln(2)

        # Meta details table
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(71, 85, 105)
        pdf.cell(40, 6, "Investigation ID:", border=0)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 6, data.get("id", "N/A"), ln=True)

        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(40, 6, "Datasets Analyzed:", border=0)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 6, ", ".join(data.get("datasets", [])), ln=True)

        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(40, 6, "Run Timestamp:", border=0)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 6, data.get("timestamp", "N/A"), ln=True)
        pdf.ln(4)

        # 2. User Question
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 6, "Primary Question Asked:", ln=True)
        pdf.ln(1)
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(51, 65, 85)
        pdf.multi_cell(0, 5, f"\"{data.get('question')}\"")
        pdf.ln(4)

        # 3. Execution Graph Details
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 6, "Agent Execution Graph Steps:", ln=True)
        pdf.ln(2)

        # Table header
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(241, 245, 249)
        pdf.cell(45, 6, "Step ID", border=1, fill=True)
        pdf.cell(40, 6, "Agent Tool", border=1, fill=True)
        pdf.cell(65, 6, "Description", border=1, fill=True)
        pdf.cell(30, 6, "Duration (ms)", border=1, fill=True, ln=True)

        # Table body
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(51, 65, 85)
        
        steps = data.get("plan", {}).get("steps", [])
        step_timings = {s.get("step_id"): s for s in data.get("metrics", {}).get("steps", [])}

        for step in steps:
            s_id = step.get("id")
            s_tool = step.get("tool")
            s_desc = step.get("description", "")
            
            timing = step_timings.get(s_id, {})
            duration = f"{timing.get('duration_ms', 0.0):.1f}" if timing else "0.0"

            pdf.cell(45, 6, str(s_id), border=1)
            pdf.cell(40, 6, str(s_tool), border=1)
            pdf.cell(65, 6, str(s_desc)[:38], border=1)  # Truncate to fit column
            pdf.cell(30, 6, duration, border=1, ln=True)
        pdf.ln(6)

        # 4. Execution Metrics
        metrics = data.get("metrics", {})
        total_time = metrics.get("total_duration_ms", 0.0)
        
        # Calculate sequential sum
        sequential_sum = sum(s.get("duration_ms", 0.0) for s in metrics.get("steps", []))
        speedup = sequential_sum / total_time if total_time > 0 else 1.0

        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 6, "Performance & Speedup Metrics:", ln=True)
        pdf.ln(1)

        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(60, 5, "Total Parallel Duration (Wall Time):", border=0)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 5, f"{total_time:.2f} ms", ln=True)

        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(60, 5, "Total Sequential Duration (Sum):", border=0)
        pdf.set_font("Helvetica", "", 9)
        pdf.cell(0, 5, f"{sequential_sum:.2f} ms", ln=True)

        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(60, 5, "Concurrency Speedup Ratio:", border=0)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(37, 99, 235)
        pdf.cell(0, 5, f"{speedup:.2f}x speedup", ln=True)
        pdf.set_text_color(51, 65, 85)
        pdf.ln(6)

        # 5. Final AI Findings
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 6, "Reasoning Agent Explanation:", ln=True)
        pdf.ln(2)
        
        pdf.set_font("Helvetica", "", 9.5)
        pdf.set_text_color(15, 23, 42)
        # Handle unicode conversions safely
        ans_text = data.get("answer", "No answer compiled.").encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 5.5, ans_text)
        pdf.ln(6)

        # 6. Recommendations
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 6, "Strategic Recommendations:", ln=True)
        pdf.ln(2)
        pdf.set_font("Helvetica", "", 9.5)
        pdf.multi_cell(0, 5, (
            "1. Inspect the visual Recharts bar/line displays in the Cortex Dashboard UI to confirm trends.\n"
            "2. Utilize the interactive details modal inside the Tool Executor stage to verify raw JSON intermediates.\n"
            "3. Export and archive reports when performing cross-dataset analysis inside production pipelines."
        ))

        # Save to disk
        pdf_path = OUTPUTS_DIR / f"{run_id}_report.pdf"
        try:
            pdf.output(str(pdf_path))
            logger.info("[Report] Successfully generated PDF at %s", pdf_path)
            return pdf_path
        except Exception as e:
            logger.exception("[Report] Failed to write PDF document: %s", e)
            return None


report_generator = ReportGenerator()
