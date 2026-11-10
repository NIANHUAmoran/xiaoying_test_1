import sqlite3

from .domain import slot


class Tools:
    def __init__(self, world, store, request_id, item):
        self.world, self.store, self.request_id, self.item = world, store, request_id, item
        self.observations = {}
        self.raced = False

    def execute(self, action, arguments):
        try:
            if action == "read_material":
                material = self.world["materials"].get(self.item["material_id"])
                result = {"ok": bool(material), "material": material,
                          "missing": [k for k in self.world["rules"]["required_fields"] if not material or not material.get(k)]}
            elif action == "check_rules":
                read = self.observations.get("read_material", {})
                if not read.get("ok") or read.get("missing"):
                    result = {"ok": False, "error": "material_incomplete"}
                else:
                    material = read["material"]
                    risks = ["blocked_tag:" + tag for tag in material.get("tags", [])
                             if tag in self.world["rules"]["blocked_tags"]]
                    result = {"ok": True, "risks": risks, "passed": not risks}
            elif action == "query_slots":
                values = sorted({slot(x) for x in self.world["available_slots"]} | {slot(self.item["requested_slot"])})
                result = {"ok": True, "slots": [{"slot": x, "available": not self.store.busy(x, self.request_id, self.item["material_id"])} for x in values]}
                if self.world.get("race_slot") and not self.raced:
                    self.store.occupy(self.world["race_slot"])
                    self.raced = True
            elif action == "save_draft":
                if self.observations.get("save_draft", {}).get("ok"):
                    return {**self.observations["save_draft"], "duplicate": True}
                selected = slot(arguments["slot"])
                review = self.observations.get("check_rules", {})
                query = self.observations.get("query_slots", {})
                allowed = {x["slot"] for x in query.get("slots", []) if x["available"]}
                if not review.get("passed") or not query.get("ok") or selected not in allowed:
                    result = {"ok": False, "error": "save_precondition_failed"}
                elif self.world.get("fail_save"):
                    result = {"ok": False, "error": "storage_unavailable"}
                else:
                    approved = self.item.get("approved_slot")
                    confirmed = (selected == slot(self.item["requested_slot"]) or
                                 bool(approved and selected == slot(approved)) or not self.item.get("hard_time", True))
                    result = self.store.save(self.request_id, self.item, selected, confirmed)
            else:
                result = {"ok": False, "error": "unknown_tool"}
        except (ValueError, KeyError, TypeError, sqlite3.Error) as exc:
            result = {"ok": False, "error": "tool_error", "detail": str(exc)}
        self.observations[action] = result
        return result
