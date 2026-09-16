"""
Data loader for Drilling Report Analysis.

Loads Corpus A (JSON DDRs), Corpus B (tabular CSV DDR), all supporting CSVs,
and reference documents into memory. Designed to be cached by Streamlit.
"""

import json

import pandas as pd
from config import (
    BENCHMARK_PATHS,
    CORPUS_A_DIR,
    CORPUS_A_TEXT_FIELD,
    CORPUS_B_PATH,
    CSV_PATHS,
    REFERENCE_DOCS_DIR,
    REPORT_PATHS,
)


def load_corpus_a() -> pd.DataFrame:
    """Load 75 narrative JSON DDRs into a single DataFrame (keyed on well_name)."""
    records = []
    for json_path in sorted(CORPUS_A_DIR.glob("*.json")):
        with open(json_path) as f:
            record = json.load(f)
        record["_source_file"] = json_path.name
        records.append(record)
    df = pd.DataFrame(records)
    if "report_date" in df.columns:
        df["report_date"] = pd.to_datetime(df["report_date"])
    return df


def load_corpus_b() -> pd.DataFrame:
    """Load tabular DDR CSV — 192 rows, 9 wells, 3 basins (keyed on well_id)."""
    df = pd.read_csv(CORPUS_B_PATH)
    if "report_date" in df.columns:
        df["report_date"] = pd.to_datetime(df["report_date"])
    return df


def load_supporting_csvs() -> dict[str, pd.DataFrame]:
    """Load all operational-context CSVs into a name->DataFrame dict."""
    tables = {}
    for name, path in {**CSV_PATHS, **BENCHMARK_PATHS, **REPORT_PATHS}.items():
        tables[name] = pd.read_csv(path)
    return tables


def load_reference_docs() -> list[dict]:
    """Load markdown reference docs as text chunks with metadata."""
    docs = []
    for md_path in sorted(REFERENCE_DOCS_DIR.glob("*.md")):
        text = md_path.read_text()
        sections = _split_md_sections(text, md_path.stem)
        docs.extend(sections)
    return docs


def _split_md_sections(text: str, doc_name: str) -> list[dict]:
    """Split a markdown document into sections for indexing."""
    sections = []
    current_heading = doc_name
    current_lines = []

    for line in text.split("\n"):
        if line.startswith("# ") or line.startswith("## "):
            if current_lines:
                body = "\n".join(current_lines).strip()
                if body:
                    sections.append(
                        {
                            "source": f"reference_docs/{doc_name}.md",
                            "heading": current_heading,
                            "text": body,
                        }
                    )
            current_heading = line.lstrip("# ").strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        body = "\n".join(current_lines).strip()
        if body:
            sections.append(
                {
                    "source": f"reference_docs/{doc_name}.md",
                    "heading": current_heading,
                    "text": body,
                }
            )
    return sections


def load_narrative_chunks() -> list[dict]:
    """
    Extract all narrative text passages for vector indexing.

    Returns a list of dicts with keys: text, source, well_id, date, metadata.
    Each chunk is one DDR's narrative, tagged with its origin for citation.
    """
    chunks = []

    # Corpus A narratives
    corpus_a = load_corpus_a()
    for _, row in corpus_a.iterrows():
        text = str(row.get(CORPUS_A_TEXT_FIELD, "")).strip()
        if not text:
            continue
        chunks.append(
            {
                "text": text,
                "source": f"corpus_a/{row.get('_source_file', '')}",
                "well_key": row.get("well_name", ""),
                "date": str(row.get("report_date", "")),
                "corpus": "A",
                "metadata": {
                    "depth_ft": row.get("measured_depth_ft"),
                    "formation": row.get("casing_string", ""),
                    "npt_hrs": row.get("npt_hrs"),
                    "npt_description": row.get("npt_description", ""),
                },
            }
        )

    # Corpus B narratives
    corpus_b = load_corpus_b()
    for _, row in corpus_b.iterrows():
        text = str(row.get("remarks", "")).strip()
        if not text:
            continue
        chunks.append(
            {
                "text": text,
                "source": f"corpus_b/daily_drilling_reports.csv:row_{row.get('report_id', '')}",
                "well_key": row.get("well_id", ""),
                "date": str(row.get("report_date", "")),
                "corpus": "B",
                "metadata": {
                    "depth_ft": row.get("measured_depth_ft"),
                    "formation": row.get("formation", ""),
                    "npt_hours": row.get("npt_hours"),
                    "npt_category": row.get("npt_category", ""),
                },
            }
        )

    return chunks


def load_all() -> dict:
    """
    Load everything into a single dict. Intended for Streamlit cache.

    Returns:
        {
            "corpus_a": DataFrame,
            "corpus_b": DataFrame,
            "tables": {name: DataFrame, ...},
            "narrative_chunks": [dict, ...],
            "reference_docs": [dict, ...],
        }
    """
    return {
        "corpus_a": load_corpus_a(),
        "corpus_b": load_corpus_b(),
        "tables": load_supporting_csvs(),
        "narrative_chunks": load_narrative_chunks(),
        "reference_docs": load_reference_docs(),
    }


if __name__ == "__main__":
    data = load_all()
    corpus_a_wells = data["corpus_a"]["well_name"].nunique()
    corpus_b_wells = data["corpus_b"]["well_id"].nunique()
    print(
        f"Corpus A: {len(data['corpus_a'])} reports, "
        f"{corpus_a_wells} wells"
    )
    print(
        f"Corpus B: {len(data['corpus_b'])} reports, "
        f"{corpus_b_wells} wells"
    )
    print(f"Supporting tables: {list(data['tables'].keys())}")
    for name, df in data["tables"].items():
        print(f"  {name}: {len(df)} rows")
    print(f"Narrative chunks: {len(data['narrative_chunks'])}")
    print(f"Reference doc sections: {len(data['reference_docs'])}")
