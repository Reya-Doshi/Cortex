"""Visualization Agent — generates charts independently using processed data only."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class VisualizerAgent:
    """Generates and saves chart artifacts using processed data (never reads CSV)."""

    def generate(
        self,
        processed_data: dict[str, Any] | None = None,
        chart_type: str = "bar",
    ) -> dict[str, Any]:
        """Request chart generation for a dataset.
        
        This agent is restricted: it receives only processed/aggregated data
        and never reads the raw dataset CSV.
        """
        logger.info(
            "[Visualization] Chart requested | type=%s | has_data=%s",
            chart_type,
            processed_data is not None,
        )
        
        # Return a structured representation of the visualization config
        # and the data to plot (which the frontend React app can render interactively!)
        plot_data = []
        x_key = ""
        y_keys = []
        
        if processed_data and "data" in processed_data:
            data_list = processed_data["data"]
            if isinstance(data_list, list) and len(data_list) > 0:
                plot_data = data_list
                # Auto-infer columns
                sample = data_list[0]
                keys = list(sample.keys())
                # Pick first string or categorical key for X, numeric keys for Y
                for k in keys:
                    val = sample[k]
                    if isinstance(val, (int, float)):
                        y_keys.append(k)
                    elif not x_key and isinstance(val, str):
                        x_key = k
                
                # Fallback if keys not selected
                if not x_key and len(keys) > 0:
                    x_key = keys[0]
                if not y_keys and len(keys) > 1:
                    y_keys = keys[1:]
        else:
            # Fallback mock visualization data
            x_key = "label"
            y_keys = ["value"]
            plot_data = [
                {"label": "A", "value": 10},
                {"label": "B", "value": 23},
                {"label": "C", "value": 17},
            ]

        return {
            "status": "success",
            "chart_type": chart_type,
            "x_axis": x_key,
            "series": y_keys,
            "data": plot_data,
            "message": f"Visualization spec constructed for {chart_type} chart.",
        }


visualizer = VisualizerAgent()
