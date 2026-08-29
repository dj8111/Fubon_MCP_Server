import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional
from fubon_common_contracts.models.enums import PositionType
from fubon_common_contracts.models.portfolio import (
    BankBalance,
    MaintenanceRatio,
    PortfolioSummary,
    Position,
    RealizedPnL,
    SettlementInfo,
    SettlementItem,
    UnrealizedPnL,
)
from .base import AccountAdapter


class FubonSdkAccountAdapter(AccountAdapter):
    """富邦正式 SDK 帳務配接器 (對接 fubon_neo.sdk.FubonSDK)"""

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
        except Exception as e:
            self._logged_in = False

    def _get_active_acc(self, account_ref: Optional[str] = None):
        if not self._logged_in or not self.accounts or not self.accounts.data:
            raise RuntimeError("富邦 SDK 尚未登入或未設定有效憑證 (FUBON_USER_ID / FUBON_CERT_PATH)")
        if account_ref:
            for acc in self.accounts.data:
                if acc.account == account_ref or acc.account.endswith(account_ref[-3:]):
                    return acc
        return self.accounts.data[0]

    def get_positions(self, account_ref: Optional[str] = None, symbol: Optional[str] = None) -> List[Position]:
        acc = self._get_active_acc(account_ref)
        res = self.sdk.accounting.inventories(acc)
        if not getattr(res, "is_success", False) and hasattr(res, "is_success"):
            raise RuntimeError(f"查詢庫存失敗: {getattr(res, 'message', '未知錯誤')}")

        positions: List[Position] = []
        raw_list = res.data if hasattr(res, "data") else (res if isinstance(res, list) else [])
        for item in raw_list:
            sym = getattr(item, "stock_no", "") or getattr(item, "symbol", "")
            if symbol and sym != symbol:
                continue
            qty = int(getattr(item, "today_qty", 0)) + int(getattr(item, "yesterday_qty", 0))
            avg_p = str(getattr(item, "cost_price", "0.00"))
            cur_p = str(getattr(item, "last_price", avg_p))
            cost_amt = str(Decimal(avg_p) * Decimal(qty))
            mkt_amt = str(Decimal(cur_p) * Decimal(qty))
            pnl = str(Decimal(mkt_amt) - Decimal(cost_amt))
            pnl_pct = str((Decimal(pnl) / Decimal(cost_amt) * Decimal(100)) if Decimal(cost_amt) > 0 else Decimal("0.00"))

            positions.append(
                Position(
                    symbol=sym,
                    display_name=getattr(item, "stock_name", sym),
                    quantity_shares=qty,
                    available_shares=int(getattr(item, "today_qty", qty)),
                    average_price=avg_p,
                    current_price=cur_p,
                    market_value=f"{Decimal(mkt_amt):.2f}",
                    total_cost=f"{Decimal(cost_amt):.2f}",
                    unrealized_pnl=f"{Decimal(pnl):.2f}",
                    unrealized_pnl_percent=f"{Decimal(pnl_pct):.2f}",
                    weight_percent="0.00",
                    position_type=PositionType.STOCK,
                )
            )

        tot_mkt = sum(Decimal(p.market_value) for p in positions)
        for p in positions:
            if tot_mkt > 0:
                p.weight_percent = f"{(Decimal(p.market_value) / tot_mkt * Decimal(100)):.2f}"

        return positions

    def get_unrealized_pnl(self, account_ref: Optional[str] = None, symbol: Optional[str] = None) -> UnrealizedPnL:
        acc = self._get_active_acc(account_ref)
        res = self.sdk.accounting.unrealized_gains_and_loses(acc)
        raw_list = res.data if hasattr(res, "data") else []
        tot_cost = Decimal("0.00")
        tot_mkt = Decimal("0.00")
        tot_pnl = Decimal("0.00")
        details = []

        for item in raw_list:
            sym = getattr(item, "stock_no", "") or getattr(item, "symbol", "")
            if symbol and sym != symbol:
                continue
            cost = Decimal(str(getattr(item, "cost_amount", 0)))
            mkt = Decimal(str(getattr(item, "market_amount", 0)))
            pnl = Decimal(str(getattr(item, "unrealized_profit", 0)))
            tot_cost += cost
            tot_mkt += mkt
            tot_pnl += pnl
            details.append({
                "symbol": sym,
                "name": getattr(item, "stock_name", sym),
                "quantity": getattr(item, "quantity", 0),
                "cost_price": str(getattr(item, "cost_price", 0)),
                "last_price": str(getattr(item, "last_price", 0)),
                "cost_amount": str(cost),
                "market_amount": str(mkt),
                "unrealized_profit": str(pnl),
                "pnl_rate": str(getattr(item, "pnl_rate", 0)),
            })

        rate = (tot_pnl / tot_cost * Decimal("100")) if tot_cost > 0 else Decimal("0.00")
        return UnrealizedPnL(
            account_ref=acc.account if hasattr(acc, "account") else "FubonAcc",
            total_cost=f"{tot_cost:.2f}",
            total_market_value=f"{tot_mkt:.2f}",
            total_unrealized_profit=f"{tot_pnl:.2f}",
            total_pnl_rate=f"{rate:.2f}",
            details=details,
        )

    def get_realized_pnl(self, account_ref: Optional[str] = None, days: int = 30) -> RealizedPnL:
        acc = self._get_active_acc(account_ref)
        start_date = (datetime.now() - datetime.timedelta(days=days)).strftime("%Y%m%d")
        end_date = datetime.now().strftime("%Y%m%d")
        res = self.sdk.accounting.realized_gains_and_loses(acc, start_date, end_date)
        raw_list = res.data if hasattr(res, "data") else []
        tot_pnl = Decimal("0.00")
        for item in raw_list:
            tot_pnl += Decimal(str(getattr(item, "realized_profit", 0)))

        return RealizedPnL(
            account_ref=acc.account if hasattr(acc, "account") else "FubonAcc",
            start_date=start_date,
            end_date=end_date,
            total_realized_profit=f"{tot_pnl:.2f}",
            total_buy_amount="0.00",
            total_sell_amount="0.00",
            total_trade_fee="0.00",
            total_trade_tax="0.00",
            details=[],
        )

    def get_settlements(self, account_ref: Optional[str] = None) -> SettlementInfo:
        acc = self._get_active_acc(account_ref)
        res_0d = self.sdk.accounting.query_settlement(acc, "0d")
        res_1d = self.sdk.accounting.query_settlement(acc, "1d")
        res_2d = self.sdk.accounting.query_settlement(acc, "2d")

        def _parse(res, label):
            data = res.data if hasattr(res, "data") else {}
            buy = str(getattr(data, "buy_amount", "0.00"))
            sell = str(getattr(data, "sell_amount", "0.00"))
            net = str(getattr(data, "settlement_amount", "0.00"))
            return SettlementItem(
                settle_date=label,
                buy_amount=buy,
                sell_amount=sell,
                net_amount=net,
                description=f"{label} 交割款項",
            )

        t0 = _parse(res_0d, "0d")
        t1 = _parse(res_1d, "1d")
        t2 = _parse(res_2d, "2d")

        payables = [Decimal(item.net_amount) for item in [t0, t1, t2] if Decimal(item.net_amount) < 0]
        total_payable = abs(sum(payables)) if payables else Decimal("0.00")

        return SettlementInfo(
            account_ref=acc.account if hasattr(acc, "account") else "FubonAcc",
            t_zero=t0,
            t_one=t1,
            t_two=t2,
            total_pending_payable=f"{total_payable:.2f}",
            total_pending_receivable="0.00",
        )

    def get_bank_balance(self, account_ref: Optional[str] = None) -> BankBalance:
        acc = self._get_active_acc(account_ref)
        res = self.sdk.accounting.bank_remain(acc)
        bal = "0.00"
        if hasattr(res, "data"):
            bal = str(getattr(res.data, "available_balance", "0.00"))
        return BankBalance(
            account_ref=acc.account if hasattr(acc, "account") else "FubonAcc",
            bank_code="012",
            bank_account=acc.account if hasattr(acc, "account") else "",
            available_balance=bal,
            currency="TWD",
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

    def get_maintenance_ratio(self, account_ref: Optional[str] = None) -> MaintenanceRatio:
        acc = self._get_active_acc(account_ref)
        res = self.sdk.accounting.maintenance(acc)
        ratio = "0.00"
        if hasattr(res, "data"):
            ratio = str(getattr(res.data, "maintenance_ratio", "0.00"))
        return MaintenanceRatio(
            account_ref=acc.account if hasattr(acc, "account") else "FubonAcc",
            self_maintenance_ratio=ratio,
            full_maintenance_ratio=ratio,
            margin_buy_amount="0.00",
            short_sell_amount="0.00",
            collateral_value="0.00",
            is_safe=float(ratio) >= 130.0 if ratio != "0.00" else True,
        )

    def get_portfolio_summary(self, account_ref: Optional[str] = None) -> PortfolioSummary:
        positions = self.get_positions(account_ref=account_ref)
        tot_cost = sum(Decimal(p.total_cost) for p in positions)
        tot_mkt = sum(Decimal(p.market_value) for p in positions)
        tot_pnl = sum(Decimal(p.unrealized_pnl) for p in positions)
        rate = (tot_pnl / tot_cost * Decimal("100")) if tot_cost > 0 else Decimal("0.00")

        bank = self.get_bank_balance(account_ref=account_ref)
        settle = self.get_settlements(account_ref=account_ref)
        maint = self.get_maintenance_ratio(account_ref=account_ref)

        buying_power = Decimal(bank.available_balance) - Decimal(settle.total_pending_payable)

        return PortfolioSummary(
            account_ref=account_ref or (self.accounts.data[0].account if self.accounts and self.accounts.data else "FubonAcc"),
            total_market_value=f"{tot_mkt:.2f}",
            total_cost=f"{tot_cost:.2f}",
            total_unrealized_pnl=f"{tot_pnl:.2f}",
            total_unrealized_pnl_percent=f"{rate:.2f}",
            realized_pnl_today="0.00",
            bank_balance=bank.available_balance,
            buying_power=f"{buying_power:.2f}",
            pending_settlement_net=f"-{settle.total_pending_payable}",
            maintenance_ratio=f"{maint.full_maintenance_ratio}%",
            position_count=len(positions),
            positions=positions,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
