import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from nexusrag.config import Settings
from nexusrag.main import create_app
from tests.helpers import make_pdf, upload, wait_ready

KEY = "sk-live-SECRET-0123456789abcdef"
FINANCE = ["Quarterly report\nRevenue in Q3 was 4.2 million dollars. Headcount grew to 118 people."]
COOKING = ["Pasta\nBoil the spaghetti for nine minutes in salted water. Spaghetti needs salt."]
BILLING = ["Invoice review\nThe billing team reviewed every invoice. Invoice totals were confirmed by finance."]
PRIVATE = ["Diary\nThe safe code is 4471 and the hiding spot is the attic."]


def hdrs(base):
    return {"X-Provider": "openai-compatible", "X-Provider-Model": "m", "X-Provider-Key": KEY, "X-Provider-Base-Url": base}


def src(client, app, name, pages, private=False):
    res = client.post(f"/sources{'?private=true' if private else ''}", files={"file": (name, make_pdf(pages), "application/pdf")})
    sid = res.json()["id"]
    wait_ready(client, app, sid)
    return sid


def say(client, text, scope=None, headers=None):
    body = {"question": text}
    if scope:
        body["scope"] = scope
    return client.post("/chat", json=body, headers=headers or {})


def shipped_instruction(settings, name):
    return (Path(settings.skills_dir) / f"{name}.md").read_text()


def test_shipped_skills_are_listed_with_descriptions(client):
    res = client.get("/skills")
    assert res.status_code == 200
    by_name = {s["name"]: s for s in res.json()}
    assert "summarize" in by_name
    assert by_name["summarize"]["description"]
    assert by_name["summarize"]["usage"].startswith("/summarize")


def test_summarize_without_an_argument_covers_the_whole_scope(client, app, settings, fake_provider):
    src(client, app, "finance.pdf", FINANCE)
    src(client, app, "cooking.pdf", COOKING)
    src(client, app, "diary.pdf", PRIVATE, private=True)
    fake_provider.reply = "Finance and cooking material [1][2]."
    body = say(client, "/summarize", headers=hdrs(fake_provider.base_url)).json()
    assert body["mode"] == "model"
    assert body["skill"] == "summarize"
    assert {c["source_name"] for c in body["citations"]} == {"finance.pdf", "cooking.pdf"}

    sent = fake_provider.requests[0]
    assert "4.2 million" in sent.raw and "spaghetti" in sent.raw
    assert "4471" not in fake_provider.all_text()                      # Private Source never sent
    system = sent.body["messages"][0]["content"]
    assert "summary" in system.lower()                                  # the Skill's own instruction travels as the system prompt


def test_summarize_respects_a_notebook_scope(client, app, fake_provider):
    src(client, app, "finance.pdf", FINANCE)
    src(client, app, "cooking.pdf", COOKING)
    nid = client.post("/notebooks", json={"name": "Kitchen", "rules": [{"type": "keyword", "value": "spaghetti"}]}).json()["id"]
    fake_provider.reply = "Kitchen notes [1]."
    body = say(client, "/summarize", {"type": "notebook", "id": nid}, hdrs(fake_provider.base_url)).json()
    assert {c["source_name"] for c in body["citations"]} == {"cooking.pdf"}
    assert "4.2 million" not in fake_provider.all_text()


def test_summarize_a_named_source_makes_it_primary_but_others_stay_citable(client, app, fake_provider):
    finance = src(client, app, "finance.pdf", FINANCE)
    src(client, app, "billing.pdf", BILLING)
    src(client, app, "cooking.pdf", COOKING)
    fake_provider.reply = "The finance report covers revenue [1]."
    body = say(client, "/summarize finance.pdf", headers=hdrs(fake_provider.base_url)).json()
    assert body["citations"][0]["source_id"] == finance                 # the named Source leads
    assert "4.2 million" in fake_provider.requests[0].raw
    assert body["mode"] == "model"


def test_summarize_a_topic_retrieves_within_the_scope(client, app, fake_provider):
    src(client, app, "billing.pdf", BILLING)
    src(client, app, "cooking.pdf", COOKING)
    fake_provider.reply = "Invoices were reviewed [1]."
    body = say(client, "/summarize invoice totals", headers=hdrs(fake_provider.base_url)).json()
    assert body["citations"][0]["source_name"] == "billing.pdf"
    assert "spaghetti" not in fake_provider.requests[0].raw


def test_skills_work_offline_with_an_extractive_summary(client, app, fake_provider):
    src(client, app, "finance.pdf", FINANCE)
    body = say(client, "/summarize").json()
    assert body["mode"] == "extractive"
    assert body["citations"][0]["source_name"] == "finance.pdf"
    assert "Revenue" in body["answer"]
    assert fake_provider.requests == []


def test_an_empty_scope_has_nothing_to_summarize(client, fake_provider):
    body = say(client, "/summarize", headers=hdrs(fake_provider.base_url)).json()
    assert body["mode"] == "no_results"
    assert fake_provider.requests == []


def test_an_unknown_skill_lists_what_is_available(client):
    res = say(client, "/teleport somewhere")
    assert res.status_code == 400
    assert "/summarize" in res.json()["detail"]


def test_slash_commands_are_case_insensitive_and_plain_paths_are_not_skills(client, app):
    src(client, app, "finance.pdf", FINANCE)
    assert say(client, "/Summarize").json()["skill"] == "summarize"
    plain = say(client, "What does /etc/hosts have to do with revenue?")
    assert plain.status_code == 200 and "skill" not in plain.json()


@pytest.fixture
def custom_client(tmp_path, data_dir, settings):
    skills = tmp_path / "skills"
    shutil.copytree(settings.skills_dir, skills)
    (skills / "shout.md").write_text(
        "---\nname: shout\ndescription: Answer in capital letters.\nusage: /shout <question>\n---\n"
        "Answer the question using the passages, but write the entire answer in CAPITAL LETTERS.\n"
    )
    app = create_app(Settings(data_dir=data_dir, web_origin=settings.web_origin, skills_dir=skills))
    with TestClient(app, base_url="http://localhost") as c:
        yield c, app


def test_dropping_a_markdown_file_into_the_skills_folder_adds_a_command(custom_client, fake_provider):
    client, app = custom_client
    src(client, app, "finance.pdf", FINANCE)
    assert "shout" in {s["name"] for s in client.get("/skills").json()}
    fake_provider.reply = "REVENUE WAS 4.2 MILLION [1]"
    body = say(client, "/shout what was revenue in Q3?", headers=hdrs(fake_provider.base_url)).json()
    assert body["skill"] == "shout"
    assert body["answer"] == "REVENUE WAS 4.2 MILLION [1]"
    sent = fake_provider.requests[0]
    assert "CAPITAL LETTERS" in sent.body["messages"][0]["content"]       # the user's instruction is the system prompt
    assert "4.2 million" in sent.raw                                       # grounded in retrieved passages


def test_a_skill_file_without_frontmatter_still_works_using_its_filename(custom_client):
    client, app = custom_client
    skills = Path(app.state.settings.skills_dir)
    (skills / "plain.md").write_text("Just answer briefly.")
    assert "plain" in {s["name"] for s in client.get("/skills").json()}
