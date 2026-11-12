"""A2A server for the sales data agent.

Each A2A context gets its own commons agent, built on that context's first
message. The agent needs ANTHROPIC_API_KEY, which Connect injects from an
attached Anthropic integration.
"""

from __future__ import annotations

import os
from pathlib import Path

import chatlas
import pandas as pd
from a2a.types import AgentSkill
from measures import revenue
from posit.connect.external.a2a import A2ARequest, create_a2a_app

import commons

HERE = Path(__file__).parent
DATA = HERE / "data"
DEFAULT_MODEL = "anthropic/claude-sonnet-5"

# Shared by every agent. Each agent copies the frame into its own in-process
# database, so no database connection is shared between contexts.
ORDERS = pd.read_parquet(DATA / "orders.parquet")
SEMANTIC_LAYER = commons.semantic_layer(revenue)
CONTEXT_LAYER = commons.context_layer(files=[DATA / "context.md"])

# The agent's additional instructions, kept in a Markdown file so the text can be
# read and edited apart from the code.
INSTRUCTIONS = str(HERE / "instructions.md")

SKILLS = [
    AgentSkill(
        id="ask-sales-data",
        name="Ask about sales data",
        description=(
            "Answers questions about the demonstration sales orders: booked revenue, "
            "regions, products, customers, and order counts. Use it for sales questions "
            "that the revenue skill does not cover."
        ),
        tags=["sales", "orders", "data"],
        examples=[
            "Which region had the most orders?",
            "How many orders did each product sell?",
        ],
    ),
    AgentSkill(
        id="revenue",
        name="Total revenue",
        description=(
            "Approved total booked revenue in USD, for all regions or for one region "
            "(North or South)."
        ),
        tags=["sales", "revenue"],
        examples=["What was total revenue?", "What was South region revenue?"],
    ),
]


def client() -> chatlas.Chat:
    """Return the chat client. Raise a RuntimeError when no API key is set."""
    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set. Attach the Anthropic integration to this "
            "content on Posit Connect, or export ANTHROPIC_API_KEY for a local run."
        )
    return chatlas.ChatAuto(os.environ.get("COMMONS_CHAT_MODEL") or DEFAULT_MODEL)


def build_agent(_request: A2ARequest) -> commons.Commons:
    """Build the sales agent for one A2A context."""
    return commons.Commons(
        client=client(),
        data_sources={
            "warehouse": commons.data_source(
                orders=ORDERS, dictionary=DATA / "data-dict.yaml"
            )
        },
        semantic_layer=SEMANTIC_LAYER,
        context_layer=CONTEXT_LAYER,
        instructions=INSTRUCTIONS,
    )


app = create_a2a_app(
    build_agent,
    name="Sales data agent",
    description=(
        "Answers questions about demonstration sales orders from a synthetic "
        "warehouse: booked revenue overall and by region, plus order, product, and "
        "customer counts. Route questions about orders, revenue, or sales regions here."
    ),
    skills=SKILLS,
)
