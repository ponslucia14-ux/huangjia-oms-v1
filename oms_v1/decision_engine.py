from __future__ import annotations

from typing import Any

from .schemas import DecisionRecommendation, now_iso


class DecisionEngine:
    """Convert business events into non-executing recommendations."""

    def build_decision_stream(self, event_stream: dict[str, Any]) -> dict[str, Any]:
        decisions = self.decide(event_stream)
        return {
            "schema_version": "oms.v1.decision_stream",
            "input_id": event_stream.get("input_id"),
            "flow": ["input", "parsed_json", "business_events", "recommendations"],
            "decisions": [decision.to_dict() for decision in decisions],
            "audit": {
                "created_at": now_iso(),
                "decision_count": len(decisions),
                "direct_execution_allowed": False,
                "human_override_required": True,
            },
        }

    def decide(self, event_stream: dict[str, Any]) -> list[DecisionRecommendation]:
        decisions: list[DecisionRecommendation] = []
        for event in event_stream.get("events", []):
            event_type = event.get("event_type")
            if event_type == "room_status_event":
                decisions.extend(self._room_decisions(event))
            elif event_type == "financial_event":
                decisions.extend(self._financial_decisions(event))
            elif event_type == "service_event":
                decisions.extend(self._service_decisions(event))
            elif event_type == "sales_event":
                decisions.extend(self._sales_link_decisions(event))
        return decisions

    def _room_decisions(self, event: dict[str, Any]) -> list[DecisionRecommendation]:
        payload = event.get("payload", {})
        raw = self._raw(payload)
        decisions: list[DecisionRecommendation] = []

        if self._has_any(raw, ["已生", "已生产", "生了"]):
            decisions.append(
                self._decision(
                    event,
                    "room_assignment",
                    "标记为已生优先，优先检查近期可用房和入住准备。",
                    "high",
                    "medium",
                    "房态事件中出现已生/生产线索，六月排房逻辑需要优先处理已生客户。",
                    ["BOSS", "六月"],
                )
            )

        if self._has_any(raw, ["超卖", "没房", "满房", "房间不够", "爆房"]):
            decisions.append(
                self._decision(
                    event,
                    "room_risk",
                    "发出超卖风险预警，要求六月复核房态和待入住名单。",
                    "urgent",
                    "high",
                    "房态事件中出现超卖/满房/房间不够线索，存在无法按原计划入住的风险。",
                    ["BOSS", "六月"],
                )
            )

        if self._has_any(raw, ["调房", "换房", "倒房"]):
            decisions.append(
                self._decision(
                    event,
                    "room_scheduling",
                    "建议进入调房/倒房期调整队列，由六月人工确认。",
                    "high",
                    "medium",
                    "房态事件中出现调房、换房或倒房线索，系统只能建议排程，不能直接改房态。",
                    ["六月"],
                )
            )

        if self._has_any(raw, ["入住", "待入住", "房间", "房态", "调房", "换房", "倒房"]):
            decisions.append(
                self._decision(
                    event,
                    "support_logistics",
                    "建议后勤保障准备房间清理、设备检查和物资配送。",
                    "normal",
                    "low",
                    "房态/入住业务流会触发房间、设备和物资保障，后勤需要提前进入支撑层工作项。",
                    ["后勤", "六月"],
                )
            )

        if self._has_any(raw, ["劝退", "居家", "回家服务"]):
            decisions.append(
                self._decision(
                    event,
                    "room_exception",
                    "建议评估劝退或居家服务方案，并同步服务与财务影响。",
                    "urgent",
                    "high",
                    "房态事件中出现劝退/居家服务线索，可能影响客户体验、服务安排和费用口径。",
                    ["BOSS", "六月", "娜娜", "刘姐"],
                )
            )

        if not any(decision.decision_type.startswith("room_") or decision.decision_type == "room_assignment" for decision in decisions):
            decisions.append(
                self._decision(
                    event,
                    "room_assignment",
                    "建议六月复核入住/房态线索，确认是否需要排房动作。",
                    "normal",
                    "low",
                    "事件包含入住、房间或房态线索，但未命中特殊风险词，需要人工确认是否进入排房。",
                    ["六月"],
                )
            )
        return decisions

    def _financial_decisions(self, event: dict[str, Any]) -> list[DecisionRecommendation]:
        payload = event.get("payload", {})
        raw = self._raw(payload)
        amount = payload.get("amount") or {}
        amount_value = amount.get("amount") if isinstance(amount, dict) else None
        decisions: list[DecisionRecommendation] = []

        if event.get("action") == "payment_received":
            decisions.append(
                self._decision(
                    event,
                    "finance_reconciliation",
                    "建议刘姐核对收款到账，并关联合同/客户档案。",
                    "high",
                    "medium",
                    "财务事件为收款到账，必须进入对账确认；系统只建议，不直接入账。",
                    ["BOSS", "刘姐"],
                )
            )
            if amount_value and amount_value >= 30000:
                decisions.append(
                    self._decision(
                        event,
                        "finance_risk",
                        "建议标记为大额收款，复核合同金额、收款账户和款项性质。",
                        "high",
                        "medium",
                        "收款金额达到大额阈值，存在合同金额、分期或异常收款核对需求。",
                        ["BOSS", "刘姐"],
                    )
                )

        if event.get("action") == "reimbursement_submitted":
            decisions.append(
                self._decision(
                    event,
                    "payment_required",
                    "建议进入待付款/待报销复核队列。",
                    "normal",
                    "medium",
                    "财务事件为报销或采购费用，需要刘姐确认凭证、金额和付款状态。",
                    ["刘姐", "BOSS"],
                )
            )
            decisions.append(
                self._decision(
                    event,
                    "support_admin_procurement",
                    "建议行政采购核对采购申请、物资补给和消耗品补充。",
                    "normal",
                    "medium",
                    "报销/采购费用业务流会影响行政采购和物资补给，需要支撑层同步生成工作项。",
                    ["行政", "采购", "刘姐"],
                )
            )
            if self._has_any(raw, ["厨房", "月子餐", "食材", "餐食"]):
                decisions.append(
                    self._decision(
                        event,
                        "support_kitchen",
                        "建议餐饮/厨房确认食材采购、餐食准备和备餐计划。",
                        "normal",
                        "medium",
                        "采购内容涉及厨房、餐食或食材，需要餐饮/厨房进入支撑层流转。",
                        ["厨房", "刘姐"],
                    )
                )
            if self._has_any(raw, ["重复", "补发", "又发", "同一张", "同一单"]):
                decisions.append(
                    self._decision(
                        event,
                        "finance_risk",
                        "建议标记为疑似重复报销，付款前人工复核。",
                        "urgent",
                        "high",
                        "报销文本中出现重复/补发/同一单线索，存在重复付款风险。",
                        ["刘姐", "BOSS"],
                    )
                )

        if self._has_any(raw, ["服务金额", "服务日房款", "拆分"]):
            decisions.append(
                self._decision(
                    event,
                    "service_amount_split",
                    "建议进入服务金额拆分复核。",
                    "high",
                    "medium",
                    "财务事件涉及服务金额或服务日房款，需按凰家服务金额口径拆分，不能直接按收款入账。",
                    ["刘姐", "BOSS"],
                )
            )

        return decisions

    def _service_decisions(self, event: dict[str, Any]) -> list[DecisionRecommendation]:
        payload = event.get("payload", {})
        raw = self._raw(payload)
        decisions: list[DecisionRecommendation] = []

        if self._has_any(raw, ["入住", "待入住", "上户"]):
            decisions.append(
                self._decision(
                    event,
                    "service_preparation",
                    "建议娜娜启动入住准备检查，并同步管家/产护/厨房。",
                    "high",
                    "medium",
                    "服务事件中出现入住或上户线索，服务准备需要提前协同。",
                    ["娜娜", "六月"],
                )
            )
            decisions.extend(
                [
                    self._decision(
                        event,
                        "support_maternity_care",
                        "建议产护支持确认人员调度、护理资源分配和临时支援。",
                        "normal",
                        "medium",
                        "入住准备会触发产护资源安排，支撑层需要提前生成产护支持工作项。",
                        ["产护", "娜娜"],
                    ),
                    self._decision(
                        event,
                        "support_kitchen",
                        "建议餐饮/厨房准备餐食、特殊餐需求和备餐计划。",
                        "normal",
                        "medium",
                        "入住准备会触发餐饮/厨房备餐协同，需要支撑层同步生成工作项。",
                        ["厨房", "娜娜"],
                    ),
                    self._decision(
                        event,
                        "support_logistics",
                        "建议后勤保障确认房间清理、设备维护和物资配送。",
                        "normal",
                        "medium",
                        "入住准备会触发房间和设备保障，需要后勤进入支撑层工作项。",
                        ["后勤", "娜娜"],
                    ),
                ]
            )

        if self._has_any(raw, ["异常", "投诉", "不满意", "延迟", "没到", "缺人"]):
            decisions.append(
                self._decision(
                    event,
                    "service_risk",
                    "建议标记服务异常或延迟风险，由娜娜协调处理。",
                    "urgent",
                    "high",
                    "服务事件中出现异常、投诉、延迟或缺人线索，可能影响客户体验。",
                    ["娜娜", "BOSS"],
                )
            )

        if self._has_any(raw, ["厨房", "月子餐", "餐食", "产护", "护理", "医生"]):
            decisions.append(
                self._decision(
                    event,
                    "service_coordination",
                    "建议娜娜协调产护/厨房/相关服务岗位。",
                    "normal",
                    "medium",
                    "服务事件涉及厨房、餐食、产护或护理，需要跨岗位协同。",
                    ["娜娜"],
                )
            )
            if self._has_any(raw, ["产护", "护理", "医生"]):
                decisions.append(
                    self._decision(
                        event,
                        "support_maternity_care",
                        "建议产护支持安排护理资源和临时支援。",
                        "normal",
                        "medium",
                        "服务协同内容涉及产护、护理或医生，需要产护支持进入支撑层。",
                        ["产护", "娜娜"],
                    )
                )
            if self._has_any(raw, ["厨房", "月子餐", "餐食"]):
                decisions.append(
                    self._decision(
                        event,
                        "support_kitchen",
                        "建议餐饮/厨房确认特殊餐需求和备餐计划。",
                        "normal",
                        "medium",
                        "服务协同内容涉及厨房、月子餐或餐食，需要餐饮/厨房进入支撑层。",
                        ["厨房", "娜娜"],
                    )
                )

        if not decisions:
            decisions.append(
                self._decision(
                    event,
                    "service_followup",
                    "建议娜娜复核服务备注，判断是否需要跟进。",
                    "normal",
                    "low",
                    "事件包含服务或备注线索，但未命中特殊风险词，需要人工确认。",
                    ["娜娜"],
                )
            )
        return decisions

    def _sales_link_decisions(self, event: dict[str, Any]) -> list[DecisionRecommendation]:
        return [
            self._decision(
                event,
                "sales_to_operations",
                "建议销售事件同步财务和房态，确认合同、收款和入住安排是否闭环。",
                "normal",
                "low",
                "签约事件通常会影响收款、排房和服务准备，需要后续事件或人工确认闭环。",
                ["BOSS", "六月", "刘姐"],
            )
        ]

    def _decision(
        self,
        event: dict[str, Any],
        decision_type: str,
        recommended_action: str,
        priority: str,
        risk_level: str,
        reason: str,
        roles: list[str],
    ) -> DecisionRecommendation:
        return DecisionRecommendation(
            event_id=event.get("event_id", ""),
            decision_type=decision_type,
            recommended_action=recommended_action,
            priority=priority,
            risk_level=risk_level,
            reason=f"{reason} 基于事件 {event.get('event_id', '')} ({event.get('event_type', '')}/{event.get('action', '')})。",
            override_roles=roles,
            source_event_type=event.get("event_type"),
        )

    def _raw(self, payload: dict[str, Any]) -> str:
        values = [str(v) for v in payload.values() if v is not None]
        return " ".join(values)

    def _has_any(self, text: str, keywords: list[str]) -> bool:
        return any(keyword in text for keyword in keywords)
