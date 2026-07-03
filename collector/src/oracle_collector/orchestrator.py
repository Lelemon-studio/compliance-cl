from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Callable

from .models import CollectorResult


@dataclass(frozen=True)
class CollectorTask:
    name: str
    collect: Callable[[], CollectorResult]
    region: str | None = None
    fatal: bool = False


def run_tasks(tasks: list[CollectorTask], parallelism: int = 8) -> CollectorResult:
    aggregate = CollectorResult()
    if not tasks:
        return aggregate
    with ThreadPoolExecutor(max_workers=max(1, min(parallelism, len(tasks)))) as executor:
        futures = {executor.submit(task.collect): task for task in tasks}
        for future in as_completed(futures):
            task = futures[future]
            try:
                aggregate.merge(future.result())
            except Exception as exc:  # collectors are isolation boundaries
                error = {
                    "collector": task.name,
                    "error": type(exc).__name__,
                    "fatal": task.fatal,
                }
                if task.region is not None:
                    error["region"] = task.region
                aggregate.errors.append(error)
    aggregate.evidence.sort(key=lambda item: item.id)
    aggregate.errors.sort(key=lambda item: (str(item.get("collector")), str(item.get("region", ""))))
    return aggregate

