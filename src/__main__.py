import argparse
import json
import sqlite3
import sys
from pathlib import Path

from .agent import run
from .config import DEFAULT_ENV, load_env
from .models import HTTPModel, MockModel
from .store import Store


def main():
    parser = argparse.ArgumentParser(description="素材审核与排期草稿 Agent（不执行发布）")
    parser.add_argument("--input", required=True)
    parser.add_argument("--data", default="data/world.json")
    parser.add_argument("--db", default=".runtime/drafts.sqlite3")
    parser.add_argument("--output")
    parser.add_argument("--mock", action="store_true", help="显式启用离线固定策略；不证明真实模型决策效果")
    parser.add_argument("--max-steps", type=int, default=12)
    parser.add_argument("--env-file", default=str(DEFAULT_ENV), help="模型配置文件，默认项目根目录 .env；环境变量优先")
    args = parser.parse_args()
    store = None
    try:
        request = json.loads(Path(args.input).read_text(encoding="utf-8-sig"))
        world = json.loads(Path(args.data).read_text(encoding="utf-8-sig"))
        if not args.mock:
            load_env(args.env_file)
        model = MockModel() if args.mock else HTTPModel()
        Path(args.db).parent.mkdir(parents=True, exist_ok=True)
        store = Store(args.db, world.get("occupied_slots", []))
        result = run(request, world, store, model, args.max_steps)
        text = json.dumps(result, ensure_ascii=False, indent=2)
        if args.output:
            Path(args.output).parent.mkdir(parents=True, exist_ok=True)
            Path(args.output).write_text(text + "\n", encoding="utf-8")
        print(text)
        return 1 if any(x["status"] in {"failed", "incomplete"} for x in result["items"]) else 0
    except (OSError, ValueError, KeyError, TypeError, sqlite3.Error) as exc:
        print(json.dumps({"error": type(exc).__name__, "detail": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    finally:
        if store:
            store.close()


if __name__ == "__main__":
    raise SystemExit(main())
