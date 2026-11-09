"""Deterministic fixture corpus for the retrieval eval. Everything is generated
in code, so there are no binary fixtures to review or drift."""
from __future__ import annotations

from tests.helpers import make_csv, make_pdf, make_png, make_xlsx

PDFS: dict[str, list[str]] = {
    "finance.pdf": [
        "Quarterly report\nRevenue in Q3 was 4.2 million dollars.",
        "Appendix\nHeadcount grew to 118 people across the Jakarta office.",
    ],
    "ops-runbook.pdf": [
        "Incident log\nIncident INC-7731 was escalated to the platform team on Tuesday.",
        "Rollback procedure\nRestart the ingestion worker, then clear the cache.",
    ],
    "hr-policy.pdf": [
        "Annual leave\nEmployees receive 24 days of paid annual leave each year.",
        "Remote work\nStaff may work remotely up to three days per week.",
    ],
    "cooking.pdf": [
        "Pasta\nBoil the spaghetti for nine minutes in salted water.",
        "Sauce\nSimmer the tomatoes with basil for twenty minutes.",
    ],
    "astronomy.pdf": [
        "Nebulae\nThe Orion Nebula is about 1344 light years from Earth.",
        "Moons\nJupiter has at least ninety five known moons.",
    ],
}

NOTE = ("Launch plan", "# Launch plan\nThe beta ships on Friday with the purple theme.\n\n## Codename\nThe codename is Sparrowhawk.")

CHART_TEXT = "Q3 chart 4200 units sold"


def sales_rows() -> list[list[object]]:
    rows: list[list[object]] = [[f"City{i}", 1000 + i, 10 + i] for i in range(120)]
    rows[76] = ["Surabaya", 7777, 99]          # spreadsheet row 78 (header is row 1)
    return rows


INVENTORY = {
    "Warehouse": (["SKU", "Item", "Quantity"], [["SKU-4410", "Hex bolt", 36], ["SKU-5521", "Copper pipe", 12], ["SKU-6632", "Steel plate", 80]]),
    "Returns": (["SKU", "Reason", "Quantity"], [["SKU-4410", "Damaged in transit", 3], ["SKU-7743", "Wrong size", 5]]),
}


def upload_all(client, app) -> dict[str, str]:
    """Upload the corpus through the API. Returns {source name: id}."""
    ids: dict[str, str] = {}

    def up(name: str, data: bytes, mime: str) -> None:
        ids[name] = client.post("/sources", files={"file": (name, data, mime)}).json()["id"]

    for name, pages in PDFS.items():
        up(name, make_pdf(pages), "application/pdf")
    up("sales.csv", make_csv(["Region", "Revenue", "Units"], sales_rows()), "text/csv")
    up("inventory.xlsx", make_xlsx(INVENTORY), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    up("chart.png", make_png(CHART_TEXT), "image/png")
    note = client.post("/notes", json={"title": NOTE[0], "content": NOTE[1]}).json()
    ids[NOTE[0]] = note["id"]
    app.state.jobs.join()
    return ids
