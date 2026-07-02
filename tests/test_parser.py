import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from oms_v1.data_parser import OMSDataParser
from oms_v1.input_hub import OMSInputHub


class ParserTests(unittest.TestCase):
    def setUp(self):
        self.hub = OMSInputHub()
        self.parser = OMSDataParser()

    def test_payment_message_to_json(self):
        env = self.hub.accept_text("刘姐收到客户张三尾款 20000 元，7月2日到账，合同编号 HJM20260702")
        result = self.parser.parse(env)
        self.assertEqual(result["document_type"], "payment")
        self.assertEqual(result["structured_data"]["amount"]["amount"], 20000)
        self.assertEqual(result["structured_data"]["payment_type"], "尾款")
        self.assertEqual(result["structured_data"]["contract_number"], "HJM20260702")

    def test_reimbursement_message_to_json(self):
        env = self.hub.accept_text("维维报销厨房采购鸡蛋 360 元，美团，6.29 单据已发")
        result = self.parser.parse(env)
        self.assertEqual(result["document_type"], "reimbursement")
        self.assertEqual(result["structured_data"]["expense_amount"]["amount"], 360)
        self.assertIn("厨房", result["entities"]["departments"])

    def test_contract_message_to_json(self):
        env = self.hub.accept_text("客户姓名：李梅，签约无敌套餐，合同编号 HJ-2026-001，全款费用 49800 元")
        result = self.parser.parse(env)
        self.assertEqual(result["document_type"], "contract")
        self.assertEqual(result["structured_data"]["customer_name"], "李梅")
        self.assertEqual(result["structured_data"]["contract_amount"]["amount"], 49800)
        self.assertEqual(result["entities"]["dates"], [])

    def test_image_without_ocr_engine_is_explicit(self):
        with TemporaryDirectory() as tmp:
            image = Path(tmp) / "receipt.png"
            image.write_bytes(b"not-a-real-image")
            env = self.hub.accept_file(image)
            result = self.parser.parse(env)
            self.assertIn(result["status"], {"ocr_unavailable", "unparsed"})
            self.assertEqual(result["document_type"], "unknown")


if __name__ == "__main__":
    unittest.main()
