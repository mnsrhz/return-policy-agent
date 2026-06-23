from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Union

from return_agent.models import PolicyDocument


def load_policy_documents(policy_dir: Union[str, Path]) -> List[PolicyDocument]:
    """Load local markdown policy documents from a directory."""
    directory = Path(policy_dir)
    if not directory.exists():
        raise FileNotFoundError(f"Policy directory not found: {directory}")
    if not directory.is_dir():
        raise NotADirectoryError(f"Policy path is not a directory: {directory}")

    documents = []
    for path in _iter_policy_files(directory):
        documents.append(
            PolicyDocument(
                name=path.name,
                path=str(path),
                text=path.read_text(encoding="utf-8"),
            )
        )
    return documents


def _iter_policy_files(directory: Path) -> Iterable[Path]:
    return sorted(
        path
        for path in directory.glob("*.md")
        if path.name != "README.md" and path.is_file()
    )
