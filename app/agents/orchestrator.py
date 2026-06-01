"""
app/agents/orchestrator.py

Orchestrator Agent — the entry point of every graph invocation.

Responsibilities:
1. Classify user intent: "search" (find me products) or "watch" (monitor price)
2. Extract a clean product query from the raw natural language input
3. Parse budget constraints ("under $100", "less than 80 dollars")
4. Extract product constraints ("wireless", "black", "USB-C")

In LIVE mode: Uses Groq LLM with structured output (Pydantic schema)
              for robust natural language understanding.
In MOCK mode: Uses regex + keyword matching — no API call needed.

Why structured output instead of free-form text?
  If the LLM returns "The intent is probably a search", parsing that is fragile.
  With .with_structured_output(OrchestratorOutput), LangChain forces the LLM
  to return a valid JSON object matching our Pydantic schema. Type-safe, reliable.
"""

import logging
import re

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.exceptions import LLMError
from app.graph.state import GraphState

logger = logging.getLogger(__name__)

# ── Structured output schema ──────────────────────────────────────────────────

class OrchestratorOutput(BaseModel):
    """The structured output the Orchestrator LLM must return."""
    intent: str = Field(
        description="User intent: 'search' to find products, 'watch' to add to watchlist, "
                    "'unknown' if unclear"
    )
    product_query: str = Field(
        description="Cleaned, search-optimised product query string (e.g. 'wireless headphones')"
    )
    extracted_budget: float | None = Field(
        default=None,
        description="Budget in USD extracted from the query, or null if not mentioned"
    )
    extracted_constraints: list[str] = Field(
        default_factory=list,
        description="Product constraints extracted from the query (e.g. ['wireless', 'USB-C'])"
    )


# ── LLM setup ────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are a product search assistant. Analyse user queries and extract structured information.

Rules:
- intent is "search" when the user wants product recommendations
- intent is "watch" when they say "watch", "track", "alert me", "notify me", "monitor"
- intent is "unknown" for greetings, off-topic queries, or completely ambiguous input
- product_query should be concise and suitable for a Google Shopping search
- extracted_budget should be in USD as a number (e.g. "$100" → 100.0)
- extracted_constraints are specific requirements beyond the main product type"""

_HUMAN_PROMPT = "Query: {raw_query}"

_prompt = ChatPromptTemplate.from_messages([
    ("system", _SYSTEM_PROMPT),
    ("human", _HUMAN_PROMPT),
])


def _get_llm_chain():
    """Lazily initialise the LLM chain (avoids import errors at startup in mock mode)."""
    from langchain_groq import ChatGroq  # type: ignore[import]

    llm = ChatGroq(
        model=settings.GROQ_MODEL,
        api_key=settings.GROQ_API_KEY,
        temperature=0,  # Deterministic output for classification tasks
    )
    return _prompt | llm.with_structured_output(OrchestratorOutput)


# ── Mock implementation ───────────────────────────────────────────────────────

_WATCH_KEYWORDS = {"watch", "track", "alert", "notify", "monitor", "follow", "remind"}
_BUDGET_PATTERN = re.compile(
    r"(?:under|below|less than|max|budget|within|up to)?\s*\$?(\d+(?:\.\d{1,2})?)\s*(?:dollars?|usd)?",
    re.IGNORECASE,
)
_STOP_WORDS = {
    "a", "an", "the", "for", "best", "good", "great", "me", "i", "want",
    "need", "find", "show", "get", "buy", "purchase", "looking", "is", "are",
    "under", "below", "above", "over", "less", "than", "within", "budget",
    "dollars", "dollar", "usd", "please", "some", "any", "with",
}


def _mock_classify(raw_query: str) -> OrchestratorOutput:
    """Rule-based classification without LLM."""
    query_lower = raw_query.lower()
    words = set(query_lower.split())

    # Detect intent
    intent = "watch" if words & _WATCH_KEYWORDS else "search"

    # Extract budget
    budget_match = _BUDGET_PATTERN.search(raw_query)
    extracted_budget = float(budget_match.group(1)) if budget_match else None

    # Build clean product query (remove stop words + budget phrases)
    clean_words = [
        w for w in query_lower.split()
        if w not in _STOP_WORDS and not w.startswith("$") and not w.isdigit()
    ]
    product_query = " ".join(clean_words).strip() or raw_query

    # Extract constraints (short, specific words after main noun)
    constraint_indicators = {"wireless", "bluetooth", "usb-c", "noise", "cancelling",
                             "canceling", "anc", "true", "gaming", "professional",
                             "lightweight", "waterproof", "portable", "foldable"}
    extracted_constraints = [w for w in query_lower.split() if w in constraint_indicators]

    return OrchestratorOutput(
        intent=intent,
        product_query=product_query,
        extracted_budget=extracted_budget,
        extracted_constraints=extracted_constraints,
    )


# ── Node function ─────────────────────────────────────────────────────────────

async def orchestrator_node(state: GraphState) -> GraphState:
    """
    LangGraph node: classify intent and extract structured query info.

    This is the entry point of the graph. Every invocation passes through here.
    """
    raw_query = state["raw_query"]
    logger.info("[Orchestrator] Processing query: '%s'", raw_query[:100])

    try:
        if state.get("use_mock", True) or settings.USE_MOCK_DATA:
            output = _mock_classify(raw_query)
            logger.debug("[Orchestrator] Mock classification: intent=%s", output.intent)
        else:
            chain = _get_llm_chain()
            output: OrchestratorOutput = await chain.ainvoke({"raw_query": raw_query})
            logger.debug("[Orchestrator] LLM classification: intent=%s", output.intent)

        return {
            **state,
            "intent": output.intent,
            "product_query": output.product_query,
            "extracted_budget": output.extracted_budget,
            "extracted_constraints": output.extracted_constraints,
        }

    except Exception as e:
        logger.error("[Orchestrator] Failed: %s", str(e))
        return {
            **state,
            "intent": "unknown",
            "product_query": raw_query,
            "extracted_budget": None,
            "extracted_constraints": [],
            "error": str(e),
            "error_node": "orchestrator",
        }
