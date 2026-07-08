import tempfile
import unittest
from pathlib import Path

from oms_v1.audit_log import AuditEngine
from oms_v1.contract_payment import ContractPaymentStore, ContractService, PaymentService
from oms_v1.event_bus import EventBus
from oms_v1.master_data import OMSMasterData
from tests.test_health_check import write_identity, write_organization


class ContractPaymentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        organization_path = root / "OMS_组织主数据.md"
        identity_path = root / "OMS_飞书身份映射.md"
        write_organization(organization_path)
        write_identity(identity_path)
        self.master_data = OMSMasterData(organization_path=organization_path, feishu_identity_path=identity_path)
        self.store = ContractPaymentStore()
        self.audit = AuditEngine(root / "audit")
        self.bus = EventBus()
        self.delivered_events = []
        for event_type in ["contract.created", "payment.recorded", "payment.confirmed"]:
            self.bus.subscribe(
                module="test_listener",
                event_type=event_type,
                handler=lambda event: self.delivered_events.append(event.event_type) or "ok",
            )
        self.contracts = ContractService(store=self.store, audit=self.audit, event_bus=self.bus, master_data=self.master_data)
        self.payments = PaymentService(store=self.store, audit=self.audit, event_bus=self.bus, master_data=self.master_data)

    def tearDown(self):
        self.tmp.cleanup()

    def _create_contract(self):
        return self.contracts.create_contract(
            actor_emp_id="EMP006",
            customer_id="customer_001",
            customer_name="客户A",
            contract_number="HT-2026-001",
            amount="39800",
            package_name="28天套餐",
            reason="客户正式签约",
        )

    def test_contract_payment_minimum_loop_writes_audit_and_publishes_events(self):
        contract_result = self._create_contract()
        contract_id = contract_result["contract"]["contract_id"]

        payment_result = self.payments.record_payment(
            actor_emp_id="EMP004",
            contract_id=contract_id,
            amount="10000",
            payment_method="bank_transfer",
            reason="客户支付定金",
        )
        confirm_result = self.payments.confirm_payment(
            actor_emp_id="EMP004",
            payment_id=payment_result["payment"]["payment_id"],
            reason="银行到账确认",
        )

        self.assertEqual(contract_result["event"]["event"]["event_type"], "contract.created")
        self.assertEqual(payment_result["event"]["event"]["event_type"], "payment.recorded")
        self.assertEqual(confirm_result["event"]["event"]["event_type"], "payment.confirmed")
        self.assertEqual(confirm_result["payment"]["status"], "confirmed")
        self.assertEqual(self.delivered_events, ["contract.created", "payment.recorded", "payment.confirmed"])

        audit_events = self.audit.events(sort_by_time=False)
        self.assertEqual([event["action"] for event in audit_events], ["create_contract", "record_payment", "confirm_payment"])
        self.assertEqual([event["reason"] for event in audit_events], ["客户正式签约", "客户支付定金", "银行到账确认"])
        self.assertEqual({event["emp_id"] for event in audit_events}, {"EMP006", "EMP004"})

    def test_reason_is_required_for_each_key_action(self):
        with self.assertRaises(ValueError):
            self.contracts.create_contract(
                actor_emp_id="EMP006",
                customer_id="customer_001",
                customer_name="客户A",
                contract_number="HT-2026-001",
                amount="39800",
                package_name="28天套餐",
                reason="",
            )
        contract_id = self._create_contract()["contract"]["contract_id"]
        with self.assertRaises(ValueError):
            self.payments.record_payment(
                actor_emp_id="EMP004",
                contract_id=contract_id,
                amount="10000",
                payment_method="bank_transfer",
                reason="",
            )

    def test_actor_must_be_emp_and_have_domain_permission(self):
        with self.assertRaises(KeyError):
            self.contracts.create_contract(
                actor_emp_id="杨欢欢",
                customer_id="customer_001",
                customer_name="客户A",
                contract_number="HT-2026-001",
                amount="39800",
                package_name="28天套餐",
                reason="测试昵称不能作为 actor",
            )
        contract_id = self._create_contract()["contract"]["contract_id"]
        with self.assertRaises(PermissionError):
            self.payments.record_payment(
                actor_emp_id="EMP006",
                contract_id=contract_id,
                amount="10000",
                payment_method="bank_transfer",
                reason="销售不能录入收款",
            )

    def test_invalid_payment_state_is_rejected(self):
        contract_id = self._create_contract()["contract"]["contract_id"]
        payment = self.payments.record_payment(
            actor_emp_id="EMP004",
            contract_id=contract_id,
            amount="10000",
            payment_method="bank_transfer",
            reason="客户支付定金",
        )
        payment_id = payment["payment"]["payment_id"]
        self.payments.confirm_payment(actor_emp_id="EMP004", payment_id=payment_id, reason="银行到账确认")

        with self.assertRaises(ValueError):
            self.payments.confirm_payment(actor_emp_id="EMP004", payment_id=payment_id, reason="重复确认到账")


if __name__ == "__main__":
    unittest.main()
