from enum import Enum


class MarketSession(str, Enum):
    REGULAR = "REGULAR"        # 整股盤中 (09:00 - 13:30)
    ODD_LOT = "ODD_LOT"        # 盤中零股 (09:00 - 13:30)
    AFTER_HOURS = "AFTER_HOURS" # 盤後定價 (14:00 - 14:30)
    ODD_LOT_AFTER = "ODD_LOT_AFTER" # 盤後零股


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    LIMIT = "LIMIT"            # 限價
    MARKET = "MARKET"          # 市價


class TimeInForce(str, Enum):
    ROD = "ROD"  # Rest of Day 當日有效
    IOC = "IOC"  # Immediate or Cancel 立即成交否則取消
    FOK = "FOK"  # Fill or Kill 立即全部成交否則取消


class MarketType(str, Enum):
    COMMON = "Common"     # 證券普通單
    FIXING = "Fixing"     # 定價
    ODD = "Odd"           # 零股
    EMERGING = "Emerging" # 興櫃
    FUTURE = "Future"     # 期貨
    OPTION = "Option"     # 選擇權


class OrderStatus(str, Enum):
    DRAFT_PENDING_APPROVAL = "DRAFT_PENDING_APPROVAL" # 待人類 OTP 核准
    CHALLENGE_ISSUED = "CHALLENGE_ISSUED"             # OTP 挑戰已發行
    SUBMITTED_TO_BROKER = "SUBMITTED_TO_BROKER"       # 已送出券商主機
    ACKNOWLEDGED = "ACKNOWLEDGED"                     # 券商收單受理
    PARTIALLY_FILLED = "PARTIALLY_FILLED"             # 部分成交
    FILLED = "FILLED"                                 # 全部成交
    CANCELLED = "CANCELLED"                           # 已刪單
    REJECTED = "REJECTED"                             # 遭拒絕
    EXPIRED = "EXPIRED"                               # 已過期


class TriggerOperator(str, Enum):
    GREATER_THAN_OR_EQUAL = "GREATER_THAN_OR_EQUAL" # >= 突破上漲
    LESS_THAN_OR_EQUAL = "LESS_THAN_OR_EQUAL"       # <= 跌破下跌
    CROSS_ABOVE = "CROSS_ABOVE"                     # 向上穿越
    CROSS_BELOW = "CROSS_BELOW"                     # 向下穿越


class MonitorStatus(str, Enum):
    ACTIVE = "ACTIVE"       # 運行中監測
    PAUSED = "PAUSED"       # 已暫停
    TRIGGERED = "TRIGGERED" # 已觸發
    CANCELLED = "CANCELLED" # 已取消
    EXPIRED = "EXPIRED"     # 已過期


class TriggerEventStatus(str, Enum):
    VALIDATED = "VALIDATED"     # 已驗證防抖
    DRAFT_CREATED = "DRAFT_CREATED" # 已轉入交易草稿
    DISMISSED = "DISMISSED"     # 已忽略
    EXPIRED = "EXPIRED"         # 已失效


class PositionType(str, Enum):
    STOCK = "STOCK"     # 現股
    MARGIN_BUY = "MARGIN_BUY" # 資買
    SHORT_SELL = "SHORT_SELL" # 券賣
    FUTURE = "FUTURE"   # 期貨部位
    OPTION = "OPTION"   # 選擇權部位
