import argparse
import json
import sys
from .server import portfolio_service, run, snapshot_service


def main():
    parser = argparse.ArgumentParser(description="富邦證券帳務管理 CLI")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("serve", help="以 STDIO 模式啟動 MCP 伺服器")
    subparsers.add_parser("positions", help="列印當前庫存部位")
    subparsers.add_parser("summary", help="列印資產總覽與實質購買力")
    subparsers.add_parser("settlement", help="查詢交割款明細")

    snap_parser = subparsers.add_parser("snapshot", help="快照管理")
    snap_sub = snap_parser.add_subparsers(dest="snap_cmd")

    create_p = snap_sub.add_parser("create", help="建立快照")
    create_p.add_argument("--note", type=str, default=None, help="快照備註")

    snap_sub.add_parser("list", help="列出歷史快照")

    args = parser.parse_args()

    if args.command == "serve" or args.command is None:
        run()
    elif args.command == "positions":
        positions = portfolio_service.get_positions()
        print(json.dumps([p.model_dump() for p in positions], indent=2, ensure_ascii=False))
    elif args.command == "summary":
        summary = portfolio_service.get_portfolio_summary()
        print(json.dumps(summary.model_dump(), indent=2, ensure_ascii=False))
    elif args.command == "settlement":
        settle = portfolio_service.get_settlements()
        print(json.dumps(settle.model_dump(), indent=2, ensure_ascii=False))
    elif args.command == "snapshot":
        if args.snap_cmd == "create":
            snap = snapshot_service.save_snapshot(note=args.note)
            print(json.dumps(snap.model_dump(), indent=2, ensure_ascii=False))
        elif args.snap_cmd == "list":
            snaps = snapshot_service.list_snapshots()
            print(json.dumps(snaps, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
