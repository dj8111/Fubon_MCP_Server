import argparse
import json
import sys
from fubon_common_contracts.models.enums import TriggerOperator
from .server import market_service, run


def main():
    parser = argparse.ArgumentParser(description="富邦證券行情與價格監測 CLI")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("serve", help="以 STDIO 模式啟動 MCP 伺服器")

    quote_p = subparsers.add_parser("quote", help="查詢即時報價")
    quote_p.add_argument("symbol", type=str, help="股票代碼 (例: 2881)")

    book_p = subparsers.add_parser("book", help="查詢五檔委託簿")
    book_p.add_argument("symbol", type=str, help="股票代碼 (例: 2881)")

    mon_p = subparsers.add_parser("monitor", help="條件監測管理")
    mon_sub = mon_p.add_subparsers(dest="mon_cmd")

    create_p = mon_sub.add_parser("create", help="建立監測條件")
    create_p.add_argument("--symbol", type=str, required=True, help="股票代碼")
    create_p.add_argument("--op", type=str, default="GREATER_THAN_OR_EQUAL", help="觸發運算子")
    create_p.add_argument("--price", type=str, required=True, help="觸發價格")

    mon_sub.add_parser("list", help="列出運行中監測條件")

    args = parser.parse_args()

    if args.command == "serve" or args.command is None:
        run()
    elif args.command == "quote":
        quote = market_service.get_stock_quote(args.symbol)
        print(json.dumps(quote.model_dump(), indent=2, ensure_ascii=False))
    elif args.command == "book":
        book = market_service.get_order_book(args.symbol)
        print(json.dumps(book, indent=2, ensure_ascii=False))
    elif args.command == "monitor":
        if args.mon_cmd == "create":
            mon = market_service.create_price_monitor(
                symbol=args.symbol,
                operator=TriggerOperator(args.op),
                trigger_price=args.price,
            )
            print(json.dumps(mon, indent=2, ensure_ascii=False))
        elif args.mon_cmd == "list":
            mons = market_service.list_active_monitors()
            print(json.dumps(mons, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
