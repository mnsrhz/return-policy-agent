from __future__ import annotations

import functools
import os
from pathlib import Path
from typing import Any, Callable, Dict, Optional, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def load_env_file(path: str | Path = ".env") -> Dict[str, str]:
    values: Dict[str, str] = {}
    env_path = Path(path)
    if not env_path.exists():
        return values
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        values[key] = value
        os.environ.setdefault(key, value)
    return values


def tracing_enabled() -> bool:
    load_env_file()
    tracing_requested = os.getenv("LANGCHAIN_TRACING_V2", "").lower() in {"1", "true", "yes", "on"}
    return tracing_requested and bool(os.getenv("LANGCHAIN_API_KEY"))


def langsmith_available() -> bool:
    try:
        import langsmith  # noqa: F401
    except Exception:
        return False
    return True


def require_langsmith() -> None:
    if not langsmith_available():
        raise RuntimeError(
            "The langsmith package is not installed. Run `.venv/bin/pip install -r requirements.txt` "
            "before using LangSmith scripts."
        )
    if not os.getenv("LANGCHAIN_API_KEY"):
        load_env_file()
    if not os.getenv("LANGCHAIN_API_KEY"):
        raise RuntimeError("LANGCHAIN_API_KEY is not configured. Add it to `.env` or your shell environment.")


def trace_function(
    name: str,
    func: F,
    *args: Any,
    run_type: str = "chain",
    metadata: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> Any:
    if not tracing_enabled() or not langsmith_available():
        return func(*args, **kwargs)

    from langsmith import traceable

    try:
        traced = traceable(name=name, run_type=run_type, metadata=metadata or {})(func)
    except TypeError:
        traced = traceable(name=name, run_type=run_type)(func)
    return traced(*args, **kwargs)


def traceable_function(name: str, *, run_type: str = "chain", metadata: Optional[Dict[str, Any]] = None):
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return trace_function(
                name,
                func,
                *args,
                run_type=run_type,
                metadata=metadata,
                **kwargs,
            )

        return wrapper  # type: ignore[return-value]

    return decorator


def run_traced_agent(agent: Any, payload: Dict[str, Any], *, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return trace_function(
        "top_level_agent_run",
        agent.run,
        payload,
        run_type="chain",
        metadata=metadata or {},
    )
