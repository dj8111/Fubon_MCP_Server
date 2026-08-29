import hashlib
import hmac
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple


class ChallengeManager:
    """富邦 6 碼本機 OTP 挑戰與 Draft Hash 防竄改驗證管理器"""

    def __init__(self, expires_in_seconds: int = 120):
        self.expires_in_seconds = expires_in_seconds
        self._active_challenges: Dict[str, Dict] = {}

    @staticmethod
    def calculate_draft_hash(
        draft_id: str,
        account_ref: str,
        symbol: str,
        side: str,
        quantity: int,
        price: Optional[str],
        session: str,
    ) -> str:
        """計算草稿特徵 Hash (防止參數在 OTP 核准過程中被惡意篡改)"""
        raw = f"{draft_id}:{account_ref}:{symbol}:{side}:{quantity}:{price or 'MARKET'}:{session}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def generate_otp_challenge(self, draft_id: str, draft_hash: str) -> Tuple[str, str, str]:
        """產生 6 碼數字 OTP 並儲存雜湊與過期時間"""
        otp = "".join(secrets.choice(string.digits) for _ in range(6))
        salt = secrets.token_hex(8)
        otp_hash = hashlib.sha256(f"{salt}:{otp}".encode("utf-8")).hexdigest()
        expires_at = (datetime.now(timezone.utc) + timedelta(seconds=self.expires_in_seconds)).isoformat()

        self._active_challenges[draft_id] = {
            "draft_hash": draft_hash,
            "salt": salt,
            "otp_hash": otp_hash,
            "expires_at": expires_at,
            "attempts": 0,
        }

        return otp, salt, expires_at

    def verify_otp(self, draft_id: str, user_draft_hash: str, user_otp: str) -> Tuple[bool, str]:
        """驗證草稿 Hash 與 OTP"""
        challenge = self._active_challenges.get(draft_id)
        if not challenge:
            return False, "OTP 挑戰不存在或已失效，請重新核准草稿"

        challenge["attempts"] += 1
        if challenge["attempts"] > 3:
            del self._active_challenges[draft_id]
            return False, "OTP 錯誤次數超過 3 次，草稿已強制作廢"

        now = datetime.now(timezone.utc)
        exp = datetime.fromisoformat(challenge["expires_at"])
        if now > exp:
            del self._active_challenges[draft_id]
            return False, "OTP 已逾期 (超過 120 秒)，請重新發行挑戰"

        if challenge["draft_hash"] != user_draft_hash:
            return False, "Draft Hash 不相符，交易參數可能遭受竄改，拒絕執行"

        salt = challenge["salt"]
        calc_hash = hashlib.sha256(f"{salt}:{user_otp.strip()}".encode("utf-8")).hexdigest()

        if not hmac.compare_digest(calc_hash, challenge["otp_hash"]):
            return False, f"OTP 驗證碼錯誤 (剩餘嘗試次數: {3 - challenge['attempts']})"

        # 驗證成功，清除已使用之挑戰
        del self._active_challenges[draft_id]
        return True, "OTP 驗證成功"
