"""
Agent 3 — Product Canvas Generator (LangGraph)

Graph flow:
  generate_canvas
       ↓
  [READY — sections editable/regeneratable]
       ↓ (on regenerate_section request)
  regenerate_section  →  merge_section  →  [READY]
"""
import json
import logging
import io
from typing import TypedDict, Annotated, Optional
import operator
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from agents.rag_client import query_rag
import config

logger = logging.getLogger(__name__)

CANVAS_SECTIONS = [
    {"key": "executive_summary",  "title": "Executive Summary"},
    {"key": "need",               "title": "Need & Problem Statement"},
    {"key": "market_view",        "title": "Market View & Regulatory Landscape"},
    {"key": "scalability",        "title": "Scalability & Growth Anchors"},
    {"key": "success_kpis",       "title": "Success KPIs & Metrics"},
    {"key": "risks",              "title": "Risks & Mitigations"},
    {"key": "compliance",         "title": "Compliance & Regulatory Requirements"},
    {"key": "recommendation",     "title": "Recommendation & Next Steps"},
]

CANVAS_SECTION_KEYS = [s["key"] for s in CANVAS_SECTIONS]
CANVAS_TITLE_MAP = {s["key"]: s["title"] for s in CANVAS_SECTIONS}

SECTION_FORMAT_INSTRUCTIONS = {
    "executive_summary": "Write a 150-200 word executive summary suitable for senior leadership. Cover the problem, proposed solution, market opportunity, and recommendation.",
    "need": "Write the Need section of a product canvas. Include: problem statement, differentiation (incremental/exponential), UX improvement, cannibalization risk, and cost of inaction.",
    "market_view": "Write the Market View section. Include: ecosystem response, effort/cost for participants, RBI regulatory view, and competitive landscape.",
    "scalability": "Write the Scalability section. Include: demand/supply anchors, projected user and revenue impact, and operational requirements.",
    "success_kpis": "Write the Success KPIs section as a structured table/list: KPI name, target value, measurement method, and timeline.",
    "risks": "Write the Risks & Mitigations section as a structured list. For each risk: category (fraud/infosec/operational), description, severity, and mitigation strategy.",
    "compliance": "Write the Compliance section listing: applicable RBI/NPCI circulars, requirements, timeline for compliance, and responsible team.",
    "recommendation": "Write a clear Recommendation section: Go/No-Go recommendation with rationale, proposed launch timeline, key dependencies, and immediate next steps.",
}


# --------------------------------------------------------------------------
# LangGraph state
# --------------------------------------------------------------------------

class CanvasState(TypedDict):
    research_report: dict             # full report from Agent 2
    requirement_output: dict          # from Agent 1
    sections: Annotated[dict, lambda a, b: {**a, **b}]   # key -> content
    section_versions: dict            # key -> version number
    canvas_versions: list[dict]       # full canvas snapshots
    current_version: int
    target_section: Optional[str]     # for single-section regen
    regen_instructions: Optional[str]
    status: str


# --------------------------------------------------------------------------
# LLM
# --------------------------------------------------------------------------

def _llm():
    return ChatOpenAI(
        model=config.MODEL_NAME,
        api_key=config.OPENAI_API_KEY,
        temperature=0.3,
    )


# --------------------------------------------------------------------------
# Nodes
# --------------------------------------------------------------------------

async def _generate_single_section(
    key: str,
    research_report: dict,
    requirement_output: dict,
    existing_content: Optional[str] = None,
    instructions: Optional[str] = None,
) -> str:
    llm = _llm()

    # Find matching research section
    research_section_content = ""
    for sec in research_report.get("sections", []):
        if sec.get("key") == key or sec.get("key") in key:
            research_section_content = sec.get("content", "")
            break

    if not research_section_content:
        # Use full report summary as fallback
        research_section_content = research_report.get("summary", "")

    req_section = json.dumps(requirement_output.get(key, requirement_output), indent=2)[:1000]

    format_instruction = SECTION_FORMAT_INSTRUCTIONS.get(key, f"Write the {key} section for a product canvas.")

    parts = [
        f"You are writing the '{CANVAS_TITLE_MAP.get(key, key)}' section of a Product Canvas document.",
        f"\nFormat instruction: {format_instruction}",
        f"\n\nResearch content:\n{research_section_content[:3000]}",
        f"\n\nRequirement data:\n{req_section}",
    ]

    if existing_content and instructions:
        parts.append(f"\n\nExisting content to refine:\n{existing_content}")
        parts.append(f"\n\nRefinement instructions:\n{instructions}")

    parts.append("\n\nWrite the section now using professional product document language. Use markdown formatting.")

    system = SystemMessage(content="You are a senior product manager writing a Product Canvas document for a UPI/payments feature. Be concise, structured, and data-driven.")
    human = HumanMessage(content="\n".join(parts))

    response = await llm.ainvoke([system, human])
    return response.content.strip()


async def generate_canvas(state: CanvasState) -> dict:
    """Generate all canvas sections from the research report."""
    research_report = state["research_report"]
    requirement_output = state["requirement_output"]

    new_sections = {}
    new_section_versions = {}

    for sec in CANVAS_SECTIONS:
        key = sec["key"]
        content = await _generate_single_section(key, research_report, requirement_output)
        new_sections[key] = content
        new_section_versions[key] = 1
        logger.info(f"Generated canvas section: {key}")

    new_version = 1
    canvas_snapshot = {
        "version": new_version,
        "sections": [
            {
                "key": k,
                "title": CANVAS_TITLE_MAP[k],
                "content": new_sections[k],
                "version": 1,
            }
            for k in CANVAS_SECTION_KEYS
        ],
    }

    return {
        "sections": new_sections,
        "section_versions": new_section_versions,
        "canvas_versions": [canvas_snapshot],
        "current_version": new_version,
        "status": "ready",
        "target_section": None,
        "regen_instructions": None,
    }


async def regenerate_section(state: CanvasState) -> dict:
    """Regenerate a single section, preserving all others."""
    key = state["target_section"]
    if not key or key not in CANVAS_SECTION_KEYS:
        logger.warning(f"Invalid section key for regeneration: {key}")
        return {"status": "ready"}

    content = await _generate_single_section(
        key=key,
        research_report=state["research_report"],
        requirement_output=state["requirement_output"],
        existing_content=state["sections"].get(key),
        instructions=state.get("regen_instructions"),
    )

    new_sections = {**state["sections"], key: content}
    new_section_versions = {**state.get("section_versions", {}), key: state.get("section_versions", {}).get(key, 1) + 1}

    # Save canvas snapshot
    new_version = state["current_version"] + 1
    canvas_snapshot = {
        "version": new_version,
        "sections": [
            {
                "key": k,
                "title": CANVAS_TITLE_MAP[k],
                "content": new_sections[k],
                "version": new_section_versions.get(k, 1),
            }
            for k in CANVAS_SECTION_KEYS
        ],
    }
    versions = list(state.get("canvas_versions", []))
    versions.append(canvas_snapshot)

    return {
        "sections": new_sections,
        "section_versions": new_section_versions,
        "canvas_versions": versions,
        "current_version": new_version,
        "status": "ready",
        "target_section": None,
        "regen_instructions": None,
    }


def update_section_manual(state: CanvasState, key: str, content: str) -> dict:
    """Apply a user's manual edit to a section (not a graph node, called directly)."""
    new_sections = {**state["sections"], key: content}
    new_sv = {**state.get("section_versions", {}), key: state.get("section_versions", {}).get(key, 1) + 1}
    new_version = state["current_version"] + 1
    canvas_snapshot = {
        "version": new_version,
        "sections": [
            {
                "key": k,
                "title": CANVAS_TITLE_MAP[k],
                "content": new_sections[k],
                "version": new_sv.get(k, 1),
            }
            for k in CANVAS_SECTION_KEYS
        ],
    }
    versions = list(state.get("canvas_versions", []))
    versions.append(canvas_snapshot)
    return {
        **state,
        "sections": new_sections,
        "section_versions": new_sv,
        "canvas_versions": versions,
        "current_version": new_version,
    }


# --------------------------------------------------------------------------
# Graph
# --------------------------------------------------------------------------

def _route_after_entry(state: CanvasState) -> str:
    if state.get("target_section"):
        return "regenerate_section"
    return "generate_canvas"


def build_canvas_graph() -> StateGraph:
    workflow = StateGraph(CanvasState)

    workflow.add_node("generate_canvas", generate_canvas)
    workflow.add_node("regenerate_section", regenerate_section)

    workflow.set_entry_point("generate_canvas")
    workflow.add_edge("generate_canvas", END)
    workflow.add_edge("regenerate_section", END)

    return workflow


_checkpointer = MemorySaver()
canvas_graph = build_canvas_graph().compile(checkpointer=_checkpointer)


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------

async def generate_product_canvas(
    session_id: str,
    research_report: dict,
    requirement_output: dict,
) -> dict:
    config_dict = {"configurable": {"thread_id": f"canvas_{session_id}"}}
    initial_state = {
        "research_report": research_report,
        "requirement_output": requirement_output,
        "sections": {},
        "section_versions": {},
        "canvas_versions": [],
        "current_version": 0,
        "target_section": None,
        "regen_instructions": None,
        "status": "generating",
    }
    result = await canvas_graph.ainvoke(initial_state, config=config_dict)
    return result


async def regenerate_canvas_section(
    session_id: str,
    section_key: str,
    instructions: Optional[str] = None,
) -> dict:
    config_dict = {"configurable": {"thread_id": f"canvas_{session_id}"}}
    snapshot = canvas_graph.get_state(config_dict)
    current = snapshot.values

    updated = {
        **current,
        "target_section": section_key,
        "regen_instructions": instructions,
    }
    # Directly invoke regenerate_section node
    result = await canvas_graph.ainvoke(updated, config=config_dict)
    return result


async def update_canvas_section_manually(
    session_id: str,
    section_key: str,
    content: str,
) -> dict:
    config_dict = {"configurable": {"thread_id": f"canvas_{session_id}"}}
    snapshot = canvas_graph.get_state(config_dict)
    current = dict(snapshot.values)
    updated = update_section_manual(current, section_key, content)
    # Write back to checkpointer
    canvas_graph.update_state(config_dict, updated)
    return updated


# --------------------------------------------------------------------------
# Export helpers
# --------------------------------------------------------------------------

def _build_canvas_markdown(sections: dict) -> str:
    lines = ["# Product Canvas\n"]
    for sec in CANVAS_SECTIONS:
        key = sec["key"]
        title = sec["title"]
        content = sections.get(key, "_Not generated yet._")
        lines.append(f"## {title}\n\n{content}\n")
    return "\n---\n\n".join(lines)


def export_docx(sections: dict) -> bytes:
    """Generate DOCX from canvas sections."""
    from docx import Document
    from docx.shared import Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    import re

    doc = Document()

    # Title
    title = doc.add_heading("Product Canvas", 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    for sec in CANVAS_SECTIONS:
        key = sec["key"]
        title_text = sec["title"]
        content = sections.get(key, "Not generated yet.")

        doc.add_heading(title_text, level=1)

        # Render markdown-ish content: strip ** for bold, handle bullet points
        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith("### "):
                doc.add_heading(line[4:], level=3)
            elif line.startswith("## "):
                doc.add_heading(line[3:], level=2)
            elif line.startswith("- ") or line.startswith("* "):
                p = doc.add_paragraph(style="List Bullet")
                p.add_run(re.sub(r"\*\*(.+?)\*\*", r"\1", line[2:]))
            else:
                p = doc.add_paragraph()
                # Handle **bold** markers inline
                parts = re.split(r"(\*\*.+?\*\*)", line)
                for part in parts:
                    if part.startswith("**") and part.endswith("**"):
                        run = p.add_run(part[2:-2])
                        run.bold = True
                    else:
                        p.add_run(part)

        doc.add_paragraph()  # spacing

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()


def export_pdf(sections: dict) -> bytes:
    """Generate PDF from canvas sections using markdown → HTML → PDF."""
    import markdown
    from weasyprint import HTML

    md_content = _build_canvas_markdown(sections)
    html_body = markdown.markdown(md_content, extensions=["tables", "fenced_code"])

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: Arial, sans-serif; margin: 40px; font-size: 13px; line-height: 1.6; color: #222; }}
  h1 {{ color: #1a3c6e; border-bottom: 2px solid #1a3c6e; padding-bottom: 6px; }}
  h2 {{ color: #2a5db0; margin-top: 30px; }}
  h3 {{ color: #444; }}
  hr {{ border: none; border-top: 1px solid #ccc; margin: 24px 0; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ border: 1px solid #ccc; padding: 6px 10px; text-align: left; }}
  th {{ background: #f0f4fa; }}
  ul {{ margin: 6px 0 6px 20px; }}
</style>
</head>
<body>{html_body}</body>
</html>"""

    pdf_bytes = HTML(string=html).write_pdf()
    return pdf_bytes
