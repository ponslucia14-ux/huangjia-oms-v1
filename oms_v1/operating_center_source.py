from __future__ import annotations


OPERATING_CENTER_VERSION = "凰家运营中心（OMS）V1.1"

OPERATING_CENTER_PEOPLE = {
    "boss": {
        "order": 1,
        "name": "王梦为",
        "role": "总控",
        "title": "总控工作台",
        "focus": ["经营总览", "决策", "验收"],
        "layer": "business_layer",
        "unit": "经营总览",
        "aliases": ["BOSS", "boss", "老板", "王梦为", "总控"],
        "feishu_env": "FEISHU_USER_ID_BOSS",
    },
    "huanhuan": {
        "order": 2,
        "name": "欢欢",
        "role": "销售",
        "title": "销售工作台",
        "focus": ["销售签约", "意向客户", "销售分析"],
        "layer": "business_layer",
        "unit": "销售",
        "aliases": ["欢欢", "huanhuan", "销售"],
        "feishu_env": "FEISHU_USER_ID_HUANHUAN",
    },
    "june": {
        "order": 3,
        "name": "六月",
        "role": "店长 + 销售",
        "title": "店总工作台",
        "focus": ["经营事务", "排房", "销售下房"],
        "layer": "business_layer",
        "unit": "店长 + 销售",
        "aliases": ["六月", "june", "店长", "店总"],
        "feishu_env": "FEISHU_USER_ID_JUNE",
    },
    "liujie": {
        "order": 4,
        "name": "刘姐",
        "role": "出纳",
        "title": "财务工作台",
        "focus": ["待收款", "日结管理", "收支台账"],
        "layer": "business_layer",
        "unit": "出纳",
        "aliases": ["刘姐", "liujie", "出纳", "财务"],
        "feishu_env": "FEISHU_USER_ID_LIUJIE",
    },
    "zhangjie": {
        "order": 5,
        "name": "张姐",
        "role": "财务总监/会计",
        "title": "财务总监工作台",
        "focus": ["财务总览", "现金流水", "财务审核"],
        "layer": "business_layer",
        "unit": "财务总监/会计",
        "aliases": ["张姐", "zhangjie", "财务总监", "会计"],
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
        "aliases": ["娜娜", "nana", "管家"],
        "feishu_env": "FEISHU_USER_ID_NANA",
    },
    "chenchangyi": {
        "order": 7,
        "name": "陈昌伊",
        "role": "产护总监",
        "title": "产护工作台",
        "focus": ["产护服务", "护理资源", "待排护理需求"],
        "layer": "support_layer",
        "unit": "产护总监",
        "aliases": ["陈昌伊", "chenchangyi", "产护", "产护总监"],
        "feishu_env": "FEISHU_USER_ID_CHENCHANGYI",
    },
    "zhouchen": {
        "order": 8,
        "name": "周辰",
        "role": "厨师长",
        "title": "月厨工作台",
        "focus": ["今日入住", "在住饮食一览", "特殊餐管理"],
        "layer": "support_layer",
        "unit": "厨师长",
        "aliases": ["周辰", "zhouchen", "厨师长", "厨房"],
        "feishu_env": "FEISHU_USER_ID_ZHOUCHEN",
    },
    "yaowei": {
        "order": 9,
        "name": "尧维",
        "role": "行政采购 + 后勤",
        "title": "后勤采购工作台",
        "focus": ["行政采购", "装修", "园区后勤工具"],
        "layer": "support_layer",
        "unit": "行政采购 + 后勤",
        "aliases": ["尧维", "yaowei", "行政", "采购", "后勤"],
        "feishu_env": "FEISHU_USER_ID_YAOWEI",
    },
    "songxue": {
        "order": 10,
        "name": "宋雪",
        "role": "人事行政",
        "title": "人事行政工作台",
        "focus": ["考勤管理", "工资管理", "人事审批"],
        "layer": "support_layer",
        "unit": "人事行政",
        "aliases": ["宋雪", "songxue", "人事行政", "人事"],
        "feishu_env": "FEISHU_USER_ID_SONGXUE",
    },
    "yuchun": {
        "order": 11,
        "name": "于淳",
        "role": "食材采购 + 销售",
        "title": "食材采购 + 销售工作台",
        "focus": ["食材采购", "销售工作台"],
        "layer": "support_layer",
        "unit": "食材采购 + 销售",
        "aliases": ["于淳", "yuchun", "食材采购"],
        "feishu_env": "FEISHU_USER_ID_YUCHUN",
    },
}


ROLE_USER_ALIASES = {
    alias: key
    for key, person in OPERATING_CENTER_PEOPLE.items()
    for alias in [key, *person["aliases"]]
}


WORKSPACE_KEY_BY_ROLE = {
    person["role"]: key for key, person in OPERATING_CENTER_PEOPLE.items()
}
WORKSPACE_KEY_BY_ROLE.update(
    {
        "BOSS": "boss",
        "销售": "huanhuan",
        "六月": "june",
        "刘姐": "liujie",
        "娜娜": "nana",
        "行政采购": "yaowei",
        "产护支持": "chenchangyi",
        "餐饮/厨房": "zhouchen",
        "后勤保障": "yaowei",
    }
)
