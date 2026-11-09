from tests.helpers import make_csv, make_pdf, upload, wait_ready

BILLING = "Invoice review\nThe billing team reviewed every invoice this week. Each invoice was matched to the billing ledger."
COOKING = "Pasta\nBoil the spaghetti for nine minutes in salted water. Spaghetti needs salt."


def src(client, app, name, pages):
    sid = upload(client, name, make_pdf(pages)).json()["id"]
    wait_ready(client, app, sid)
    return sid


def csv_src(client, app, name="sales.csv"):
    sid = upload(client, name, make_csv(["Region", "Revenue"], [["EMEA", 100]])).json()["id"]
    wait_ready(client, app, sid)
    return sid


def nb(client, name="Finance", rules=None):
    res = client.post("/notebooks", json={"name": name, "rules": rules or []})
    assert res.status_code == 201, res.text
    return res.json()["id"]


def members(client, nid):
    res = client.get(f"/notebooks/{nid}/sources")
    assert res.status_code == 200
    return {m["id"]: m for m in res.json()}


def test_a_file_type_rule_fills_the_notebook_automatically(client, app):
    nid = nb(client, "Sheets", [{"type": "file_type", "value": "spreadsheet"}])
    sheet = csv_src(client, app)
    pdf = src(client, app, "a.pdf", [BILLING])
    got = members(client, nid)
    assert sheet in got and pdf not in got
    later = csv_src(client, app, "more.csv")           # a new upload joins by itself
    assert later in members(client, nid)


def test_keyword_rule_matches_extracted_text_case_insensitively(client, app):
    nid = nb(client, "Finance", [{"type": "keyword", "value": "INVOICE"}])
    billing = src(client, app, "billing.pdf", [BILLING])
    cooking = src(client, app, "cooking.pdf", [COOKING])
    got = members(client, nid)
    assert billing in got and cooking not in got


def test_tag_rule_follows_automatically_derived_tags(client, app):
    nid = nb(client, "Cooking", [{"type": "tag", "value": "spaghetti"}])
    cooking = src(client, app, "cooking.pdf", [COOKING])
    src(client, app, "billing.pdf", [BILLING])
    assert list(members(client, nid)) == [cooking]


def test_pin_in_adds_a_source_no_rule_matches_and_pin_out_removes_a_match(client, app):
    nid = nb(client, "Finance", [{"type": "keyword", "value": "invoice"}])
    billing = src(client, app, "billing.pdf", [BILLING])
    cooking = src(client, app, "cooking.pdf", [COOKING])

    assert client.put(f"/notebooks/{nid}/pins/{cooking}", json={"mode": "in"}).status_code == 200
    assert client.put(f"/notebooks/{nid}/pins/{billing}", json={"mode": "out"}).status_code == 200
    got = members(client, nid)
    assert cooking in got and billing not in got

    client.delete(f"/notebooks/{nid}/pins/{billing}")
    client.delete(f"/notebooks/{nid}/pins/{cooking}")
    got = members(client, nid)
    assert billing in got and cooking not in got        # rules decide again


def test_every_member_says_why_it_is_there(client, app):
    nid = nb(client, "Finance", [{"type": "keyword", "value": "invoice"}])
    billing = src(client, app, "billing.pdf", [BILLING])
    cooking = src(client, app, "cooking.pdf", [COOKING])
    client.put(f"/notebooks/{nid}/pins/{cooking}", json={"mode": "in"})
    got = members(client, nid)
    assert got[billing]["reasons"] == [{"via": "rule", "rule": {"type": "keyword", "value": "invoice"}}]
    assert got[cooking]["reasons"] == [{"via": "pin"}]


def test_one_source_can_belong_to_many_notebooks(client, app):
    a = nb(client, "Finance", [{"type": "keyword", "value": "invoice"}])
    b = nb(client, "Reviews", [{"type": "keyword", "value": "reviewed"}])
    billing = src(client, app, "billing.pdf", [BILLING])
    assert billing in members(client, a) and billing in members(client, b)


def test_editing_rules_changes_membership_immediately_and_renames(client, app):
    nid = nb(client, "Finance", [{"type": "keyword", "value": "invoice"}])
    billing = src(client, app, "billing.pdf", [BILLING])
    cooking = src(client, app, "cooking.pdf", [COOKING])
    res = client.patch(f"/notebooks/{nid}", json={"name": "Kitchen", "rules": [{"type": "keyword", "value": "spaghetti"}]})
    assert res.status_code == 200
    assert res.json()["name"] == "Kitchen"
    got = members(client, nid)
    assert cooking in got and billing not in got


def test_deleting_a_notebook_never_touches_its_sources(client, app):
    nid = nb(client, "Finance", [{"type": "keyword", "value": "invoice"}])
    billing = src(client, app, "billing.pdf", [BILLING])
    assert client.delete(f"/notebooks/{nid}").status_code == 204
    assert client.get(f"/notebooks/{nid}").status_code == 404
    assert [s["id"] for s in client.get("/sources").json()] == [billing]


def test_deleting_a_source_removes_its_pins(client, app):
    nid = nb(client, "Pinned")
    cooking = src(client, app, "cooking.pdf", [COOKING])
    client.put(f"/notebooks/{nid}/pins/{cooking}", json={"mode": "in"})
    client.delete(f"/sources/{cooking}")
    assert members(client, nid) == {}
    assert client.get(f"/notebooks/{nid}").json()["pins"] == []


def test_notebook_list_reports_member_counts(client, app):
    nid = nb(client, "Finance", [{"type": "keyword", "value": "invoice"}])
    src(client, app, "billing.pdf", [BILLING])
    rows = client.get("/notebooks").json()
    assert rows == [{"id": nid, "name": "Finance", "rules": [{"type": "keyword", "value": "invoice"}], "member_count": 1}] or (
        len(rows) == 1 and rows[0]["member_count"] == 1 and rows[0]["name"] == "Finance"
    )


def test_validation_and_unknown_ids(client, app):
    assert client.post("/notebooks", json={"name": "  ", "rules": []}).status_code == 422
    assert client.post("/notebooks", json={"name": "x", "rules": [{"type": "magic", "value": "a"}]}).status_code == 422
    assert client.post("/notebooks", json={"name": "x", "rules": [{"type": "tag", "value": " "}]}).status_code == 422
    assert client.get("/notebooks/nope").status_code == 404
    assert client.patch("/notebooks/nope", json={"name": "x"}).status_code == 404
    nid = nb(client)
    assert client.put(f"/notebooks/{nid}/pins/nope", json={"mode": "in"}).status_code == 404
    cooking = src(client, app, "cooking.pdf", [COOKING])
    assert client.put(f"/notebooks/{nid}/pins/{cooking}", json={"mode": "sideways"}).status_code == 422
