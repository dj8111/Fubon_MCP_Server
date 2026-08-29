import argparse
import json
import sys
from .server import run, trading_service


def main():
    parser = argparse.ArgumentParser(description="富邦證券交易與風控 CLI")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("serve", help="以 STDIO 模式啟動 MCP 伺服器")
    subparsers.add_parser("status", help="查詢交易系統狀態與風控累計")
    subparsers.add_parser("power", help="查詢購買力與交割款")

    kill_p = subparsers.add_parser("kill", help="啟動交易熔斷")
    kill_p.add_argument("--reason", type=str, default="CLI 手動觸發熔斷", help="熔斷原因")

    args = parser.parse_args()

    if args.command == "serve" or args.command is None:
        run()
    elif args.command == "status":
        stat = trading_service.get_status()
        print(json.dumps(stat, indent=2, ensure_ascii=False))
    elif args.command == "power":
        power = trading_service.get_buying_power()
        print(json.dumps(power, indent=2, ensure_ascii=False))
    elif args.command == "kill":
        res = trading_service.activate_kill_switch(reason=args.reason)
        print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
