from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple
from fubon_common_contracts.models.enums import MarketSession, OrderSide, OrderType
from fubon_common_contracts.models.order import RiskCheckResult


class RiskEngine:
    """富邦證券硬性風控檢核引擎 (不可由 AI 竄改或繞過)"""

    def __init__(
        self,
        single_order_limit: Decimal = Decimal("500000.00"),
        daily_cumulative_limit: Decimal = Decimal("2000000.00"),
        max_daily_orders: int = 20,
    ):
        self.single_order_limit = single_order_limit
        self.daily_cumulative_limit = daily_cumulative_limit
        self.max_daily_orders = max_daily_orders

        # 當日累計計數器
        self._daily_order_count = 0
        self._daily_cumulative_amount = Decimal("0.00")

    @staticmethod
    def get_valid_tick_size(price: Decimal) -> Decimal:
        """依臺股法規取得對應價格區間之最小跳動單位"""
        if price < Decimal("10"):
            return Decimal("0.01")
        elif price < Decimal("50"):
            return Decimal("0.05")
        elif price < Decimal("100"):
            return Decimal("0.10")
        elif price < Decimal("500"):
            return Decimal("0.50")
        elif price < Decimal("1000"):
            return Decimal("1.00")
        else:
            return Decimal("5.00")

    @classmethod
    def validate_tick_size(cls, price_str: str) -> Tuple[bool, str]:
        """驗證價格是否符合臺股跳動單位"""
        try:
            p = Decimal(price_str)
        except Exception:
            return False, f"價格格式錯誤: {price_str}"

        tick = cls.get_valid_tick_size(p)
        remainder = (p / tick) % Decimal("1")
        if remainder != Decimal("0"):
            return False, f"價格 {price_str} 不符合臺股該價位之跳動單位 {tick} 元規範"
        return True, ""

    def validate_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity_shares: int,
        price_type: OrderType,
        limit_price: Optional[str],
        market_session: MarketSession,
        reference_price: Decimal,
        available_shares: int = 0,
        open_opposite_orders: Optional[List[Dict[str, Any]]] = None,
    ) -> List[RiskCheckResult]:
        """執行全套硬性風控檢核"""
        results: List[RiskCheckResult] = []

        # 1. 股數與盤別檢核
        if market_session == MarketSession.REGULAR:
            if quantity_shares <= 0 or quantity_shares % 1000 != 0:
                results.append(RiskCheckResult(
                    check_code="REGULAR_LOT_VALIDATION",
                    result="REJECT",
                    message=f"整股交易委託股數必須為 1,000 股之整數倍 (目前為 {quantity_shares} 股)",
                ))
            else:
                results.append(RiskCheckResult(check_code="REGULAR_LOT_VALIDATION", result="PASS", message="整股股數檢核通過"))
        elif market_session == MarketSession.ODD_LOT:
            if quantity_shares <= 0 or quantity_shares >= 1000:
                results.append(RiskCheckResult(
                    check_code="ODD_LOT_VALIDATION",
                    result="REJECT",
                    message=f"零股交易委託股數必須介於 1 至 999 股 (目前為 {quantity_shares} 股)",
                ))
            else:
                results.append(RiskCheckResult(check_code="ODD_LOT_VALIDATION", result="PASS", message="零股股數檢核通過"))

        # 2. 限價與跳動單位檢核
        if price_type == OrderType.LIMIT:
            if not limit_price:
                results.append(RiskCheckResult(
                    check_code="LIMIT_PRICE_REQUIRED",
                    result="REJECT",
                    message="限價單必須明確指定 limit_price",
                ))
            else:
                ok, err_msg = self.validate_tick_size(limit_price)
                if not ok:
                    results.append(RiskCheckResult(check_code="TICK_SIZE_VALIDATION", result="REJECT", message=err_msg))
                else:
                    results.append(RiskCheckResult(check_code="TICK_SIZE_VALIDATION", result="PASS", message="跳動單位符合規範"))

                # 3. 漲跌停 10% 價格區間檢核
                p = Decimal(limit_price)
                limit_up = (reference_price * Decimal("1.10")).quantize(Decimal("0.01"))
                limit_down = (reference_price * Decimal("0.90")).quantize(Decimal("0.01"))
                if p > limit_up or p < limit_down:
                    results.append(RiskCheckResult(
                        check_code="PRICE_COLLAR_VALIDATION",
                        result="REJECT",
                        message=f"委託價 {limit_price} 超出漲跌停 10% 範圍 [{limit_down}, {limit_up}] (昨收: {reference_price})",
                    ))
                else:
                    results.append(RiskCheckResult(check_code="PRICE_COLLAR_VALIDATION", result="PASS", message="價格位於漲跌停限制內"))
        else:
            results.append(RiskCheckResult(check_code="MARKET_PRICE_CHECK", result="PASS", message="市價單不檢核限價跳動"))

        # 4. 委託總金額與限額檢核
        price_for_est = Decimal(limit_price) if (price_type == OrderType.LIMIT and limit_price) else reference_price
        est_amount = price_for_est * Decimal(quantity_shares)

        if est_amount > self.single_order_limit:
            results.append(RiskCheckResult(
                check_code="SINGLE_ORDER_LIMIT",
                result="REJECT",
                message=f"單筆委託預估金額 NT${est_amount:,.2f} 超過單筆限額 NT${self.single_order_limit:,.2f}",
            ))
        else:
            results.append(RiskCheckResult(check_code="SINGLE_ORDER_LIMIT", result="PASS", message="單筆限額符合規範"))

        if (self._daily_cumulative_amount + est_amount) > self.daily_cumulative_limit:
            results.append(RiskCheckResult(
                check_code="DAILY_TURNOVER_LIMIT",
                result="REJECT",
                message=f"當日累計委託金額 NT${self._daily_cumulative_amount + est_amount:,.2f} 超過每日上限 NT${self.daily_cumulative_limit:,.2f}",
            ))
        else:
            results.append(RiskCheckResult(check_code="DAILY_TURNOVER_LIMIT", result="PASS", message="每日總委託限額符合規範"))

        # 5. 賣出庫存充足性檢核
        if side == OrderSide.SELL:
            if quantity_shares > available_shares:
                results.append(RiskCheckResult(
                    check_code="SHORT_SELL_PREVENTION",
                    result="REJECT",
                    message=f"現股賣出股數 {quantity_shares} 超過可用庫存股數 {available_shares} (禁止無券賣空)",
                ))
            else:
                results.append(RiskCheckResult(check_code="SHORT_SELL_PREVENTION", result="PASS", message="賣出部位充足"))

        # 6. 反向自成交 / 洗售防護
        if open_opposite_orders:
            opposite_side = OrderSide.SELL if side == OrderSide.BUY else OrderSide.BUY
            matching_opposites = [
                o for o in open_opposite_orders
                if o.get("symbol") == symbol and o.get("side") == opposite_side.value
            ]
            if matching_opposites:
                results.append(RiskCheckResult(
                    check_code="SELF_TRADE_PREVENTION",
                    result="REJECT",
                    message=f"偵測到標的 {symbol} 尚有反向未成交委託單，為防範自成交違規拒絕送單",
                ))
            else:
                results.append(RiskCheckResult(check_code="SELF_TRADE_PREVENTION", result="PASS", message="無反向自成交疑慮"))

        return results

    def record_approved_order(self, amount: Decimal):
        """記錄已核准送出之訂單金額與筆數"""
        self._daily_order_count += 1
        self._daily_cumulative_amount += amount

    def get_risk_status(self) -> Dict[str, Any]:
        return {
            "daily_order_count": self._daily_order_count,
            "max_daily_orders": self.max_daily_orders,
            "daily_cumulative_amount": f"{self._daily_cumulative_amount:.2f}",
            "daily_cumulative_limit": f"{self.daily_cumulative_limit:.2f}",
            "single_order_limit": f"{self.single_order_limit:.2f}",
            "remaining_daily_limit": f"{max(Decimal('0'), self.daily_cumulative_limit - self._daily_cumulative_amount):.2f}",
        }
