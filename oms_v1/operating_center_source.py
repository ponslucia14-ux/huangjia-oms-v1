from __future__ import annotations


OPERATING_CENTER_VERSION = "凰家运营中心（OMS）V1.1"
IDENTITY_LOCK_POLICY = "source_of_truth_locked_no_runtime_alias"
UNRESOLVED_IDENTITY = {
    "workspace_key": "__unresolved__",
    "name": "未绑定用户",
    "role": "身份未绑定",
    "title": "个人工作台未绑定",
    "layer": "unresolved",
    "unit": "unresolved",
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
        "feishu_env": "FEISHU_USER_ID_BOSS",
    },
    "huanhuan": {
        "order": 2,
        "name": "欢欢",
        "role": "销售",
        "title": "销售工作台",
        "focus": ["新增签约", "我的客户", "销售分析"],
        "layer": "business_layer",
        "unit": "销售",
        "feishu_env": "FEISHU_USER_ID_HUANHUAN",
    },
    "june": {
        "order": 3,
        "name": "六月",
        "role": "店总 + 销售",
        "title": "店总工作台",
        "focus": ["今日经营看板", "销售工作台", "排房工作台", "今日必须处理", "未来30天预产期", "已生产待安排"],
        "layer": "business_layer",
        "unit": "店总 + 销售",
        "feishu_env": "FEISHU_USER_ID_JUNE",
    },
    "liujie": {
        "order": 4,
        "name": "刘姐",
        "role": "出纳",
        "title": "财务工作台",
        "focus": ["待确认到账", "待付款", "日结管理", "收支总览", "财务报表"],
        "layer": "business_layer",
        "unit": "出纳",
        "feishu_env": "FEISHU_USER_ID_LIUJIE",
    },
    "zhangjie": {
        "order": 5,
        "name": "张姐",
        "role": "财务总监/会计",
        "title": "财务总监工作台",
        "focus": ["财务总览", "资金流水", "利润报表", "成本分析", "预算管理", "财务审批"],
        "layer": "business_layer",
        "unit": "财务总监/会计",
        "feishu_env": "FEISHU_USER_ID_ZHANGJIE",
    },
    "nana": {
        "order": 6,
        "name": "娜娜",
        "role": "管家",
        "title": "管家工作台",
        "focus": ["今日入住", "在住妈妈", "CRM客户管理"],
        "layer": "business_layer",
        "unit": "管家",
        "feishu_env": "FEISHU_USER_ID_NANA",
    },
    "chenchangyi": {
        "order": 7,
        "name": "陈昌辉",
        "role": "产护部总监",
        "title": "产护工作台",
        "focus": ["今日入住", "在住产护一览", "套餐信息", "入住/出馆日期", "产康套餐内容", "特殊护理要求"],
        "layer": "support_layer",
        "unit": "产护部总监",
        "feishu_env": "FEISHU_USER_ID_CHENCHANGYI",
    },
    "zhouchen": {
        "order": 8,
        "name": "周厨",
        "role": "厨师长",
        "title": "料理工作台",
        "focus": ["今日入住", "在住饮食一览", "忌口管理", "特殊餐管理", "加餐管理"],
        "layer": "support_layer",
        "unit": "厨师长",
        "feishu_env": "FEISHU_USER_ID_ZHOUCHEN",
    },
    "yaowei": {
        "order": 9,
        "name": "维维",
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
        "name": "子渝",
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


def canonical_person(workspace_key: str) -> dict[str, str]:
    return OPERATING_CENTER_PEOPLE.get(workspace_key, UNRESOLVED_IDENTITY)
