"""Rebuild offline evidence in a temporary database, without touching user drafts."""
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

from src.agent import run
from src.models import MockModel
from src.store import Store


def write(name, value):
    (ROOT / "examples" / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    world = json.loads((ROOT / "data/world.json").read_text(encoding="utf-8"))
    paired_inputs = {"duplicate": "normal", "changed-occupancy": "conflict", "race": "normal",
                     "live-normal": "normal", "live-conflict": "conflict", "live-missing": "missing",
                     "live-conflict-before-fix": "conflict"}
    for target, source in paired_inputs.items():
        write(f"{target}.input.json", json.loads((ROOT / f"examples/{source}.input.json").read_text(encoding="utf-8")))
    summary = []
    with tempfile.TemporaryDirectory() as temp:
        temp = Path(temp)
        for scenario in ["normal", "conflict", "missing", "risk", "save-failure"]:
            request = json.loads((ROOT / f"examples/{scenario}.input.json").read_text(encoding="utf-8"))
            fixture = copy.deepcopy(world)
            if scenario == "save-failure":
                fixture["fail_save"] = True
                (ROOT / "data/save-failure.world.json").write_text(json.dumps(fixture, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            data_path = temp / f"{scenario}.world.json"
            data_path.write_text(json.dumps(fixture), encoding="utf-8")
            process = subprocess.run([sys.executable, "-m", "src", "--mock", "--input", f"examples/{scenario}.input.json",
                                      "--data", str(data_path), "--db", str(temp / f"{scenario}.sqlite3"),
                                      "--output", f"examples/{scenario}.output.json"], cwd=ROOT, capture_output=True)
            expected_exit = 1 if scenario == "save-failure" else 0
            if process.returncode != expected_exit:
                raise RuntimeError(f"{scenario} exited {process.returncode}: {process.stderr!r}")
            output = json.loads((ROOT / f"examples/{scenario}.output.json").read_text(encoding="utf-8"))
            summary.append({"scenario": scenario, "exit_code": process.returncode, "status": output["items"][0]["status"], "mode": output["mode"]})
            if scenario == "conflict":
                confirmation = subprocess.run([sys.executable, "-m", "src", "--mock", "--input", "examples/confirm.input.json",
                                               "--db", str(temp / "conflict.sqlite3"), "--output", "examples/confirm.output.json"],
                                              cwd=ROOT, capture_output=True)
                assert confirmation.returncode == 0
                confirmed = json.loads((ROOT / "examples/confirm.output.json").read_text(encoding="utf-8"))
                assert confirmed["items"][0]["status"] == "draft_saved"
                assert confirmed["items"][0]["draft_id"] == output["items"][0]["draft_id"]
            if scenario == "normal":
                duplicate = subprocess.run([sys.executable, "-m", "src", "--mock", "--input", "examples/normal.input.json",
                                            "--db", str(temp / "normal.sqlite3"), "--output", "examples/duplicate.output.json"],
                                           cwd=ROOT, capture_output=True)
                if duplicate.returncode:
                    raise RuntimeError("duplicate execution failed")
                repeated = json.loads((ROOT / "examples/duplicate.output.json").read_text(encoding="utf-8"))
                assert repeated["items"][0]["duplicate"]
                assert repeated["items"][0]["draft_id"] == output["items"][0]["draft_id"]
                store = Store(str(temp / "normal.sqlite3"))
                try:
                    count = store.db.execute("SELECT count(*) FROM drafts").fetchone()[0]
                    assert count == 1
                finally:
                    store.close()
                summary.append({"scenario": "duplicate", "exit_code": 0, "draft_count": count, "mode": "mock"})
        request = json.loads((ROOT / "examples/conflict.input.json").read_text(encoding="utf-8"))
        store = Store(str(temp / "changed.sqlite3"), world["occupied_slots"])
        try:
            before = run(request, world, store, MockModel())
            store.occupy("2026-11-11T19:00:00+08:00")
            after = run(request, world, store, MockModel())
            write("changed-occupancy.output.json", {"before": before, "after": after,
                  "draft_count": store.db.execute("SELECT count(*) FROM drafts").fetchone()[0]})
        finally:
            store.close()
        fixture = copy.deepcopy(world)
        fixture["race_slot"] = "2026-11-11T19:00:00+08:00"
        request = json.loads((ROOT / "examples/normal.input.json").read_text(encoding="utf-8"))
        store = Store(str(temp / "race.sqlite3"), world["occupied_slots"])
        try:
            write("race.output.json", run(request, fixture, store, MockModel()))
        finally:
            store.close()
    # Exercise actual CLI behavior when live credentials are absent; never silently fall back to mock.
    env = {k: v for k, v in os.environ.items() if k not in {"LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY"}}
    with tempfile.TemporaryDirectory() as empty:
        process = subprocess.run([sys.executable, "-m", "src", "--input", "examples/normal.input.json",
                                  "--env-file", str(Path(empty) / "absent.env")], cwd=ROOT, env=env, capture_output=True)
    assert process.returncode == 2
    write("live-config-check.json", {"exit_code": process.returncode, "live_run_performed": False,
          "reason": "No LLM configuration supplied; live decision quality is unverified."})
    write("run-summary.json", summary)
    # Extract the original execution records verbatim; never synthesize model decisions.
    for output_path in sorted((ROOT / "examples").glob("*.output.json")):
        output = json.loads(output_path.read_text(encoding="utf-8"))
        def trace_record(record):
            return {key: record[key] for key in ["request_id", "mode", "model", "generated_at", "trace"]}
        extracted = ({"runs": [{"name": name, **trace_record(output[name])} for name in ["before", "after"]]}
                     if "before" in output and "after" in output else trace_record(output))
        write(output_path.name.replace(".output.json", ".trace.json"),
              {"source_output": output_path.name, **extracted})
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    with (ROOT / "examples/test-results.txt").open("w", encoding="utf-8") as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    print(f"Offline examples rebuilt; tests: {result.testsRun}, failures: {len(result.failures)}, errors: {len(result.errors)}")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
