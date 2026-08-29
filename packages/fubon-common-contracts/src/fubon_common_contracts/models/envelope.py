import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Generic, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class StandardEnvelope(BaseModel, Generic[T]):
    """富邦 MCP Server 全域標準回傳信封格式"""
    success: bool
    data: Optional[T] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def ok(cls, data: T, metadata: Optional[Dict[str, Any]] = None, correlation_id: Optional[str] = None) -> "StandardEnvelope[T]":
        return cls(
            success=True,
            data=data,
            correlation_id=correlation_id or str(uuid.uuid4()),
            metadata=metadata or {},
        )

    @classmethod
    def fail(cls, error_code: str, error_message: str, correlation_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> "StandardEnvelope[None]":
        return cls(
            success=False,
            error_code=error_code,
            error_message=error_message,
            correlation_id=correlation_id or str(uuid.uuid4()),
            metadata=metadata or {},
        )
