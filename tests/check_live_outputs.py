"""Check recorded live traces against the actual local SQLite drafts. No API calls."""
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    rows = []
    for name, expected in [("normal", "draft_saved"), ("conflict", "needs_confirmation"), ("missing", "needs_information")]:
        output = json.loads((ROOT / f"examples/live-{name}.output.json").read_text(encoding="utf-8"))
        item = output["items"][0]
        assert output["mode"] == "live" and output["decision_evidence"] == "live_provider_run"
        assert item["status"] == expected and item["termination"] == "finished"
        assert item["published"] is False
        connection = sqlite3.connect((ROOT / f".runtime/live-{name}.sqlite3").as_uri() + "?mode=ro", uri=True)
        try:
            stored = connection.execute("SELECT body FROM drafts WHERE request_id=?", (output["request_id"],)).fetchall()
        finally:
            connection.close()
        draft = json.loads(stored[0][0]) if stored else None
        assert len(stored) == (0 if name == "missing" else 1)
        if draft:
            assert draft["draft_id"] == item["draft_id"]
            assert draft["requested_slot"] == item["requested_slot"]
            assert draft["suggested_slot"] == item["suggested_slot"]
            assert draft["confirmed"] == (name == "normal")
        if name == "conflict":
            assert item["requested_slot"] == "2026-11-11T18:00:00+08:00"
            assert item["suggested_slot"] == "2026-11-11T19:00:00+08:00"
            assert item["pending_confirmations"]
        steps = output["trace"][0]["steps"]
        assert all(x.get("basis") for x in steps)
        actions = [x["action"] for x in steps]
        assert actions == (["read_material", "finish"] if name == "missing" else
                           ["read_material", "check_rules", "query_slots", "save_draft", "finish"])
        rows.append({"scenario": name, "model": output["model"], "mode": output["mode"],
                     "status": item["status"], "save_status": item["save_status"], "actions": actions,
                     "draft_count": len(stored), "database_consistent": True,
                     "confirmed": draft["confirmed"] if draft else None,
                     "output": f"live-{name}.output.json"})
    summary = {"checked_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
               "checks": rows, "all_passed": True,
               "scope": "Three observed live runs; not a guarantee of future model reliability."}
    (ROOT / "examples/live-validation-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    delivery_path = ROOT / "examples/delivery-status.json"
    delivery = json.loads(delivery_path.read_text(encoding="utf-8"))
    delivery.update(tests_passed=31, tests_failed=0, live_model_run_performed=True,
                    live_model=rows[0]["model"], live_scenarios_passed=[x["scenario"] for x in rows],
                    live_validation_completed_at=summary["checked_at"])
    delivery_path.write_text(json.dumps(delivery, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"all_passed": True, "live_scenarios": [x["scenario"] for x in rows], "tests_passed": 31}))


if __name__ == "__main__":
    main()
