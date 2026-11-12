"""A2A server for the hospital operations agent.

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
from measures import hospital_event_counts, hospital_summary
from posit.connect.external.a2a import A2ARequest, create_a2a_app

import commons

HERE = Path(__file__).parent
DATA = HERE / "data"
DEFAULT_MODEL = "anthropic/claude-sonnet-5"

# Shared by every agent. Each agent copies the frame into its own in-process
# database, so no database connection is shared between contexts.
EVENTS = pd.read_parquet(DATA / "hospital_events.parquet")
SEMANTIC_LAYER = commons.semantic_layer(hospital_summary, hospital_event_counts)
CONTEXT_LAYER = commons.context_layer(files=[DATA / "context.md"])

# The agent's additional instructions, kept in a Markdown file so the text can be
# read and edited apart from the code.
INSTRUCTIONS = str(HERE / "instructions.md")

SKILLS = [
    AgentSkill(
        id="ask-hospital-data",
        name="Ask about hospital event data",
        description=(
            "Answers questions about the recorded hospital events: counts by hospital, "
            "event type, or severity level. Use it for hospital event questions that "
            "the summary and count skills do not cover."
        ),
        tags=["hospital", "events", "data"],
        examples=[
            "Which hospital has the most recorded events?",
            "How many events are Level 3 severity?",
        ],
    ),
    AgentSkill(
        id="hospital_summary",
        name="Hospital event summary",
        description=(
            "Approved recorded-event count, plus counts of distinct hospitals, event "
            "types, and severity levels, for all hospitals or one exact hospital name."
        ),
        tags=["hospital", "events", "summary"],
        examples=[
            "How many hospital events are recorded in total?",
            "Summarize the events at Example Port Hospital.",
        ],
    ),
    AgentSkill(
        id="hospital_event_counts",
        name="Hospital event counts",
        description=(
            "Approved recorded-event counts grouped by hospital, event type, or severity "
            "level. These are counts, not incidence rates."
        ),
        tags=["hospital", "events", "counts"],
        examples=[
            "Count the recorded events by event type.",
            "Count the recorded events by severity level.",
        ],
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
    """Build the hospital agent for one A2A context."""
    return commons.Commons(
        client=client(),
        data_sources={
            "hospital": commons.data_source(
                hospital_events=EVENTS, dictionary=DATA / "data-dict.yaml"
            )
        },
        semantic_layer=SEMANTIC_LAYER,
        context_layer=CONTEXT_LAYER,
        instructions=INSTRUCTIONS,
    )


app = create_a2a_app(
    build_agent,
    name="Hospital operations agent",
    description=(
        "Answers questions about synthetic hospital event records: counts of recorded "
        "events by hospital, event type, and severity level. The records hold counts "
        "only, with no dates, patients, or rates. Route hospital event count questions "
        "here."
    ),
    skills=SKILLS,
)
