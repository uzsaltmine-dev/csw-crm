"""Import formatlari: .xls, .csv (cp1251 va utf-8), .docx, matnli .pdf — natija .xlsx bilan bir xil."""
import pytest

from tests.test_customers import _import
from tests.xlsx_factory import build, build_csv, build_docx, build_pdf, build_scanned_pdf, build_xls

EXPECTED = {"rows_total": 6, "rows_ok": 5, "rows_skipped": 1, "septic_rows": 1, "customers_new": 3, "customers_existing": 1,
            "contacts_added": 4}


def _summary(b: dict) -> dict:
    return {k: b[k] for k in EXPECTED}


@pytest.mark.parametrize("name,content,kind", [
    ("call-center.xlsx", build, "xlsx"),
    ("eski.xls", build_xls, "xls"),
    ("windows.csv", build_csv, "csv"),
    ("utf8.csv", lambda: build_csv(encoding="utf-8-sig", delimiter=","), "csv"),
    ("hujjat.docx", build_docx, "docx"),
    ("hisobot.pdf", build_pdf, "pdf"),
])
async def test_every_format_gives_same_result(world, client_factory, name, content, kind):
    admin = await client_factory("admin")
    r = await _import(admin, dry_run=True, content=content(), name=name)
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["file_kind"] == kind and _summary(b) == EXPECTED, b
    messages = " ".join(e["message"] for e in b["errors"])
    assert "Tuman topilmadi" in messages and "12345" in messages


async def test_real_import_from_docx_then_pdf_is_idempotent(world, client_factory):
    admin = await client_factory("admin")
    first = (await _import(admin, dry_run=False, content=build_docx(), name="a.docx")).json()
    assert first["customers_new"] == 3 and first["batch_id"]
    again = (await _import(admin, dry_run=False, content=build_pdf(), name="b.pdf")).json()
    assert (again["customers_new"], again["customers_existing"], again["contacts_added"]) == (0, 4, 0)


async def test_format_errors(world, client_factory):
    admin = await client_factory("admin")
    r = await _import(admin, dry_run=True, content=build_scanned_pdf(), name="skan.pdf")
    assert r.status_code == 422 and r.json()["error"]["code"] == "pdf_scanned"
    assert (await _import(admin, dry_run=True, content=b"salom", name="matn.txt")).json()["error"]["code"] == "unsupported_format"
    for name in ("buzuq.docx", "buzuq.xls", "buzuq.pdf", "buzuq.xlsx"):
        assert (await _import(admin, dry_run=True, content=b"not a real file", name=name)).json()["error"]["code"] == "bad_file", name
    r = await _import(admin, dry_run=True, content="a;b;c\n1;2;3\n".encode(), name="boshqa.csv")
    assert r.json()["error"]["code"] == "no_sheet"
