from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .parsers import RuleBasedMessageParser
from .schemas import RULES_VERSION, SCHEMA_VERSION, InputEnvelope, now_iso
from .text_extractor import TextExtractor


class OMSDataParser:
    """OCR/text extraction plus structured JSON parsing."""

    def __init__(self, extractor: TextExtractor | None = None, parser: RuleBasedMessageParser | None = None) -> None:
        self.extractor = extractor or TextExtractor()
        self.parser = parser or RuleBasedMessageParser()

    def parse(self, envelope: InputEnvelope) -> dict[str, Any]:
        extraction = self.extractor.extract(envelope)
        if extraction.status != "ok":
            return self._empty_result(envelope, extraction)

        parsed = self.parser.parse(extraction.text)
        return {
            "schema_version": SCHEMA_VERSION,
            "input": envelope.to_dict(),
            "text_extraction": extraction.to_dict(),
            "parser": {
                "name": "OMS_DataParser",
                "rules_version": RULES_VERSION,
                "mode": "rule_based_v1",
            },
            **parsed,
            "audit": {
                "created_at": now_iso(),
                "requires_human_confirmation": parsed["status"] != "parsed",
            },
        }

    def _empty_result(self, envelope: InputEnvelope, extraction: Any) -> dict[str, Any]:
        status = "ocr_unavailable" if extraction.status == "ocr_unavailable" else "unparsed"
        return {
            "schema_version": SCHEMA_VERSION,
            "input": envelope.to_dict(),
            "text_extraction": asdict(extraction),
            "parser": {
                "name": "OMS_DataParser",
                "rules_version": RULES_VERSION,
                "mode": "rule_based_v1",
            },
            "status": status,
            "document_type": "unknown",
            "classification": {"top1": {"type": "unknown", "confidence": 0.0, "matched_keywords": []}, "alternatives": []},
            "entities": {"amounts": [], "dates": [], "people": [], "contract_numbers": [], "platforms": [], "departments": []},
            "structured_data": {},
            "validation": {"missing_required": [], "warnings": [extraction.error] if extraction.error else []},
            "audit": {"created_at": now_iso(), "requires_human_confirmation": True},
        }

