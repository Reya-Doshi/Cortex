"""Tool Executor — runs tools requested by the Planner Agent concurrently where possible."""

from __future__ import annotations

import logging
import time
import concurrent.futures
from datetime import datetime, timezone
from typing import Any

from backend.models import ExecutionPlan, ExecutionResult, ToolResult, ToolStep
from backend.tools import TOOL_REGISTRY

logger = logging.getLogger(__name__)


class ToolExecutor:
    """Executes each step in a planner-produced execution plan concurrently using a thread pool."""

    def execute(self, plan: ExecutionPlan, execution_id: str | None = None) -> ExecutionResult:
        """Run tool steps concurrently using ThreadPoolExecutor while preserving dependency orders."""
        logger.info("[Executor] Starting concurrent plan with %d step(s)", len(plan.steps))
        
        # 1. Topological cycle validation
        try:
            self._topological_sort(plan.steps)
        except ValueError as err:
            logger.error("[Executor] Invalid DAG structure: %s", err)
            return ExecutionResult(
                plan=plan,
                results=[
                    ToolResult(
                        tool="executor",
                        step_id="topological_sort",
                        success=False,
                        error=f"Dependency cycle/error: {err}",
                        start_time=datetime.now(timezone.utc).isoformat(),
                        end_time=datetime.now(timezone.utc).isoformat(),
                        duration_ms=0.0
                    )
                ],
                total_duration_ms=0.0
            )

        steps_map = {step.id: step for step in plan.steps}
        completed_steps: set[str] = set()
        failed_steps: set[str] = set()
        skipped_steps: set[str] = set()
        
        step_outputs: dict[str, Any] = {}
        results_map: dict[str, ToolResult] = {}
        
        # We start wall-clock time
        wall_start_time = time.perf_counter()
        
        # Execute using ThreadPoolExecutor
        max_workers = min(len(plan.steps), 4)  # Limit concurrent threads to 4
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="cortex_agent") as pool:
            active_futures: dict[concurrent.futures.Future, str] = {}
            steps_to_run = list(plan.steps)

            while steps_to_run or active_futures:
                # 1. Find and skip steps that depend on failed steps
                skipped_this_round = []
                for step in steps_to_run:
                    if any(dep_id in failed_steps or dep_id in skipped_steps for dep_id in step.dependencies):
                        skipped_steps.add(step.id)
                        skipped_this_round.append(step)
                        
                        # Add a failed/skipped result
                        results_map[step.id] = ToolResult(
                            tool=step.tool,
                            step_id=step.id,
                            success=False,
                            error=f"Skipped because dependency failed.",
                            start_time=datetime.now(timezone.utc).isoformat(),
                            end_time=datetime.now(timezone.utc).isoformat(),
                            duration_ms=0.0
                        )
                        logger.warning("[Executor] Step '%s' skipped because a dependency failed.", step.id)
                
                # Remove skipped steps from queue
                for s in skipped_this_round:
                    steps_to_run.remove(s)

                # 2. Find steps that are ready (all dependencies completed successfully)
                ready_steps = [
                    step for step in steps_to_run
                    if all(dep_id in completed_steps for dep_id in step.dependencies)
                ]

                # 3. Submit ready steps to the thread pool
                for step in ready_steps:
                    steps_to_run.remove(step)
                    logger.info("[Executor] Scheduling step '%s' (%s) for parallel execution", step.id, step.tool)
                    
                    # Collect dependency outputs
                    dep_outputs = {
                        dep_id: step_outputs[dep_id]
                        for dep_id in step.dependencies
                        if dep_id in step_outputs
                    }
                    
                    # Submit task
                    future = pool.submit(
                        self._run_single_step,
                        step=step,
                        file_path=plan.file_path,
                        dep_outputs=dep_outputs,
                        execution_id=execution_id
                    )
                    active_futures[future] = step.id

                # 4. Wait for at least one active task to complete
                if active_futures:
                    done_futures, _ = concurrent.futures.wait(
                        active_futures.keys(),
                        return_when=concurrent.futures.FIRST_COMPLETED
                    )

                    for future in done_futures:
                        step_id = active_futures.pop(future)
                        try:
                            result = future.result()
                            results_map[step_id] = result
                            if result.success:
                                completed_steps.add(step_id)
                                step_outputs[step_id] = result.output
                                logger.info("[Executor] Step '%s' completed successfully in %.1fms", step_id, result.duration_ms)
                            else:
                                failed_steps.add(step_id)
                                logger.error("[Executor] Step '%s' failed: %s", step_id, result.error)
                        except Exception as e:
                            failed_steps.add(step_id)
                            results_map[step_id] = ToolResult(
                                tool=steps_map[step_id].tool,
                                step_id=step_id,
                                success=False,
                                error=str(e),
                                start_time=datetime.now(timezone.utc).isoformat(),
                                end_time=datetime.now(timezone.utc).isoformat(),
                                duration_ms=0.0
                            )
                            logger.exception("[Executor] Step '%s' raised exception", step_id)

        wall_end_time = time.perf_counter()
        total_duration_ms = (wall_end_time - wall_start_time) * 1000.0

        # Construct final ordered results list
        ordered_results = [results_map[step.id] for step in plan.steps if step.id in results_map]
        
        logger.info(
            "[Executor] Plan execution finished | total_wall_time=%.2fms | succeeded=%d failed=%d",
            total_duration_ms,
            len(completed_steps),
            len(failed_steps) + len(skipped_steps),
        )
        
        return ExecutionResult(plan=plan, results=ordered_results, total_duration_ms=total_duration_ms)

    @staticmethod
    def _run_single_step(step: ToolStep, file_path: str, dep_outputs: dict[str, Any], execution_id: str | None = None) -> ToolResult:
        """Run a single tool step and capture detailed timing metrics."""
        t0 = time.perf_counter()
        start_dt = datetime.now(timezone.utc)
        start_time_str = start_dt.isoformat()
        
        handler = TOOL_REGISTRY.get(step.tool)
        if handler is None:
            t1 = time.perf_counter()
            duration_ms = (t1 - t0) * 1000.0
            return ToolResult(
                tool=step.tool,
                step_id=step.id,
                success=False,
                error=f"Unknown tool: {step.tool}",
                start_time=start_time_str,
                end_time=datetime.now(timezone.utc).isoformat(),
                duration_ms=duration_ms
            )

        try:
            output = handler(
                file_path=file_path,
                dependency_outputs=dep_outputs,
                execution_id=execution_id,
                **step.params
            )
            t1 = time.perf_counter()
            duration_ms = (t1 - t0) * 1000.0
            return ToolResult(
                tool=step.tool,
                step_id=step.id,
                success=True,
                output=output,
                start_time=start_time_str,
                end_time=datetime.now(timezone.utc).isoformat(),
                duration_ms=duration_ms
            )
        except Exception as exc:
            t1 = time.perf_counter()
            duration_ms = (t1 - t0) * 1000.0
            return ToolResult(
                tool=step.tool,
                step_id=step.id,
                success=False,
                error=str(exc),
                start_time=start_time_str,
                end_time=datetime.now(timezone.utc).isoformat(),
                duration_ms=duration_ms
            )

    @staticmethod
    def _topological_sort(steps: list[ToolStep]) -> list[ToolStep]:
        """Perform DFS-based topological sort to validate cyclic dependencies."""
        steps_map = {step.id: step for step in steps}
        visited: dict[str, int] = {}
        ordered: list[ToolStep] = []

        def visit(step_id: str):
            state = visited.get(step_id, 0)
            if state == 1:
                raise ValueError(f"Circular dependency detected in plan involving: {step_id}")
            if state == 2:
                return

            visited[step_id] = 1
            step = steps_map.get(step_id)
            if step:
                for dep_id in step.dependencies:
                    if dep_id in steps_map:
                        visit(dep_id)
                    else:
                        raise ValueError(
                            f"Step '{step_id}' depends on '{dep_id}' which does not exist in the plan."
                        )
            visited[step_id] = 2
            if step:
                ordered.append(step)

        for step in steps:
            if step.id not in visited:
                visit(step.id)

        return ordered


executor = ToolExecutor()
