"""Lightweight MOSIP client stub.

This stub avoids external network calls and returns predictable
structures so the MOSIP routes can operate without real MOSIP
credentials. Replace implementations with real MOSIP API calls
when available.
"""
from __future__ import annotations

import os
import uuid
from typing import Any, Dict


class MOSIPClient:
    def __init__(self, base_url: str, auth_token: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.auth_token = auth_token or ""

    def create_pre_registration(self, data: Dict[str, Any]) -> Dict[str, Any]:
        pre_reg_id = f"PRE{uuid.uuid4().hex[:10].upper()}"
        return {
            "status": "success",
            "response": {"preRegistrationId": pre_reg_id},
            "echo": data,
            "base_url": self.base_url,
        }

    def upload_document(self, pre_reg_id: str, file_path: str) -> Dict[str, Any]:
        return {
            "status": "uploaded",
            "preRegistrationId": pre_reg_id,
            "file": os.path.basename(file_path),
        }

    def get_application_status(self, pre_reg_id: str) -> str:
        # Placeholder status; replace with real MOSIP lookup
        return "pending"
