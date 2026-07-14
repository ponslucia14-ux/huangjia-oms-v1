import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ProcurementUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = (ROOT / "oms_app" / "app.js").read_text(encoding="utf-8")
        cls.profiles = (ROOT / "oms_app" / "workspace-profiles.js").read_text(encoding="utf-8")
        cls.styles = (ROOT / "oms_app" / "styles.css").read_text(encoding="utf-8")

    def test_only_expected_workspaces_receive_procurement_actions(self):
        self.assertIn('menu("admin_procurement", "行政采购"', self.profiles)
        self.assertIn('menu("dual_food", "食材采购"', self.profiles)
        self.assertIn('item("owner_pending_approval"', self.profiles)
        self.assertIn('item("cashier_payment_pending"', self.profiles)
        self.assertIn('item("accounting_payment_pending"', self.profiles)
        self.assertIn('["EMP001", "EMP003", "EMP004", "EMP005", "EMP007"]', self.app)

    def test_procurement_pages_are_real_forms_not_empty_placeholders(self):
        for marker in (
            "data-procurement-form",
            "data-procurement-decision-form",
            "data-procurement-payment-form",
            "data-procurement-accounting-form",
            "data-procurement-detail-open",
            "/api/oms/procurement/draft",
            "/api/oms/procurement/submit",
            "/api/oms/procurement/decision",
            "/api/oms/procurement/payment",
            "/api/oms/procurement/accounting",
        ):
            self.assertIn(marker, self.app)

    def test_mobile_procurement_layout_is_single_column(self):
        self.assertIn(".procurement-workspace", self.styles)
        self.assertIn("@media (max-width: 720px)", self.styles)
        mobile = self.styles.split("@media (max-width: 720px)", 1)[1]
        self.assertIn("grid-template-columns: 1fr", mobile)

    def test_unknown_technical_errors_are_not_shown_to_staff(self):
        self.assertIn('if (text && !/[A-Za-z_]/.test(text)) return text;', self.app)
        self.assertIn("return userFacingError();", self.app)


if __name__ == "__main__":
    unittest.main()
