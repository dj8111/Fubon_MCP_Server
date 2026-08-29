import argparse
import json
import sys
from .server import research_service, run


def main():
    parser = argparse.ArgumentParser(description="富邦證券公開研究與風險分析 CLI")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("serve", help="以 STDIO 模式啟動 MCP 伺服器")

    rep_p = subparsers.add_parser("report", help="產生個股綜合研究報告")
    rep_p.add_argument("symbol", type=str, help="股票代碼 (例: 2881)")

    ann_p = subparsers.add_parser("announcements", help="查詢重大訊息公告")
    ann_p.add_argument("symbol", type=str, help="股票代碼")

    args = parser.parse_args()

    if args.command == "serve" or args.command is None:
        run()
    elif args.command == "report":
        rep = research_service.generate_research_report(args.symbol)
        print(json.dumps(rep, indent=2, ensure_ascii=False))
    elif args.command == "announcements":
        anns = research_service.search_announcements(args.symbol)
        print(json.dumps([a.model_dump() for a in anns], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
