import hashlib
import json
from datetime import datetime, timedelta, timezone


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def slot(value):
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        raise ValueError("时间必须包含日期和时区偏移")
    return dt.astimezone(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def validate_request(request):
    if not isinstance(request, dict) or not isinstance(request.get("request_id"), str) or not request["request_id"].strip():
        raise ValueError("request_id 必须是非空字符串")
    if not isinstance(request.get("items"), list) or not request["items"]:
        raise ValueError("items 必须是非空数组")
    seen = set()
    for item in request["items"]:
        if not isinstance(item, dict):
            raise ValueError("每个 item 必须是对象")
        mid = item.get("material_id")
        if not isinstance(mid, str) or not mid or mid in seen:
            raise ValueError("material_id 必须非空且在请求中唯一")
        seen.add(mid)
        if not isinstance(item.get("requested_slot"), str):
            raise ValueError("requested_slot 必须为带时区的时间字符串")
        slot(item["requested_slot"])
        if "hard_time" in item and not isinstance(item["hard_time"], bool):
            raise ValueError("hard_time 必须为布尔值")
        if "approved_slot" in item:
            if not isinstance(item["approved_slot"], str) or not item["approved_slot"]:
                raise ValueError("approved_slot 必须为非空时间字符串")
            slot(item["approved_slot"])
