from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover - pyproject dev deps include pyyaml.
    yaml = None

SCHEMA_VERSION = "1.0"
MARKDOWN_EXTENSIONS = {".md", ".markdown"}
EXCLUDED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "artifacts",
    "build",
    "dist",
    "node_modules",
    "outputs",
    "staging",
}
REQUIRED_SKILL_FIELDS = ("name", "description", "version")
REQUIRED_SKILL_SECTIONS = ("when to use", "verification")


@dataclass(frozen=True)
class ToolboxChunk:
    source: str
    kind: str
    text: str
    symbol: str | None = None
    title: str | None = None
    start_line: int | None = None
    end_line: int | None = None

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "source": self.source,
            "symbol": self.symbol,
            "title": self.title,
            "text": self.text,
            "start_line": self.start_line,
            "end_line": self.end_line,
        }


@dataclass(frozen=True)
class SearchResult:
    chunk: ToolboxChunk
    score: float

    def to_jsonable(self) -> dict[str, Any]:
        return {"score": self.score, "chunk": self.chunk.to_jsonable()}


@dataclass(frozen=True)
class ToolboxIndex:
    schema_version: str
    root: str
    chunks: tuple[ToolboxChunk, ...]

    def search(self, query: str, *, top_k: int = 5) -> list[SearchResult]:
        if top_k < 1:
            raise ValueError("top_k must be greater than zero")
        query_terms = _terms(query)
        if not query_terms:
            return []
        results = []
        for chunk in self.chunks:
            haystack = " ".join(
                value or "" for value in (chunk.title, chunk.symbol, chunk.source, chunk.text)
            )
            tokens = _terms(haystack)
            if not tokens:
                continue
            score = _score(query_terms, tokens)
            if score > 0:
                results.append(SearchResult(chunk=chunk, score=round(score, 6)))
        return sorted(
            results,
            key=lambda result: (-result.score, result.chunk.source, result.chunk.symbol or ""),
        )[:top_k]

    def to_jsonable(self) -> dict[str, Any]:
        chunks = [chunk.to_jsonable() for chunk in self.chunks]
        return {
            "schema_version": self.schema_version,
            "root": self.root,
            "document_count": len({chunk.source for chunk in self.chunks}),
            "chunk_count": len(self.chunks),
            "source_digest": _source_digest(chunks),
            "chunks": chunks,
        }


def build_toolbox_index(root: Path | str) -> ToolboxIndex:
    """Build a deterministic documentation index for caller/toolbox support."""

    base = Path(root).resolve()
    if not base.is_dir():
        raise ValueError(f"toolbox root does not exist: {base}")
    chunks = [*_markdown_chunks(base), *_python_doc_chunks(base)]
    return ToolboxIndex(
        schema_version=SCHEMA_VERSION,
        root=str(base),
        chunks=tuple(
            sorted(chunks, key=lambda chunk: (chunk.source, chunk.kind, chunk.symbol or ""))
        ),
    )


def write_toolbox_index(index: ToolboxIndex, output_path: Path | str) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        json.dump(index.to_jsonable(), handle, indent=2, sort_keys=True)
        handle.write("\n")
    return output


def validate_codex_skills(root: Path | str) -> list[str]:
    """Return actionable validation issues for repository-local Codex skills."""

    base = Path(root)
    skill_files = sorted((base / ".codex" / "skills").glob("*/SKILL.md"))
    issues: list[str] = []
    for skill_path in skill_files:
        text = skill_path.read_text(encoding="utf-8")
        frontmatter, body = _split_frontmatter(text)
        if frontmatter is None:
            issues.append(f"{_relative(skill_path, base)} is missing YAML frontmatter")
            continue
        metadata = _load_skill_metadata(frontmatter, skill_path, base, issues)
        if metadata is None:
            continue
        for field in REQUIRED_SKILL_FIELDS:
            if not str(metadata.get(field, "")).strip():
                issues.append(f"{_relative(skill_path, base)} frontmatter missing {field!r}")
        lower_body = body.lower()
        for section in REQUIRED_SKILL_SECTIONS:
            if section not in lower_body:
                issues.append(f"{_relative(skill_path, base)} missing section: {section}")
    return issues


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a deterministic GeoDrill toolbox index.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/toolbox-index.json"),
        help="Machine-readable index output path.",
    )
    parser.add_argument(
        "--validate-skills",
        action="store_true",
        help="Validate repository-local .codex skills before writing the index.",
    )
    args = parser.parse_args(argv)
    if args.validate_skills:
        issues = validate_codex_skills(args.root)
        if issues:
            print(json.dumps({"valid": False, "issues": issues}, indent=2, sort_keys=True))
            return 1
    index = build_toolbox_index(args.root)
    output = write_toolbox_index(index, args.output)
    print(json.dumps({"chunks": len(index.chunks), "output": str(output)}, sort_keys=True))
    return 0


def _markdown_chunks(root: Path) -> list[ToolboxChunk]:
    chunks = []
    for path in _iter_files(root, MARKDOWN_EXTENSIONS):
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        chunks.extend(_markdown_sections(lines, _relative(path, root)))
    return chunks


def _markdown_sections(lines: list[str], source: str) -> list[ToolboxChunk]:
    """Split Markdown by headings so retrieval returns focused cited passages."""

    chunks: list[ToolboxChunk] = []
    title = Path(source).stem.replace("-", " ").title()
    start = 1
    body: list[str] = []

    def emit(end_line: int) -> None:
        text = "\n".join(body).strip()
        if text:
            chunks.append(
                ToolboxChunk(
                    source=source,
                    kind="markdown",
                    title=title,
                    text=text,
                    start_line=start,
                    end_line=max(start, end_line),
                )
            )

    for line_number, line in enumerate(lines, start=1):
        if re.match(r"^#{1,6}\s+\S", line):
            emit(line_number - 1)
            title = line.lstrip("#").strip()
            start = line_number
            body = [line]
        else:
            body.append(line)
    emit(len(lines))
    return chunks


def _python_doc_chunks(root: Path) -> list[ToolboxChunk]:
    chunks = []
    for path in _iter_files(root, {".py"}):
        try:
            module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError:
            continue
        source = _relative(path, root)
        module_doc = ast.get_docstring(module)
        if module_doc:
            node = module.body[0]
            chunks.append(
                ToolboxChunk(
                    source=source,
                    kind="python_module",
                    text=module_doc,
                    start_line=node.lineno,
                    end_line=getattr(node, "end_lineno", node.lineno),
                )
            )
        for node in module.body:
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                if node.name.startswith("_"):
                    continue
                doc = ast.get_docstring(node)
                if not doc:
                    continue
                chunks.append(
                    ToolboxChunk(
                        source=source,
                        kind="python_api",
                        symbol=node.name,
                        text=doc,
                        start_line=node.lineno,
                        end_line=getattr(node, "end_lineno", node.lineno),
                    )
                )
    return chunks


def _iter_files(root: Path, extensions: set[str]) -> list[Path]:
    files = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in extensions:
            continue
        if any(part in EXCLUDED_DIRS for part in path.relative_to(root).parts):
            continue
        files.append(path)
    return sorted(files)


def _first_heading(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or None
    return None


def _terms(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _score(query_terms: list[str], tokens: list[str]) -> float:
    token_counts: dict[str, int] = {}
    for token in tokens:
        token_counts[token] = token_counts.get(token, 0) + 1
    matched = sum(token_counts.get(term, 0) for term in query_terms)
    coverage = len({term for term in query_terms if term in token_counts}) / len(set(query_terms))
    return matched + coverage


def _source_digest(chunks: list[dict[str, Any]]) -> str:
    payload = json.dumps(chunks, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _split_frontmatter(text: str) -> tuple[str | None, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return "\n".join(lines[1:index]), "\n".join(lines[index + 1 :])
    return None, text


def _load_skill_metadata(
    frontmatter: str,
    skill_path: Path,
    root: Path,
    issues: list[str],
) -> dict[str, Any] | None:
    if yaml is None:
        issues.append("pyyaml is unavailable; cannot validate skill frontmatter")
        return None
    try:
        loaded = yaml.safe_load(frontmatter)
    except yaml.YAMLError as error:
        issues.append(f"{_relative(skill_path, root)} frontmatter is invalid YAML: {error}")
        return None
    if not isinstance(loaded, dict):
        issues.append(f"{_relative(skill_path, root)} frontmatter must be a mapping")
        return None
    return loaded


def _relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
