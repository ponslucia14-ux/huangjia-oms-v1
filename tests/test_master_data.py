import tempfile
import unittest

from oms_v1.master_data import OMSMasterData
from tests.test_feishu_mapping import write_identity_mapping, write_organization_master_data


class MasterDataTests(unittest.TestCase):
    def test_reads_organization_and_feishu_identity_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            organization_path = f"{tmp}/OMS_组织主数据.md"
            identity_path = f"{tmp}/OMS_飞书身份映射.md"
            write_organization_master_data(organization_path)
            write_identity_mapping(identity_path)

            master_data = OMSMasterData(organization_path=organization_path, feishu_identity_path=identity_path)

            self.assertEqual(master_data.final_authority_name(), "石磊")
            self.assertEqual(master_data.employee_by_role("ROLE_CASHIER").name, "刘晶")
            self.assertEqual(master_data.employee_by_role("ROLE_BUTLER").user_id, "9dcg7e27")
            self.assertEqual(master_data.module_owner("finance_module"), "刘晶")
            self.assertEqual(master_data.role_permissions()["刘芳羽"]["approve"], ["room_status_module"])


if __name__ == "__main__":
    unittest.main()
