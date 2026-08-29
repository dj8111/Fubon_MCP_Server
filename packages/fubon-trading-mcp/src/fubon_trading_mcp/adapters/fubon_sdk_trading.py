import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fubon_common_contracts.models.enums import (
    MarketSession,
    MarketType,
    OrderSide,
    OrderStatus,
    OrderType,
    TimeInForce,
)
from fubon_common_contracts.models.order import ExecutionReport, OrderSubmissionResult
from .base import TradingAdapter


class FubonSdkTradingAdapter(TradingAdapter):
    """富邦正式 SDK 交易配接器 (對接 fubon_neo.sdk.Order 與 sdk.stock)"""

    def __init__(
        self,
        user_id: Optional[str] = None,
        password: Optional[str] = None,
        cert_path: Optional[str] = None,
        cert_password: Optional[str] = None,
    ):
        self.user_id = user_id or os.environ.get("FUBON_USER_ID")
        self.password = password or os.environ.get("FUBON_PASSWORD")
        self.cert_path = cert_path or os.environ.get("FUBON_CERT_PATH")
        self.cert_password = cert_password or os.environ.get("FUBON_CERT_PASSWORD")

        # 支援從 fubon_config.ini 自動讀取設定
        if not (self.user_id and self.password and self.cert_path):
            import configparser
            for ini_file in ["fubon_config.ini", "config.ini", "../fubon_config.ini"]:
                if os.path.exists(ini_file):
                    cfg = configparser.ConfigParser()
                    try:
                        cfg.read(ini_file, encoding="utf-8")
                        if "FUBON" in cfg:
                            self.user_id = self.user_id or cfg["FUBON"].get("user_id")
                            self.password = self.password or cfg["FUBON"].get("password")
                            self.cert_path = self.cert_path or cfg["FUBON"].get("cert_path")
                            self.cert_password = self.cert_password or cfg["FUBON"].get("cert_password")
                            break
                    except Exception:
                        pass

        self.sdk = None
        self.accounts = None
        self._logged_in = False
        self._init_sdk()

    def _init_sdk(self):
        try:
            from fubon_neo.sdk import FubonSDK
            self.sdk = FubonSDK()
            if self.user_id and self.password and self.cert_path:
                if self.cert_password:
                    self.accounts = self.sdk.login(self.user_id, self.password, self.cert_path, self.cert_password)
                else:
                    self.accounts = self.sdk.login(self.user_id, self.password, self.cert_path)
                self._logged_in = True
        except Exception:
            self._logged_in = False

    def _get_active_acc(self, account_ref: Optional[str] = None):
        if not self._logged_in or not self.accounts or not self.accounts.data:
            raise RuntimeError("富邦 SDK 尚未登入或未設定有效交易憑證")
        if account_ref:
            for acc in self.accounts.data:
                if acc.account == account_ref or acc.account.endswith(account_ref[-3:]):
                    return acc
        return self.accounts.data[0]

    def place_order(
        self,
        draft_id: str,
        account_ref: str,
        symbol: str,
        side: OrderSide,
        quantity_shares: int,
        price_type: OrderType,
        limit_price: Optional[str],
        market_session: MarketSession,
        time_in_force: TimeInForce,
        user_def: Optional[str] = "FubonAI",
    ) -> OrderSubmissionResult:
        acc = self._get_active_acc(account_ref)
        from fubon_neo.constant import BSAction, MarketType as FubonMktType, OrderType as FubonOrdType, PriceType as FubonPriceType, TimeInForce as FubonTIF
        from fubon_neo.sdk import Order

        bs_action = BSAction.Buy if side == OrderSide.BUY else BSAction.Sell
        p_type = FubonPriceType.Limit if price_type == OrderType.LIMIT else FubonPriceType.Market
        tif = FubonTIF.ROD if time_in_force == TimeInForce.ROD else (FubonTIF.IOC if time_in_force == TimeInForce.IOC else FubonTIF.FOK)
        mkt_type = FubonMktType.Odd if market_session == MarketSession.ODD_LOT else FubonMktType.Common

        order = Order(
            buy_sell=bs_action,
            symbol=symbol,
            price=str(limit_price) if limit_price else "0",
            quantity=quantity_shares,
            market_type=mkt_type,
            price_type=p_type,
            time_in_force=tif,
            order_type=FubonOrdType.Stock,
            user_def=user_def or "FubonAI",
        )

        res = self.sdk.stock.place_order(acc, order)
        if not getattr(res, "is_success", False):
            raise RuntimeError(f"富邦證券主機下單失敗: {getattr(res, 'message', '下單遭拒')}")

        client_order_id = f"fubon_sdk_{uuid.uuid4().hex[:10]}"
        data = res.data if hasattr(res, "data") else None
        order_no = getattr(data, "order_no", None) if data else None
        seq_no = getattr(data, "seq_no", None) if data else None

        return OrderSubmissionResult(
            client_order_id=client_order_id,
            draft_id=draft_id,
            broker_order_no=order_no,
            seq_no=seq_no,
            status=OrderStatus.SUBMITTED_TO_BROKER,
            submitted_at=datetime.now(timezone.utc).isoformat(),
            raw_response={"message": getattr(res, "message", "成功送出"), "order_no": order_no},
        )

    def cancel_order(self, client_order_id: str) -> Dict[str, Any]:
        acc = self._get_active_acc()
        res = self.sdk.stock.cancel_order(acc, client_order_id)
        if not getattr(res, "is_success", False):
            raise RuntimeError(f"富邦證券主機刪單失敗: {getattr(res, 'message', '刪單遭拒')}")
        return {"client_order_id": client_order_id, "status": OrderStatus.CANCELLED.value}

    def reconcile_order(self, client_order_id: str) -> ExecutionReport:
        acc = self._get_active_acc()
        res = self.sdk.stock.get_order_results(acc)
        raw_list = res.data if hasattr(res, "data") else []
        for item in raw_list:
            if getattr(item, "order_no", "") == client_order_id or getattr(item, "seq_no", "") == client_order_id:
                return ExecutionReport(
                    broker_order_no=getattr(item, "order_no", client_order_id),
                    symbol=getattr(item, "stock_no", ""),
                    side=OrderSide.BUY if str(getattr(item, "buy_sell", "")).lower() in ("buy", "1") else OrderSide.SELL,
                    order_price=str(getattr(item, "price", "0")),
                    order_quantity=int(getattr(item, "quantity", 0)),
                    filled_quantity=int(getattr(item, "filled_quantity", 0)),
                    filled_price=str(getattr(item, "filled_price", None)),
                    status=OrderStatus.FILLED if getattr(item, "status", 0) == 50 else OrderStatus.SUBMITTED_TO_BROKER,
                    order_time=datetime.now(timezone.utc).isoformat(),
                    updated_time=datetime.now(timezone.utc).isoformat(),
                )
        raise ValueError(f"於富邦主機查無委託單 {client_order_id} 之最新狀態")

    def get_open_orders(self, account_ref: Optional[str] = None) -> List[Dict[str, Any]]:
        acc = self._get_active_acc(account_ref)
        res = self.sdk.stock.get_order_results(acc)
        raw_list = res.data if hasattr(res, "data") else []
        return [
            {
                "symbol": getattr(item, "stock_no", ""),
                "side": "BUY" if str(getattr(item, "buy_sell", "")).lower() in ("buy", "1") else "SELL",
                "order_no": getattr(item, "order_no", ""),
                "quantity": getattr(item, "quantity", 0),
            }
            for item in raw_list
        ]
