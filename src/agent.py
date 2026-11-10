import copy
from datetime import datetime, timezone

from .domain import slot, validate_request
from .tools import Tools


def validate_decision(value):
    if not isinstance(value, dict) or set(value) != {"action", "arguments", "basis"}:
        raise ValueError("模型动作必须包含且仅包含 action、arguments、basis")
    if value["action"] not in {"read_material", "check_rules", "query_slots", "save_draft", "finish"}:
        raise ValueError("模型选择了不允许的动作")
    expected = {"slot"} if value["action"] == "save_draft" else set()
    if not isinstance(value["arguments"], dict) or set(value["arguments"]) != expected:
        raise ValueError("工具参数不符合契约")
    if not isinstance(value["basis"], str) or len(value["basis"]) > 500:
        raise ValueError("basis 必须是 500 字以内的简要依据")
    if expected:
        slot(value["arguments"]["slot"])


def run(request, world, store, model, max_steps=12):
    validate_request(request)
    if not isinstance(max_steps, int) or not 1 <= max_steps <= 100:
        raise ValueError("max_steps 必须在 1 到 100 之间")
    store.register(request)
    items = []
    trace = []
    for item in request["items"]:
        tools = Tools(world, store, request["request_id"], item)
        termination = "step_limit"
        last_action = None
        attempted = None
        item_trace = []
        for step in range(1, max_steps + 1):
            context = {"item": item, "observations": tools.observations,
                       "last_action": last_action, "remaining_steps": max_steps - step + 1}
            decision = None
            try:
                decision = model.decide(copy.deepcopy(context))
                validate_decision(decision)
            except Exception as exc:
                termination = "model_error"
                error = {"step": step, "error": "model_error", "detail": type(exc).__name__}
                if isinstance(decision, dict):
                    # Record the shape needed for diagnosis, never provider response bodies or credentials.
                    error["response_fields"] = [str(k)[:50] for k in decision]
                    error["returned_action"] = str(decision.get("action", ""))[:64]
                    if isinstance(decision.get("arguments"), dict):
                        error["argument_names"] = [str(k)[:50] for k in decision["arguments"]]
                item_trace.append(error)
                break
            entry = {"step": step, "action": decision["action"], "arguments": decision["arguments"], "basis": decision["basis"]}
            if decision["action"] == "finish":
                entry["observation"] = {"finished": True}
                item_trace.append(entry)
                termination = "finished"
                break
            if decision["action"] == "save_draft":
                attempted = slot(decision["arguments"]["slot"])
            entry["observation"] = tools.execute(decision["action"], decision["arguments"])
            item_trace.append(entry)
            last_action = decision["action"]
        obs = tools.observations
        read = obs.get("read_material", {})
        review = obs.get("check_rules", {})
        saved = obs.get("save_draft", {})
        suggested = saved.get("suggested_slot") if saved.get("ok") else attempted
        confirmation = bool(suggested and item.get("hard_time", True) and suggested != slot(item["requested_slot"])
                            and suggested != (slot(item["approved_slot"]) if item.get("approved_slot") else None))
        if saved.get("ok"):
            confirmation = not saved["confirmed"]
        if termination != "finished":
            status = "incomplete"
        elif "read_material" in obs and (not read.get("ok") or read.get("missing")):
            status = "needs_information"
        elif review.get("risks"):
            status = "blocked"
        elif saved.get("ok"):
            status = "needs_confirmation" if not saved["confirmed"] else "draft_saved"
        elif saved:
            status = "failed"
        elif obs.get("query_slots", {}).get("ok") and not any(x["available"] for x in obs["query_slots"]["slots"]):
            status = "needs_confirmation"
        else:
            status = "incomplete"
        missing = read.get("missing", [])
        pending = (["补充字段：" + ", ".join(missing)] if missing else [])
        if confirmation:
            pending.append("确认替代时段；原始硬性时间要求尚未变更")
        if status == "needs_confirmation" and not suggested:
            pending.append("当前无可用时段，请确认新的时间范围")
        result = {"material_id": item["material_id"], "status": status,
                  "review_status": "blocked" if review.get("risks") else "passed" if review.get("passed") else "needs_information" if missing else "not_checked",
                  "risk_reasons": review.get("risks", []), "missing_fields": missing,
                  "requested_slot": slot(item["requested_slot"]), "suggested_slot": suggested,
                  "pending_confirmations": pending, "save_status": "saved" if saved.get("ok") else "failed" if saved else "not_attempted",
                  "save_error": saved.get("error"), "draft_id": saved.get("draft_id"),
                  "duplicate": saved.get("duplicate", False), "published": False,
                  "draft_updated": saved.get("updated", False),
                  "termination": termination, "steps": len(item_trace)}
        items.append(result)
        for index, entry in enumerate(item_trace):
            entry["next_action"] = item_trace[index + 1].get("action", "model_error") if index + 1 < len(item_trace) else None
        trace.append({"material_id": item["material_id"], "steps": item_trace})
    return {"request_id": request["request_id"], "mode": model.mode, "model": model.name,
            "generated_at": datetime.now(timezone.utc).isoformat(), "max_steps_per_item": max_steps,
            "decision_evidence": "offline_mock_not_model_evidence" if model.mode == "mock" else "live_provider_run",
            "items": items, "trace": trace}
