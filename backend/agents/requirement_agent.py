"""
Agent 1 — Requirement Gathering Agent (LangGraph)

Graph flow:
  interpret_input
       ↓
  check_completeness  ←─────────────────────┐
       ↓                                     │
  [complete?] ──Yes──→ finalize_output       │
       │No                                   │
       ↓                                    │
  generate_question                          │
       ↓                                     │
  [INTERRUPT — wait for user answer]         │
       ↓                                     │
  process_answer ──────────────────────────→─┘
"""
import json
import logging
from typing import TypedDict, Annotated, Optional
import operator

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from agents.rag_client import query_rag
import config

logger = logging.getLogger(__name__)

MAX_QUESTIONS = 5

SECTIONS = ["need", "market_view", "scalability", "success_kpis", "risks", "compliance"]

SECTION_FIELDS = {
    "need": ["why_build", "differentiation", "ux_delta", "cannibalization", "if_not_built"],
    "market_view": ["ecosystem_response", "ecosystem_effort", "regulatory_rbi_view"],
    "scalability": ["demand_supply_anchors", "impact", "product_operations"],
    "success_kpis": ["trust_grievance", "day0_automation", "sgf_frm_impact", "infra_txn_impact"],
    "risks": ["fraud_abuse", "infosec_privacy", "second_order_effects"],
    "compliance": ["compliance_notes"],
}

# --------------------------------------------------------------------------
# LangGraph state
# --------------------------------------------------------------------------

class RequirementState(TypedDict):
    feature_request: str
    messages: Annotated[list[dict], operator.add]   # [{role, content}]
    questions_asked: int
    gathered: dict                                   # section -> field -> value
    current_question: str
    current_question_key: str                        # "section.field" being asked
    status: str                                      # clarifying | complete
    structured_output: Optional[dict]
    rag_context: str


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

async def interpret_input(state: RequirementState) -> dict:
    """Parse the initial feature request and pre-fill what we can."""
    llm = _llm()

    # Pull relevant RAG context
    rag = await query_rag(state["feature_request"], top_k=5)
    rag_context = rag["enriched_context"]

    system = SystemMessage(content=f"""You are an expert product manager analyzing a feature request.
Extract and pre-fill as many of the following fields as possible from the user's input and the RAG context provided.

Return a valid JSON object with this exact structure (use null for unknown fields):
{{
  "need": {{"why_build": null, "differentiation": null, "ux_delta": null, "cannibalization": null, "if_not_built": null}},
  "market_view": {{"ecosystem_response": null, "ecosystem_effort": null, "regulatory_rbi_view": null}},
  "scalability": {{"demand_supply_anchors": null, "impact": null, "product_operations": null}},
  "success_kpis": {{"trust_grievance": null, "day0_automation": null, "sgf_frm_impact": null, "infra_txn_impact": null}},
  "risks": {{"fraud_abuse": null, "infosec_privacy": null, "second_order_effects": null}},
  "compliance": {{"compliance_notes": null}}
}}

RAG Context:
{rag_context}
""")
    human = HumanMessage(content=f"Feature request: {state['feature_request']}")

    response = await llm.ainvoke([system, human])
    try:
        gathered = json.loads(response.content)
    except json.JSONDecodeError:
        # Extract JSON from markdown code block if present
        import re
        match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", response.content)
        gathered = json.loads(match.group(1)) if match else {s: {} for s in SECTIONS}

    return {
        "gathered": gathered,
        "rag_context": rag_context,
        "messages": [{"role": "user", "content": state["feature_request"]}],
    }


def check_completeness(state: RequirementState) -> dict:
    """Identify the next missing field. Sets current_question_key or marks complete."""
    gathered = state.get("gathered", {})

    for section in SECTIONS:
        fields = SECTION_FIELDS[section]
        for field_key in fields:
            value = gathered.get(section, {}).get(field_key)
            if value is None or str(value).strip() == "" or str(value).strip() == "null":
                return {"current_question_key": f"{section}.{field_key}"}

    return {"current_question_key": ""}   # all filled


def _should_continue(state: RequirementState) -> str:
    if state["questions_asked"] >= MAX_QUESTIONS:
        return "finalize"
    if not state.get("current_question_key"):
        return "finalize"
    return "ask"


async def generate_question(state: RequirementState) -> dict:
    """Generate a natural clarification question for the missing field."""
    llm = _llm()
    section, field = state["current_question_key"].split(".", 1)

    field_descriptions = {
        "why_build": "Why should this feature be built? What problem does it solve?",
        "differentiation": "Is this incremental or exponential differentiation from existing solutions?",
        "ux_delta": "What is the user experience improvement (UX delta) for customers?",
        "cannibalization": "Could this cannibalize any existing product or revenue stream?",
        "if_not_built": "What happens if this feature is NOT built?",
        "ecosystem_response": "How will the payment ecosystem (banks, PSPs) respond to this change?",
        "ecosystem_effort": "What effort or cost does the ecosystem need to adopt this?",
        "regulatory_rbi_view": "What is the RBI/regulatory stance or any compliance requirement?",
        "demand_supply_anchors": "What are the demand and supply anchors (volume drivers, capacity)?",
        "impact": "What is the expected impact on users, revenue, and timeline?",
        "product_operations": "What operational changes are needed to support this product?",
        "trust_grievance": "What KPIs measure trust/grievance reduction?",
        "day0_automation": "What day-0 automation is needed for seamless launch?",
        "sgf_frm_impact": "What is the impact on SGF (Settlement Guarantee Fund) and FRM (Fraud Risk Management)?",
        "infra_txn_impact": "What infrastructure and transaction volume impact is expected?",
        "fraud_abuse": "What fraud or abuse vectors could this introduce?",
        "infosec_privacy": "What information security or privacy risks exist?",
        "second_order_effects": "What are the second-order or unintended effects of this feature?",
        "compliance_notes": "Are there any specific compliance or regulatory constraints to note?",
    }

    hint = field_descriptions.get(field, f"Please describe: {field}")
    conversation_so_far = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in state.get("messages", [])
    )

    system = SystemMessage(content="""You are a product manager gathering requirements.
Generate ONE concise, friendly clarification question to fill a missing field.
The question must be specific, actionable, and easy to answer. Do NOT repeat previously asked questions.
Return ONLY the question text, nothing else.""")

    human = HumanMessage(content=f"""
Missing field: {field} (section: {section})
Field context: {hint}
Questions already asked: {state['questions_asked']}

Conversation so far:
{conversation_so_far}

Generate the next clarification question:""")

    response = await llm.ainvoke([system, human])
    question = response.content.strip()

    return {
        "current_question": question,
        "messages": [{"role": "agent", "content": question}],
        "questions_asked": state["questions_asked"] + 1,
    }


async def process_answer(state: RequirementState) -> dict:
    """Parse the user's latest answer and store into gathered state."""
    llm = _llm()
    section, field = state["current_question_key"].split(".", 1)
    last_user_msg = state["messages"][-1]["content"]

    system = SystemMessage(content=f"""Extract the answer to the question about field '{field}' in section '{section}'.
Return a concise 1-3 sentence summary of the answer. Return ONLY the answer text.""")
    human = HumanMessage(content=last_user_msg)

    response = await llm.ainvoke([system, human])
    extracted = response.content.strip()

    # Deep-copy gathered and update the specific field
    gathered = {s: dict(fields) for s, fields in state["gathered"].items()}
    if section not in gathered:
        gathered[section] = {}
    gathered[section][field] = extracted

    return {"gathered": gathered}


async def finalize_output(state: RequirementState) -> dict:
    """
    Fill any still-null fields using RAG + web context, then produce final JSON.
    """
    llm = _llm()
    gathered = state["gathered"]

    # For sections still missing data, try RAG auto-fill
    for section in SECTIONS:
        fields = SECTION_FIELDS[section]
        for field_key in fields:
            value = gathered.get(section, {}).get(field_key)
            if value is None or str(value).strip() in ("", "null"):
                rag = await query_rag(
                    f"{state['feature_request']} - {section} - {field_key}",
                    top_k=3,
                )
                if rag["results"]:
                    # Ask LLM to infer the field from RAG context
                    sys_msg = SystemMessage(content=f"""Based on the context below, infer a plausible value for:
Section: {section}, Field: {field_key}
Return a 1-2 sentence inference. If not determinable, return 'To be determined based on detailed analysis.'""")
                    h_msg = HumanMessage(content=rag["enriched_context"][:2000])
                    r = await llm.ainvoke([sys_msg, h_msg])
                    if section not in gathered:
                        gathered[section] = {}
                    gathered[section][field_key] = r.content.strip()

    farewell = ("Thank you! I have gathered all the information needed. "
                "Proceeding to generate the deep research report...")

    return {
        "structured_output": gathered,
        "status": "complete",
        "messages": [{"role": "agent", "content": farewell}],
    }


# --------------------------------------------------------------------------
# Graph construction
# --------------------------------------------------------------------------

def build_requirement_graph() -> StateGraph:
    workflow = StateGraph(RequirementState)

    workflow.add_node("interpret_input", interpret_input)
    workflow.add_node("check_completeness", check_completeness)
    workflow.add_node("generate_question", generate_question)
    workflow.add_node("process_answer", process_answer)
    workflow.add_node("finalize_output", finalize_output)

    workflow.set_entry_point("interpret_input")
    workflow.add_edge("interpret_input", "check_completeness")

    workflow.add_conditional_edges(
        "check_completeness",
        _should_continue,
        {"ask": "generate_question", "finalize": "finalize_output"},
    )

    # After generating a question, interrupt and wait for user input
    workflow.add_edge("generate_question", END)   # Pause here; resume with process_answer

    workflow.add_edge("process_answer", "check_completeness")
    workflow.add_edge("finalize_output", END)

    return workflow


# Compile with memory checkpointer for stateful multi-turn
_checkpointer = MemorySaver()
requirement_graph = build_requirement_graph().compile(checkpointer=_checkpointer)


# --------------------------------------------------------------------------
# Public API used by the router
# --------------------------------------------------------------------------

async def start_requirement_gathering(session_id: str, feature_request: str) -> dict:
    """
    Start a new requirement gathering session.
    Returns agent state after first question is generated.
    """
    config_dict = {"configurable": {"thread_id": session_id}}
    initial_state = {
        "feature_request": feature_request,
        "messages": [],
        "questions_asked": 0,
        "gathered": {s: {f: None for f in SECTION_FIELDS[s]} for s in SECTIONS},
        "current_question": "",
        "current_question_key": "",
        "status": "clarifying",
        "structured_output": None,
        "rag_context": "",
    }
    result = await requirement_graph.ainvoke(initial_state, config=config_dict)
    return result


async def answer_clarification(session_id: str, answer: str) -> dict:
    """
    Resume the graph with the user's answer.
    """
    config_dict = {"configurable": {"thread_id": session_id}}

    # Get current state snapshot
    snapshot = requirement_graph.get_state(config_dict)
    current = snapshot.values

    # If already complete, just return current state
    if current.get("status") == "complete":
        return current

    # Append user answer to messages and route to process_answer
    updated_messages = current.get("messages", []) + [{"role": "user", "content": answer}]

    result = await requirement_graph.ainvoke(
        {**current, "messages": updated_messages},
        config=config_dict,
    )
    return result
