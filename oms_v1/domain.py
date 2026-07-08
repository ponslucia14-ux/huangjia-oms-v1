from __future__ import annotations

from dataclasses import asdict, dataclass


DOMAIN_SCHEMA_VERSION = "oms.v1.domain_model"


@dataclass(frozen=True)
class DomainDefinition:
    name: str
    identifier: str
    responsibility: str
    lifecycle: tuple[str, ...]
    statuses: tuple[str, ...]
    allowed_actions: tuple[str, ...]
    events: tuple[str, ...]
    audit_events: tuple[str, ...]
    mutable_by_roles: tuple[str, ...]
    schema_version: str = DOMAIN_SCHEMA_VERSION

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _domain(
    name: str,
    identifier: str,
    responsibility: str,
    lifecycle: list[str],
    statuses: list[str],
    actions: list[str],
    events: list[str],
    audits: list[str],
    roles: list[str],
) -> DomainDefinition:
    return DomainDefinition(
        name=name,
        identifier=identifier,
        responsibility=responsibility,
        lifecycle=tuple(lifecycle),
        statuses=tuple(statuses),
        allowed_actions=tuple(actions),
        events=tuple(events),
        audit_events=tuple(audits),
        mutable_by_roles=tuple(roles),
    )


DOMAIN_DEFINITIONS: tuple[DomainDefinition, ...] = (
    _domain(
        "Customer",
        "customer_id",
        "管理客户与妈妈档案的统一身份。",
        ["lead", "consulting", "contracted", "in_service", "completed", "archived"],
        ["active", "inactive", "blocked", "archived"],
        ["create_customer", "update_customer", "archive_customer", "link_contract"],
        ["customer.created", "customer.updated", "customer.archived", "customer.contract_linked"],
        ["customer.create", "customer.update", "customer.archive", "customer.link_contract"],
        ["ROLE_OWNER", "ROLE_STORE_MANAGER", "ROLE_SALES", "ROLE_BUTLER"],
    ),
    _domain(
        "Contract",
        "contract_id",
        "管理客户签约、套餐、合同金额和合同状态。",
        ["draft", "submitted", "confirmed", "active", "completed", "cancelled"],
        ["draft", "pending_review", "active", "completed", "cancelled"],
        ["create_contract", "submit_contract", "confirm_contract", "cancel_contract", "complete_contract"],
        ["contract.created", "contract.submitted", "contract.confirmed", "contract.cancelled", "contract.completed"],
        ["contract.create", "contract.submit", "contract.confirm", "contract.cancel", "contract.complete"],
        ["ROLE_OWNER", "ROLE_STORE_MANAGER", "ROLE_SALES", "ROLE_ACCOUNTANT"],
    ),
    _domain(
        "Payment",
        "payment_id",
        "管理收款、退款、付款与到账确认。",
        ["created", "pending_confirm", "confirmed", "reconciled", "voided"],
        ["pending", "confirmed", "reconciled", "failed", "voided"],
        ["create_payment", "confirm_payment", "reconcile_payment", "void_payment"],
        ["payment.created", "payment.confirmed", "payment.reconciled", "payment.voided"],
        ["payment.create", "payment.confirm", "payment.reconcile", "payment.void"],
        ["ROLE_OWNER", "ROLE_ACCOUNTANT", "ROLE_CASHIER"],
    ),
    _domain(
        "Room",
        "room_id",
        "管理房间、房态、排房资源与房态冲突。",
        ["available", "reserved", "occupied", "cleaning", "maintenance", "closed"],
        ["available", "reserved", "occupied", "cleaning", "maintenance", "closed"],
        ["create_room", "reserve_room", "assign_room", "release_room", "mark_cleaning", "mark_maintenance"],
        ["room.created", "room.reserved", "room.assigned", "room.released", "room.status_changed"],
        ["room.create", "room.reserve", "room.assign", "room.release", "room.status_change"],
        ["ROLE_OWNER", "ROLE_STORE_MANAGER", "ROLE_ADMIN"],
    ),
    _domain(
        "Stay",
        "stay_id",
        "管理客户入住、在住、出馆和服务周期。",
        ["planned", "checkin_ready", "in_house", "checkout_pending", "completed", "cancelled"],
        ["planned", "ready", "in_house", "pending_checkout", "completed", "cancelled"],
        ["create_stay", "prepare_checkin", "check_in", "update_stay", "check_out", "cancel_stay"],
        ["stay.created", "stay.prepared", "stay.checked_in", "stay.updated", "stay.checked_out", "stay.cancelled"],
        ["stay.create", "stay.prepare", "stay.check_in", "stay.update", "stay.check_out", "stay.cancel"],
        ["ROLE_OWNER", "ROLE_STORE_MANAGER", "ROLE_BUTLER", "ROLE_NURSING_DIRECTOR"],
    ),
    _domain(
        "Employee",
        "emp_id",
        "管理 OMS 内部正式员工主数据引用。",
        ["candidate", "active", "transferred", "inactive", "archived"],
        ["active", "inactive", "transferred", "archived"],
        ["create_employee", "update_employee", "transfer_employee", "deactivate_employee"],
        ["employee.created", "employee.updated", "employee.transferred", "employee.deactivated"],
        ["employee.create", "employee.update", "employee.transfer", "employee.deactivate"],
        ["ROLE_OWNER", "ROLE_HR"],
    ),
    _domain(
        "Caregiver",
        "caregiver_id",
        "管理照护师、产护资源、排班和服务能力。",
        ["candidate", "active", "scheduled", "serving", "resting", "inactive"],
        ["active", "scheduled", "serving", "resting", "inactive"],
        ["create_caregiver", "update_caregiver", "schedule_caregiver", "release_caregiver", "deactivate_caregiver"],
        ["caregiver.created", "caregiver.updated", "caregiver.scheduled", "caregiver.released", "caregiver.deactivated"],
        ["caregiver.create", "caregiver.update", "caregiver.schedule", "caregiver.release", "caregiver.deactivate"],
        ["ROLE_OWNER", "ROLE_HR", "ROLE_NURSING_DIRECTOR"],
    ),
    _domain(
        "Expense",
        "expense_id",
        "管理采购、报销、成本和费用归集。",
        ["draft", "submitted", "reviewing", "approved", "paid", "rejected", "voided"],
        ["draft", "pending_review", "approved", "paid", "rejected", "voided"],
        ["create_expense", "submit_expense", "approve_expense", "reject_expense", "mark_paid", "void_expense"],
        ["expense.created", "expense.submitted", "expense.approved", "expense.rejected", "expense.paid", "expense.voided"],
        ["expense.create", "expense.submit", "expense.approve", "expense.reject", "expense.pay", "expense.void"],
        ["ROLE_OWNER", "ROLE_ACCOUNTANT", "ROLE_CASHIER", "ROLE_ADMIN", "ROLE_KITCHEN_DIRECTOR"],
    ),
    _domain(
        "Approval",
        "approval_id",
        "管理审批请求、审批流状态和审批结果。",
        ["created", "pending", "approved", "rejected", "cancelled", "expired"],
        ["pending", "approved", "rejected", "cancelled", "expired"],
        ["create_approval", "approve", "reject", "cancel", "expire"],
        ["approval.created", "approval.approved", "approval.rejected", "approval.cancelled", "approval.expired"],
        ["approval.create", "approval.approve", "approval.reject", "approval.cancel", "approval.expire"],
        ["ROLE_OWNER", "ROLE_ACCOUNTANT", "ROLE_CASHIER", "ROLE_STORE_MANAGER", "ROLE_BUTLER"],
    ),
    _domain(
        "Task",
        "task_id",
        "管理 OMS 内部待办、派单、跟进与完成状态。",
        ["created", "assigned", "in_progress", "blocked", "completed", "cancelled"],
        ["open", "assigned", "in_progress", "blocked", "completed", "cancelled"],
        ["create_task", "assign_task", "start_task", "block_task", "complete_task", "cancel_task"],
        ["task.created", "task.assigned", "task.started", "task.blocked", "task.completed", "task.cancelled"],
        ["task.create", "task.assign", "task.start", "task.block", "task.complete", "task.cancel"],
        ["ROLE_OWNER", "ROLE_STORE_MANAGER", "ROLE_BUTLER", "ROLE_ADMIN", "ROLE_HR"],
    ),
    _domain(
        "Notification",
        "notification_id",
        "管理系统通知、飞书消息、提醒和送达状态。",
        ["created", "queued", "sent", "delivered", "failed", "cancelled"],
        ["queued", "sent", "delivered", "failed", "cancelled"],
        ["create_notification", "queue_notification", "send_notification", "mark_delivered", "mark_failed", "cancel_notification"],
        [
            "notification.created",
            "notification.queued",
            "notification.sent",
            "notification.delivered",
            "notification.failed",
            "notification.cancelled",
        ],
        [
            "notification.create",
            "notification.queue",
            "notification.send",
            "notification.deliver",
            "notification.fail",
            "notification.cancel",
        ],
        ["ROLE_OWNER", "ROLE_ADMIN", "ROLE_HR", "ROLE_STORE_MANAGER", "ROLE_BUTLER"],
    ),
)


class DomainRegistry:
    """Read-only registry of canonical OMS domain definitions."""

    def __init__(self, domains: tuple[DomainDefinition, ...] = DOMAIN_DEFINITIONS):
        self._domains = {domain.name: domain for domain in domains}

    def all(self) -> list[DomainDefinition]:
        return list(self._domains.values())

    def get(self, name: str) -> DomainDefinition:
        try:
            return self._domains[name]
        except KeyError as exc:
            raise KeyError(f"Unknown OMS domain: {name}") from exc

    def names(self) -> list[str]:
        return list(self._domains)

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": DOMAIN_SCHEMA_VERSION,
            "domain_count": len(self._domains),
            "domains": [domain.to_dict() for domain in self.all()],
            "policy": {
                "business_modules_must_reference_domain": True,
                "module_local_object_definitions_allowed": False,
                "database_binding_in_this_phase": False,
            },
        }


def default_domain_registry() -> DomainRegistry:
    return DomainRegistry()
