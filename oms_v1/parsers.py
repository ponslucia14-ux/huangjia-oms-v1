from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


AMOUNT_RE = re.compile(r"(?:(?:￥|¥|人民币)\s*)?(\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?\s*(元|块|万)")
DATE_RE = re.compile(r"(\d{4}[年/-]\d{1,2}[月/-]\d{1,2}日?|\d{1,2}[月/-]\d{1,2}日?|\d{1,2}\.\d{1,2})")
CONTRACT_RE = re.compile(r"(?:合同(?:编号|号)?|编号)[:：\s]*([A-Za-z0-9\-_/]{4,})")
NAME_RE = re.compile(r"(?:客户姓名|宝妈姓名|产妇姓名|宝妈|客户|妈妈|姓名|用户|产妇)[:：\s]*([\u4e00-\u9fa5]{2,4}?)(?=，|,|。|\s|$|尾款|定金|全款|签约|合同|报销)")


@dataclass(frozen=True)
class Classification:
    document_type: str
    confidence: float
    alternatives: list[dict[str, Any]]
    matched_keywords: list[str]


TYPE_KEYWORDS = {
    "contract": ["合同", "签约", "预定", "套餐", "房型", "预产期", "入住", "照护合约"],
    "payment": ["收款", "到账", "转账", "定金", "尾款", "全款", "押金", "实入账", "付款"],
    "reimbursement": ["报销", "采购", "发票", "单据", "费用", "垫付", "付款申请", "维修"],
    "note": ["备注", "说明", "提醒", "交接", "记录"],
}


class RuleBasedMessageParser:
    def parse(self, text: str) -> dict[str, Any]:
        normalized = normalize_text(text)
        classification = classify(normalized)
        entities = extract_entities(normalized)
        structured = build_structured_data(classification.document_type, normalized, entities)
        missing = missing_required_fields(classification.document_type, structured)
        status = "parsed" if not missing else "needs_review"

        return {
            "status": status,
            "document_type": classification.document_type,
            "classification": {
                "top1": {
                    "type": classification.document_type,
                    "confidence": classification.confidence,
                    "matched_keywords": classification.matched_keywords,
                },
                "alternatives": classification.alternatives,
            },
            "entities": entities,
            "structured_data": structured,
            "validation": {
                "missing_required": missing,
                "warnings": build_warnings(classification.document_type, normalized, entities),
            },
        }


def normalize_text(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text.replace("\r\n", "\n").replace("\r", "\n")).strip()


def classify(text: str) -> Classification:
    scores: dict[str, int] = {}
    matched: dict[str, list[str]] = {}
    for doc_type, keywords in TYPE_KEYWORDS.items():
        hits = [kw for kw in keywords if kw in text]
        scores[doc_type] = len(hits)
        matched[doc_type] = hits

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    if ranked[0][1] == 0:
        return Classification("unknown", 0.2, [], [])

    top_type, top_score = ranked[0]
    total = sum(scores.values()) or 1
    confidence = min(0.95, max(0.35, top_score / total))
    alternatives = [
        {"type": doc_type, "confidence": round(score / total, 2), "matched_keywords": matched[doc_type]}
        for doc_type, score in ranked[1:3]
        if score > 0
    ]
    return Classification(top_type, round(confidence, 2), alternatives, matched[top_type])


def extract_entities(text: str) -> dict[str, Any]:
    contract_matches = list(CONTRACT_RE.finditer(text))
    protected_spans = [match.span(1) for match in contract_matches]
    amounts = []
    for match in AMOUNT_RE.finditer(text):
        if overlaps(match.span(), protected_spans):
            continue
        raw = match.group(0).strip()
        unit = match.group(2) or "元"
        value = float(match.group(1).replace(",", ""))
        if unit == "万":
            value *= 10000
        amounts.append({"raw": raw, "amount": value, "currency": "CNY"})

    return {
        "amounts": amounts,
        "dates": sorted(set(m.group(1) for m in DATE_RE.finditer(text) if not overlaps(m.span(1), protected_spans))),
        "people": sorted(set(m.group(1) for m in NAME_RE.finditer(text))),
        "contract_numbers": sorted(set(m.group(1) for m in contract_matches)),
        "platforms": [p for p in ["微信", "支付宝", "银行", "淘宝", "京东", "拼多多", "美团", "盒马"] if p in text],
        "departments": [d for d in ["财务", "销售", "厨房", "产康", "护理", "行政", "后勤", "凤稚", "月子餐"] if d in text],
    }


def overlaps(span: tuple[int, int], protected_spans: list[tuple[int, int]]) -> bool:
    start, end = span
    return any(start < protected_end and end > protected_start for protected_start, protected_end in protected_spans)


def build_structured_data(doc_type: str, text: str, entities: dict[str, Any]) -> dict[str, Any]:
    base = {"raw_summary": summarize(text)}
    if doc_type == "payment":
        return {
            **base,
            "payment_type": pick_first(text, ["定金", "尾款", "全款", "押金", "收款", "到账", "转账"]),
            "amount": first_amount(entities),
            "customer_name": first_or_none(entities["people"]),
            "contract_number": first_or_none(entities["contract_numbers"]),
            "payment_date": first_or_none(entities["dates"]),
            "payment_channel": first_or_none(entities["platforms"]),
        }
    if doc_type == "contract":
        return {
            **base,
            "contract_number": first_or_none(entities["contract_numbers"]),
            "customer_name": first_or_none(entities["people"]),
            "contract_amount": first_amount(entities),
            "signed_date": first_or_none(entities["dates"]),
            "package_or_room_hint": pick_phrase(text, ["套餐", "房型", "阳面", "阴面", "标准", "无敌", "凰金", "凰亲"]),
        }
    if doc_type == "reimbursement":
        return {
            **base,
            "expense_amount": first_amount(entities),
            "expense_date": first_or_none(entities["dates"]),
            "department": first_or_none(entities["departments"]),
            "platform": first_or_none(entities["platforms"]),
            "expense_hint": pick_phrase(text, ["报销", "采购", "发票", "维修", "食材", "耗材", "车辆", "月子餐"]),
        }
    if doc_type == "note":
        return {**base, "note_date": first_or_none(entities["dates"]), "mentioned_people": entities["people"]}
    return base


def missing_required_fields(doc_type: str, data: dict[str, Any]) -> list[str]:
    required = {
        "payment": ["amount"],
        "contract": ["customer_name"],
        "reimbursement": ["expense_amount"],
        "note": [],
        "unknown": [],
    }
    missing = []
    for field in required.get(doc_type, []):
        if data.get(field) in (None, "", []):
            missing.append(field)
    return missing


def build_warnings(doc_type: str, text: str, entities: dict[str, Any]) -> list[str]:
    warnings = []
    if doc_type == "unknown":
        warnings.append("无法判断资料类型，需要人工复核")
    if len(entities["amounts"]) > 1:
        warnings.append("识别到多个金额，需要确认主金额")
    if "银行" in entities["platforms"] or "开户行" in text:
        warnings.append("可能包含高敏感付款或银行卡信息")
    return warnings


def first_amount(entities: dict[str, Any]) -> dict[str, Any] | None:
    return entities["amounts"][0] if entities["amounts"] else None


def first_or_none(values: list[Any]) -> Any:
    return values[0] if values else None


def pick_first(text: str, candidates: list[str]) -> str | None:
    return next((candidate for candidate in candidates if candidate in text), None)


def pick_phrase(text: str, candidates: list[str]) -> str | None:
    hit = pick_first(text, candidates)
    if not hit:
        return None
    idx = text.find(hit)
    return text[max(0, idx - 12) : min(len(text), idx + 24)].replace("\n", " ")


def summarize(text: str) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    return compact[:160]
