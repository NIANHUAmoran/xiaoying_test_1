"""Validate the required submission structure and recorded evidence; no model calls."""
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOT_ENTRIES = {"README.md", "requirements.txt", ".env.example", ".gitignore", "src", "tests", "examples", "data", "docs"}
DOCS = {"01-requirements.md", "02-solution.md", "03-evaluation.md", "04-ai-usage.md", "05-retrospective.md"}
CASES = ["normal", "missing", "risk", "conflict", "duplicate", "save-failure", "confirm",
         "changed-occupancy", "race", "live-normal", "live-conflict", "live-missing", "live-conflict-before-fix"]


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    actual_root = {p.name for p in ROOT.iterdir()}
    if actual_root != ROOT_ENTRIES:
        raise ValueError(f"项目根目录不符合交付结构：缺少 {sorted(ROOT_ENTRIES - actual_root)}；多余 {sorted(actual_root - ROOT_ENTRIES)}")
    if {p.name for p in (ROOT / "docs").iterdir()} != DOCS:
        raise ValueError("docs 必须包含且仅包含五份指定交付文档")
    if list((ROOT / "examples").glob("*.py")):
        raise ValueError("验证脚本应位于 tests，examples 只存放验证材料及索引")
    if not (ROOT / "src/__main__.py").is_file() or not list((ROOT / "tests").glob("test_*.py")):
        raise ValueError("缺少可执行入口或测试")
    for name in CASES:
        paths = {kind: ROOT / f"examples/{name}.{kind}.json" for kind in ["input", "output", "trace"]}
        values = {kind: read(path) for kind, path in paths.items()}
        request, output, trace = (values[k] for k in ["input", "output", "trace"])
        if trace["source_output"] != paths["output"].name:
            raise ValueError(f"{name} 的 Trace 引用错误")
        runs = [(output[key], trace["runs"][index]) for index, key in enumerate(["before", "after"])] if name == "changed-occupancy" else [(output, trace)]
        for run, extracted in runs:
            if run["request_id"] != request["request_id"] or extracted["trace"] != run["trace"]:
                raise ValueError(f"{name} 的输入、输出、Trace 不一致")
            expected_mode = "live" if name.startswith("live-") else "mock"
            if run["mode"] != expected_mode or extracted["mode"] != expected_mode:
                raise ValueError(f"{name} 未正确标明真实模型或 Mock")
    for doc in list(ROOT.glob("*.md")) + list((ROOT / "docs").glob("*.md")) + list((ROOT / "examples").glob("*.md")):
        for target in re.findall(r"\]\(([^)]+)\)", doc.read_text(encoding="utf-8")):
            resolved = doc.parent / target.split("#")[0]
            if resolved.resolve() == (ROOT / "examples/submission-check.json").resolve():
                continue  # This run creates the report after all checks pass.
            if not target.startswith(("http:", "https:", "#")) and not resolved.exists():
                raise ValueError(f"文档链接无效：{doc.relative_to(ROOT)} → {target}")
    report = (ROOT / "examples/test-results.txt").read_text(encoding="utf-8")
    if not re.search(r"Ran 31 tests", report) or not report.rstrip().endswith("OK"):
        raise ValueError("缺少 31 项测试全部通过的实际记录")
    result = {"checked_at": datetime.now(timezone(timedelta(hours=8))).isoformat(), "all_passed": True,
              "root_entries": sorted(actual_root), "required_documents": sorted(DOCS),
              "six_required_cases": CASES[:6], "evidence_groups_checked": len(CASES),
              "trace_matches_actual_output": True, "document_links_valid": True,
              "unit_tests_passed": 31, "live_paths": ["live-normal", "live-conflict", "live-missing"]}
    (ROOT / "examples/submission-check.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"submission_check": "passed", "evidence_groups": len(CASES), "unit_tests": 31}))


if __name__ == "__main__":
    main()
