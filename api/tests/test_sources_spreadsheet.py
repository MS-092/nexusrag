from tests.helpers import make_csv, make_xlsx, upload, wait_ready

HEADER = ["Region", "Revenue"]


def rows(n: int):
    return [[f"Region{i}", 1000 + i] for i in range(n)]


def test_csv_is_ingested_with_header_repeated_in_every_block(client, app):
    sid = upload(client, "sales.csv", make_csv(HEADER, rows(120))).json()["id"]
    done = wait_ready(client, app, sid)
    assert done["state"] == "ready"
    assert done["kind"] == "spreadsheet"
    # 120 data rows at <= 50 rows per block means at least 3 blocks,
    # and every block carries the header so a row never loses its columns.
    assert done["chunk_count"] >= 3
    assert done["extracted_text"].count("Columns: Region | Revenue") >= 3
    assert "Region: Region7 | Revenue: 1007" in done["extracted_text"]


def test_blocks_never_exceed_fifty_rows(client, app):
    sid = upload(client, "wide.csv", make_csv(["A"], [[i] for i in range(51)])).json()["id"]
    done = wait_ready(client, app, sid)
    assert done["chunk_count"] >= 2     # 51 rows cannot fit in one 50-row block


def test_xlsx_multi_sheet_is_split_per_sheet(client, app):
    data = make_xlsx({"Q1": (HEADER, rows(3)), "Q2": (HEADER, rows(2))})
    sid = upload(client, "book.xlsx", data).json()["id"]
    done = wait_ready(client, app, sid)
    assert done["state"] == "ready"
    assert "Sheet: Q1" in done["extracted_text"]
    assert "Sheet: Q2" in done["extracted_text"]
    assert done["chunk_count"] >= 2


def test_empty_spreadsheet_fails_clearly(client, app):
    sid = upload(client, "empty.csv", make_csv(HEADER, [])).json()["id"]
    done = wait_ready(client, app, sid)
    assert done["state"] == "failed"
    assert "rows" in done["error"].lower()


def test_unreadable_xlsx_fails_with_a_message(client, app):
    sid = upload(client, "bad.xlsx", b"not a workbook").json()["id"]
    done = wait_ready(client, app, sid)
    assert done["state"] == "failed"
    assert done["error"]
