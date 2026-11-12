"""Trusted measures over the sales orders table."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field

import commons


@commons.measure(
    description="Approved total booked revenue in USD, optionally for a region."
)
def revenue(
    warehouse: commons.Injected[Any],
    region: Annotated[
        Literal["North", "South"] | None,
        Field(description="North or South; omit for all regions."),
    ] = None,
) -> dict[str, Any]:
    total = warehouse.execute(
        "SELECT COALESCE(SUM(revenue), 0) FROM orders WHERE (? IS NULL OR region = ?)",
        [region, region],
    ).fetchone()[0]
    return {"revenue": total, "currency": "USD"}
