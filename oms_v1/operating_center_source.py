from __future__ import annotations

import json
import os
from pathlib import Path


OPERATING_CENTER_VERSION = "凰家运营中心（OMS）V1.1"
IDENTITY_LOCK_POLICY = "source_of_truth_locked_no_runtime_alias"
IDENTITY_BINDING_ERROR = {
    "error_type": "identity_binding_required",
    "entry": "login_required",
    "title": "OMS identity binding required",
    "message": "Feishu user_id is required before opening a personal workspace.",
    "action": "reopen_from_feishu_workbench",
}


OPERATING_CENTER_PEOPLE = {
    "boss": {
        "order": 1,
        "name": "主理办（你）",
        "role": "总览 | 决策 | 授权",
        "title": "主理办工作台",
        "focus": ["经营总览", "财务总览", "客户总览（防遗忘）", "房态总览", "风险预警", "数据分析中心", "我的待办"],
        "layer": "business_layer",
        "unit": "主理办",
        "feishu_env": "FEISHU_USER_ID_SHILEI",
    },
    "huanhuan": {
        "order": 2,
        "name": "杨欢欢",
        "role": "销售",
        "title": "销售工作台",
        "focus": ["新增签约", "我的客户", "销售分析"],
        "layer": "business_layer",
        "unit": "销售",
        "feishu_env": "FEISHU_USER_ID_HUANHUAN",
    },
    "june": {
        "order": 3,
        "name": "刘芳羽",
        "role": "店总 + 销售",
        "title": "店总工作台",
        "focus": ["今日经营看板", "销售工作台", "排房工作台", "今日必须处理", "未来30天预产期", "已生产待安排"],
        "layer": "business_layer",
        "unit": "店总 + 销售",
        "feishu_env": "FEISHU_USER_ID_JUNE",
    },
    "liujie": {
        "order": 4,
        "name": "刘晶",
        "role": "出纳",
        "title": "财务工作台",
        "focus": ["待确认到账", "待付款", "日结管理", "收支总览", "财务报表"],
        "layer": "business_layer",
        "unit": "出纳",
        "feishu_env": "FEISHU_USER_ID_LIUJIE",
    },
    "zhangjie": {
        "order": 5,
        "name": "张敬东",
        "role": "财务总监/会计",
        "title": "财务总监工作台",
        "focus": ["财务总览", "资金流水", "利润报表", "成本分析", "预算管理", "财务审批"],
        "layer": "business_layer",
        "unit": "财务总监/会计",
        "feishu_env": "FEISHU_USER_ID_ZHANGJIE",
    },
    "nana": {
        "order": 6,
        "name": "尚丽娜",
        "role": "管家",
        "title": "管家工作台",
        "focus": ["今日入住", "在住妈妈", "CRM客户管理"],
        "layer": "business_layer",
        "unit": "管家",
        "feishu_env": "FEISHU_USER_ID_NANA",
    },
    "chenchangyi": {
        "order": 7,
        "name": "陈晶辉",
        "role": "产护部总监",
        "title": "产护工作台",
        "focus": ["今日入住", "在住产护一览", "套餐信息", "入住/出馆日期", "产康套餐内容", "特殊护理要求"],
        "layer": "support_layer",
        "unit": "产护部总监",
        "feishu_env": "FEISHU_USER_ID_CHENCHANGYI",
    },
    "zhouchen": {
        "order": 8,
        "name": "周志朋",
        "role": "厨师长",
        "title": "料理工作台",
        "focus": ["今日入住", "在住饮食一览", "忌口管理", "特殊餐管理", "加餐管理"],
        "layer": "support_layer",
        "unit": "厨师长",
        "feishu_env": "FEISHU_USER_ID_ZHOUCHEN",
    },
    "yaowei": {
        "order": 9,
        "name": "石昊昕",
        "role": "行政采购 + 照护师工资决算",
        "title": "行政采购工作台",
        "focus": ["行政采购", "报销", "照护师工资决算"],
        "layer": "support_layer",
        "unit": "行政采购 + 照护师工资决算",
        "feishu_env": "FEISHU_USER_ID_YAOWEI",
    },
    "songxue": {
        "order": 10,
        "name": "宗惠",
        "role": "人事行政",
        "title": "人事行政工作台",
        "focus": ["考勤管理", "工资管理", "员工档案", "人事审批"],
        "layer": "support_layer",
        "unit": "人事行政",
        "feishu_env": "FEISHU_USER_ID_SONGXUE",
    },
    "yuchun": {
        "order": 11,
        "name": "薛子渝",
        "role": "食材采购 + 销售",
        "title": "食材采购 + 销售工作台",
        "focus": ["食材采购", "销售工作台"],
        "layer": "support_layer",
        "unit": "食材采购 + 销售",
        "feishu_env": "FEISHU_USER_ID_YUCHUN",
    },
}


WORKSPACE_KEYS = {key: key for key in OPERATING_CENTER_PEOPLE}
ROLE_USER_ALIASES: dict[str, str] = {}
WORKSPACE_KEY_BY_ROLE = {person["role"]: key for key, person in OPERATING_CENTER_PEOPLE.items()}
WORKSPACE_KEY_BY_ROLE.update({person["name"]: key for key, person in OPERATING_CENTER_PEOPLE.items()})
WORKSPACE_KEY_BY_ROLE.update(
    {
        "主理办（你）": "boss",
        "销售": "huanhuan",
        "财务": "liujie",
        "管理": "boss",
        "行政采购": "yaowei",
        "产护支持": "chenchangyi",
        "餐饮/厨房": "zhouchen",
        "后勤保障": "yaowei",
    }
)
MAPPING_ROW_NAMES = {
    "boss": ("石磊", "主理办（你）"),
    "huanhuan": ("杨欢欢", "销售"),
    "june": ("刘芳羽",),
    "liujie": ("刘晶",),
    "zhangjie": ("张敬东",),
    "nana": ("尚丽娜",),
    "chenchangyi": ("陈晶辉",),
    "zhouchen": ("周志朋",),
    "yaowei": ("石昊昕",),
    "songxue": ("宗惠",),
    "yuchun": ("薛子渝",),
}


def canonical_person(workspace_key: str) -> dict[str, str]:
    if workspace_key not in OPERATING_CENTER_PEOPLE:
        raise KeyError(f"unknown workspace_key: {workspace_key}")
    return OPERATING_CENTER_PEOPLE[workspace_key]


def feishu_identity_bindings(
    *,
    live_root: str | Path | None = None,
    env: dict[str, str] | None = None,
    env_path: str | Path | None = None,
) -> dict[str, dict[str, str]]:
    enrichment_path = _identity_enrichment_path(live_root)
    if enrichment_path and enrichment_path.exists():
        bindings = _read_enriched_identity_bindings(enrichment_path)
        if bindings:
            return bindings
    mapping_path = _realworld_mapping_path(live_root)
    if mapping_path and mapping_path.exists():
        return _read_realworld_identity_bindings(mapping_path)
    return {}


def workspace_key_for_feishu_identity(
    identity_ids: set[str],
    *,
    live_root: str | Path | None = None,
    env: dict[str, str] | None = None,
    env_path: str | Path | None = None,
) -> tuple[str, str]:
    identity_ids = {item for item in identity_ids if item}
    bindings = feishu_identity_bindings(live_root=live_root, env=env, env_path=env_path)
    for key, identity in bindings.items():
        ids = {identity.get("user_id", ""), identity.get("open_id", ""), identity.get("union_id", "")}
        if identity_ids & ids:
            return key, identity.get("source", "feishu_identity_binding")
    return "", "identity_binding_required"


def _identity_enrichment_path(live_root: str | Path | None) -> Path | None:
    root = Path(live_root) if live_root else Path(os.getenv("OMS_LIVE_ROOT", "").strip() or Path(__file__).resolve().parents[1] / "live_runtime")
    return root / "human_identity" / "identity_enrichment_layer.json"


def _realworld_mapping_path(live_root: str | Path | None) -> Path | None:
    if live_root:
        return Path(live_root) / "realworld_mapping" / "OMS_RealWorld_Mapping.json"
    env_live_root = os.getenv("OMS_LIVE_ROOT", "").strip()
    if env_live_root:
        return Path(env_live_root) / "realworld_mapping" / "OMS_RealWorld_Mapping.json"
    default_path = Path(__file__).resolve().parents[1] / "live_runtime" / "realworld_mapping" / "OMS_RealWorld_Mapping.json"
    return default_path


def _read_enriched_identity_bindings(path: Path) -> dict[str, dict[str, str]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    rows = data.get("rows") if isinstance(data, dict) else []
    if not isinstance(rows, list):
        return {}
    bindings: dict[str, dict[str, str]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        workspace_key = str(row.get("workspace_key") or "")
        if workspace_key not in OPERATING_CENTER_PEOPLE:
            continue
        base = row.get("base_identity") if isinstance(row.get("base_identity"), dict) else {}
        enriched = row.get("enriched_identity") if isinstance(row.get("enriched_identity"), dict) else {}
        user_id = str(base.get("feishu_user_id") or "").strip()
        if not user_id:
            continue
        bindings[workspace_key] = {
            "user_id": user_id,
            "open_id": str(base.get("open_id") or "").strip(),
            "union_id": str(base.get("union_id") or "").strip(),
            "name": str(enriched.get("display_name") or "").strip(),
            "role": str(enriched.get("role") or "").strip(),
            "workspace": str(enriched.get("workspace") or "").strip(),
            "department": str(enriched.get("department") or "").strip(),
            "source": "identity_enrichment_layer",
            "binding_confidence": str(row.get("identity_confidence") or "").strip(),
            "metadata_status": str(row.get("metadata_status") or "").strip(),
            "execution_status": str(row.get("execution_status") or "").strip(),
        }
    return bindings


def _read_realworld_identity_bindings(path: Path) -> dict[str, dict[str, str]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    rows = data.get("rows") if isinstance(data, dict) else []
    if not isinstance(rows, list):
        return {}
    bindings: dict[str, dict[str, str]] = {}
    for workspace_key, names in MAPPING_ROW_NAMES.items():
        person = OPERATING_CENTER_PEOPLE[workspace_key]
        candidates = set(names)
        candidates.add(person["name"])
        candidates.add(person["role"])
        for row in rows:
            if not isinstance(row, dict):
                continue
            row_names = {str(row.get("name") or ""), str(row.get("role") or "")}
            user_id = str(row.get("user_id") or "").strip()
            if candidates & row_names and user_id:
                bindings[workspace_key] = {
                    "user_id": user_id,
                    "open_id": str(row.get("open_id") or "").strip(),
                    "union_id": str(row.get("union_id") or "").strip(),
                    "name": str(row.get("name") or "").strip(),
                    "role": str(row.get("role") or "").strip(),
                    "source": "feishu_realworld_mapping",
                }
                break
    return bindings


def _read_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values
