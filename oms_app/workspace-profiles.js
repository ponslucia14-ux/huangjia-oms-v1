(function initializeWorkspaceProfiles() {
  const item = (key, label, description, source, result, tone = "blue", access = "查看") => ({
    key,
    label,
    route: "workspace",
    target: label,
    description,
    source,
    result,
    tone,
    access,
  });

  const menu = (key, label, tone, children) => ({
    key,
    label,
    route: "workspace",
    target: label,
    tone,
    children,
  });

  const profile = (config) => Object.freeze({
    ...config,
    avatar: `./assets/${config.avatar}`,
    menuTree: Object.freeze(config.menuTree),
  });

  const profiles = {
    boss: profile({
      empId: "EMP001",
      name: "10晓磊",
      role: "主理办、销售总监、资金决策责任",
      avatar: "emp001-boss-avatar.jpg",
      headline: "先看全局，再处理必须由我决定的事项",
      guidance: "只看、判断、审批、授权和追溯，不替代其他岗位录入日常事实。",
      boundary: "不录入销售、财务、入住、房态和排房日常事实。",
      homeItems: ["今日必须处理", "经营快照", "风险提醒", "资金状态", "在住与房态"],
      menuTree: [
        menu("owner_home", "首页", "red", [
          item("owner_today_required", "今日必须处理", "集中查看必须本人审批、授权或裁决的事项。", "各岗位提交与系统异常", "形成待决策清单", "orange"),
          item("owner_snapshot", "经营快照", "查看销售、资金、运营、在住和房态的当前汇总。", "各岗位已确认事实", "形成经营判断", "green"),
          item("owner_home_risk", "风险提醒", "只呈现需要主理办介入的风险。", "异常与超时事项", "形成风险关注清单", "purple"),
          item("owner_fund_status", "资金状态", "查看收款、待收、待付和付款审批状态。", "刘晶录入、张敬东复核", "形成资金判断", "red"),
          item("owner_stay_room_status", "在住与房态", "查看刘芳羽确认的当前在住和当前房态。", "运营确认事实", "形成运营判断", "blue"),
        ]),
        menu("owner_decision", "待我决策", "orange", [
          item("owner_pending_approval", "待审批", "查看所有对外付款、客户退款和工资审批。", "业务责任人提交", "审批结果", "orange", "审批"),
          item("owner_pending_authorization", "待授权", "查看需要例外授权的经营事项。", "责任岗位提交", "授权结果", "purple", "授权"),
          item("owner_exception_decision", "经营异常待决策", "查看跨岗位冲突及重大异常。", "异常责任岗位", "经营决定", "red", "决策"),
          item("owner_overdue", "已超时事项", "查看超过处理时限且仍未闭环的事项。", "系统状态", "催办或经营指令", "teal", "决策"),
          item("owner_instructions", "我的经营指令", "查看本人已经形成的经营指令及执行状态。", "本人决策记录", "经营指令", "blue"),
        ]),
        menu("owner_status", "经营状态", "green", [
          item("owner_sales_status", "销售状态", "查看三名销售分别维护并由系统汇总的销售事实。", "杨欢欢、薛子渝、刘芳羽", "销售经营状态", "green"),
          item("owner_finance_status", "资金状态", "查看真实到账、付款、待收和待付。", "刘晶与张敬东", "资金经营状态", "red"),
          item("owner_operations_status", "运营状态", "查看入住、出馆、房态与运营确认。", "刘芳羽确认事实", "运营状态", "blue"),
          item("owner_stay_status", "在住状态", "查看当前真实在住，不包含计划和历史。", "当前在住", "在住状态", "teal"),
          item("owner_room_status", "房态状态", "查看当前真实房态。", "当前房态", "房态状态", "purple"),
          item("owner_people_status", "人员状态", "查看正式员工基础状态。", "宗惠维护资料", "人员状态", "orange"),
        ]),
        menu("owner_risk", "风险异常", "red", [
          item("owner_sales_risk", "销售风险", "查看销售归属、冲突和跨人员异常。", "三名销售与系统校验", "销售风险判断", "orange"),
          item("owner_finance_risk", "资金风险", "查看到账、付款、凭证和对账异常。", "财务业务数据", "资金风险判断", "red"),
          item("owner_allocation_risk", "排房风险", "查看未来排房冲突。", "刘芳羽排房信息", "排房风险判断", "purple"),
          item("owner_room_risk", "房态风险", "查看房态冲突、维修和停用异常。", "当前房态", "房态风险判断", "blue"),
          item("owner_service_risk", "服务异常", "查看需要主理办介入的服务异常。", "运营异常", "服务风险判断", "teal"),
          item("owner_people_risk", "人员异常", "查看正式员工人事异常。", "宗惠提交", "人员风险判断", "orange"),
          item("owner_system_risk", "系统异常", "查看影响业务使用的系统异常。", "系统运行状态", "系统风险判断", "red"),
        ]),
        menu("owner_trace", "决策追溯", "purple", [
          item("owner_my_approvals", "我的审批", "查看本人审批及原因。", "审批记录", "审批追溯", "orange"),
          item("owner_my_authorizations", "我的授权", "查看本人授权及期限。", "授权记录", "授权追溯", "purple"),
          item("owner_my_instructions", "我的经营指令", "查看经营指令与执行结果。", "经营指令记录", "经营追溯", "blue"),
          item("owner_exception_results", "异常处理结果", "查看异常最终处理结果。", "异常处理记录", "异常追溯", "green"),
          item("owner_key_sources", "关键数据来源", "查看关键数字的原始来源。", "业务来源记录", "数据追溯", "teal"),
          item("owner_history", "历史操作记录", "查看本人历史查看、审批和授权记录。", "审计与事件留痕", "操作追溯", "red"),
        ]),
      ],
    }),

    songxue: profile({
      empId: "EMP002", name: "宗惠", role: "人事", avatar: "emp002-zonghui-avatar.jpg",
      headline: "先看考勤与工资异常，再提交正式员工工资",
      guidance: "只负责人事基础、考勤导入、正式员工工资和人事事项。",
      boundary: "不建设培训、排班、缺班、招聘流程和复杂绩效系统。",
      homeItems: ["考勤导入状态", "考勤异常", "工资候选", "待提交事项"],
      menuTree: [
        menu("hr_home", "首页", "red", [item("hr_today", "今日人事事项", "查看今天必须处理的人事事项。", "员工资料与考勤状态", "今日待办", "orange"), item("hr_salary_state", "工资状态", "查看工资候选、审批、付款和核算状态。", "薪资业务数据", "工资状态", "green")]),
        menu("hr_people", "员工与薪资基础", "blue", [item("hr_roster", "员工资料", "维护正式员工基础资料。", "本人维护", "员工基础资料", "blue", "录入"), item("hr_salary_base", "基础薪资", "维护经过确认的正式员工基础薪资。", "人事资料", "工资计算依据", "purple", "录入")]),
        menu("hr_attendance", "钉钉考勤导入", "green", [item("hr_attendance_upload", "导入考勤", "导入钉钉考勤文件，系统自动识别。", "钉钉考勤文件", "考勤原始记录", "green", "导入"), item("hr_attendance_history", "导入记录", "查看历次导入结果和来源。", "考勤导入记录", "导入追溯", "teal")]),
        menu("hr_exception", "考勤异常", "orange", [item("hr_missing", "缺失记录", "核对缺卡和缺失日期。", "系统校验", "异常说明", "orange", "核对"), item("hr_conflict", "冲突记录", "核对重复或冲突的考勤。", "系统校验", "更正候选", "red", "核对")]),
        menu("hr_salary", "工资候选", "purple", [item("hr_salary_candidate", "工资候选明细", "查看系统根据基础薪资和考勤计算的候选结果。", "员工基础与考勤", "工资候选", "purple", "核对"), item("hr_salary_exception", "工资异常", "核对工资候选中的异常项。", "系统计算", "异常说明", "orange", "核对")]),
        menu("hr_submit", "提交与结果", "teal", [item("hr_submit_salary", "提交工资", "提交核对完成的正式员工工资。", "工资候选", "待10晓磊审批", "teal", "提交"), item("hr_salary_result", "工资结果", "查看审批、付款和核算结果。", "审批与财务结果", "薪资结果", "green")]),
      ],
    }),

    zhangjie: profile({
      empId: "EMP003", name: "张敬东", role: "会计", avatar: "emp003-zhangjingdong-avatar.jpg",
      headline: "先复核资金事实，再完成核算与结算",
      guidance: "不创建刘晶负责的原始收付款事实。",
      boundary: "不得自己录入后自己复核，不修改业务原始事实。",
      homeItems: ["待复核收款", "待复核付款", "凭证异常", "待核算工资"],
      menuTree: [
        menu("accounting_home", "首页", "red", [item("accounting_pending", "今日待复核", "查看今天等待复核的收付款。", "刘晶提交", "复核清单", "orange"), item("accounting_exception", "财务异常", "查看凭证、金额和账户差异。", "财务业务数据", "异常清单", "red")]),
        menu("accounting_receipt", "收款复核", "green", [item("accounting_receipt_pending", "待复核收款", "复核刘晶确认的真实到账。", "刘晶收款事实", "收款复核结果", "green", "复核"), item("accounting_receipt_history", "收款复核记录", "查看历史收款复核结果。", "复核记录", "收款追溯", "teal")]),
        menu("accounting_payment", "付款复核", "red", [item("accounting_payment_pending", "待复核付款", "复核已审批并由刘晶执行的付款。", "审批与付款凭证", "付款复核结果", "red", "复核"), item("accounting_refund", "客户退款复核", "复核已经主理办审批的客户退款。", "退款审批与凭证", "退款复核结果", "orange", "复核")]),
        menu("accounting_salary", "工资核算", "purple", [item("accounting_staff_salary", "正式员工工资", "核算正式员工工资付款。", "人事工资与付款结果", "工资核算", "purple", "核算"), item("accounting_caregiver_salary", "照护师工资", "核算照护师工资付款。", "照护师工资与付款结果", "工资核算", "blue", "核算")]),
        menu("accounting_close", "对账与结算", "blue", [item("accounting_reconcile", "账户对账", "核对账户流水与系统记录。", "账户与财务记录", "对账结果", "blue", "核对"), item("accounting_settle", "结算", "完成已复核业务的会计结算。", "复核结果", "结算结果", "green", "核算")]),
        menu("accounting_trace", "财务追溯", "teal", [item("accounting_source", "凭证与来源", "查看每笔资金的业务依据和凭证。", "业务来源与凭证", "来源追溯", "teal"), item("accounting_correction", "更正记录", "查看留痕更正的前后值和原因。", "更正记录", "更正追溯", "orange")]),
      ],
    }),

    liujie: profile({
      empId: "EMP004", name: "刘晶", role: "出纳", avatar: "emp004-liujing-avatar.jpg",
      headline: "把真实发生的每一笔收款和付款准确录入",
      guidance: "客户收款确认真实到账；所有付款必须先取得10晓磊审批。",
      boundary: "不得复核自己的记录，不得绕过审批付款。",
      homeItems: ["今日收款", "今日付款", "待补凭证", "被退回记录"],
      menuTree: [
        menu("cashier_home", "首页", "red", [item("cashier_today", "今日资金事项", "查看今日收款、付款和待处理事项。", "本人资金记录", "今日待办", "orange"), item("cashier_balance", "账户状态", "查看账户余额和日结状态。", "账户记录", "账户状态", "green")]),
        menu("cashier_receipt", "收款", "green", [item("cashier_receipt_new", "确认实际到账", "根据账户事实确认客户真实到账。", "销售付款申报与账户记录", "收款事实", "green", "录入"), item("cashier_receipt_records", "收款记录", "查看本人录入的收款及复核状态。", "收款事实", "收款追溯", "teal")]),
        menu("cashier_payment", "付款", "red", [item("cashier_payment_pending", "待执行付款", "只执行已经10晓磊审批的对外付款和客户退款。", "审批结果", "付款事实", "red", "付款"), item("cashier_payment_records", "付款记录", "查看付款、凭证和复核结果。", "付款事实", "付款追溯", "orange")]),
        menu("cashier_wage", "工资付款", "purple", [item("cashier_staff_wage", "正式员工工资", "执行已经审批的正式员工工资。", "工资审批结果", "工资付款事实", "purple", "付款"), item("cashier_caregiver_wage", "照护师工资", "执行已经审批的照护师工资。", "工资审批结果", "工资付款事实", "blue", "付款")]),
        menu("cashier_close", "日结", "blue", [item("cashier_daily_close", "提交日结", "录入账户余额并提交张敬东复核。", "当日收付款与账户余额", "日结候选", "blue", "提交"), item("cashier_close_state", "日结状态", "查看复核和更正结果。", "日结记录", "日结结果", "green")]),
        menu("cashier_records", "我的记录", "teal", [item("cashier_draft", "草稿", "查看尚未提交的资金草稿。", "本人草稿", "草稿清单", "teal"), item("cashier_returned", "被退回", "查看退回原因并补充资料。", "张敬东复核结果", "补充记录", "orange", "补充")]),
      ],
    }),

    yaowei: profile({
      empId: "EMP005", name: "石昊盺", role: "行政总监", avatar: "emp005-shihaoxin-avatar.jpg",
      headline: "行政采购与照护师工资分区处理",
      guidance: "上传真实依据、核对系统识别结果并提交，不执行付款和核算。",
      boundary: "行政采购和照护师工资不得混用，不建设复杂物资管理。",
      homeItems: ["行政采购待办", "照护师工资异常", "待提交事项", "被退回记录"],
      menuTree: [
        menu("admin_home", "首页", "red", [item("admin_procurement_today", "行政采购待办", "查看采购凭证识别和待提交事项。", "本人采购资料", "采购待办", "orange"), item("admin_caregiver_today", "照护师工资待办", "查看服务数据和工资候选异常。", "照护师服务依据", "工资待办", "purple")]),
        menu("admin_procurement", "行政采购", "blue", [item("admin_receipt_upload", "上传采购凭证", "拍照或上传网购订单、微信支付或线下采购凭证。", "本人上传", "采购草稿与识别候选", "blue", "录入"), item("admin_receipt_check", "核对识别结果", "核对并修改名称、金额、日期、供应商和类别。", "系统识别结果", "采购候选", "green", "核对"), item("admin_procurement_submit", "提交审批", "提交核对完成的行政采购。", "采购候选", "待10晓磊审批", "orange", "提交")]),
        menu("admin_caregiver", "照护师工资", "purple", [item("admin_caregiver_service", "服务依据", "查看实际服务天数和基础依据。", "运营服务事实", "工资依据", "blue"), item("admin_caregiver_candidate", "工资候选", "核对系统计算的工资、补贴和扣款。", "服务依据与薪资规则", "工资候选", "purple", "核对"), item("admin_caregiver_submit", "提交审批", "提交核对完成的照护师工资。", "工资候选", "待10晓磊审批", "orange", "提交")]),
        menu("admin_results", "提交与结果", "green", [item("admin_pending_result", "待处理", "查看审批、付款和核算进度。", "流程状态", "处理状态", "green"), item("admin_returned", "被退回", "查看退回原因并补充资料。", "审批或核算反馈", "补充记录", "orange", "补充")]),
        menu("admin_records", "我的记录", "teal", [item("admin_procurement_records", "采购记录", "查看本人行政采购历史。", "采购记录", "采购追溯", "teal"), item("admin_caregiver_records", "工资记录", "查看照护师工资历史。", "工资记录", "工资追溯", "purple")]),
      ],
    }),

    huanhuan: profile({
      empId: "EMP006", name: "杨欢欢", role: "销售", avatar: "emp006-yanghuanhuan-avatar.jpg",
      headline: "先处理本人接待与新签，再查看本人客户状态",
      guidance: "只维护本人销售事实，不确认真实到账。",
      boundary: "不查看其他销售私有客户，不承担全体销售数据确认。",
      homeItems: ["我的接待", "待录新签", "我的客户", "入住计划"],
      menuTree: [
        menu("sales_home", "首页", "red", [item("sales_today", "今日销售事项", "查看本人今日接待、新签和待补资料。", "本人销售事实", "今日待办", "orange"), item("sales_payment_state", "收款确认状态", "查看刘晶对本人客户到账的确认结果。", "财务确认结果", "收款状态", "green")]),
        menu("sales_reception", "接待登记", "blue", [item("sales_reception_new", "登记接待", "轻量记录本人实际接待。", "本人业务动作", "接待事实", "blue", "录入"), item("sales_reception_records", "接待记录", "查看本人接待记录和状态。", "本人接待事实", "接待追溯", "teal")]),
        menu("sales_signing", "新签客户录入", "green", [item("sales_contract_new", "录入合同", "客户签约并发生首笔付款后录入合同和付款信息。", "本人签约资料", "合同与付款申报", "green", "录入"), item("sales_signing_draft", "待补资料", "查看未完整的新签资料。", "本人草稿", "补充记录", "orange", "补充")]),
        menu("sales_customers", "我的客户", "purple", [item("sales_customer_list", "客户列表", "查看本人名下客户。", "本人销售事实", "客户列表", "purple"), item("sales_customer_detail", "客户详情", "查看合同、付款确认和入住计划。", "销售与财务确认结果", "客户详情", "blue")]),
        menu("sales_orders", "我的签单", "orange", [item("sales_contracts", "我的合同", "查看本人合同和状态。", "本人合同", "合同列表", "orange"), item("sales_results", "我的业绩", "查看系统根据本人事实计算的业绩。", "系统汇总", "销售结果", "green")]),
        menu("sales_stay_plan", "入住计划", "teal", [item("sales_future_stay", "待入住客户", "查看本人客户的合同入住计划。", "合同入住计划", "待入住清单", "teal"), item("sales_plan_change", "计划变化", "查看已经由运营确认的计划变化。", "运营确认结果", "计划状态", "blue")]),
      ],
    }),

    yuchun: profile({
      empId: "EMP007", name: "薛子渝", role: "销售兼食材采购", avatar: "emp007-xueziyu-avatar.jpg",
      headline: "销售与食材采购分区处理",
      guidance: "本人销售事实和食材采购事实各录一次，系统自动关联财务。",
      boundary: "不确认真实到账，不执行付款，不替厨师长建设厨房生产管理。",
      homeItems: ["我的销售待办", "食材采购待办", "待提交凭证", "被退回记录"],
      menuTree: [
        menu("dual_home", "首页", "red", [item("dual_sales_today", "我的销售待办", "查看本人接待、新签和客户事项。", "本人销售事实", "销售待办", "orange"), item("dual_food_today", "食材采购待办", "查看采购单、凭证和付款状态。", "本人采购事实", "采购待办", "green")]),
        menu("dual_sales", "我的销售", "blue", [item("dual_sales_customers", "我的客户", "查看本人客户和合同状态。", "本人销售事实", "客户列表", "blue"), item("dual_sales_results", "我的销售结果", "查看系统计算的本人业绩。", "系统汇总", "销售结果", "green")]),
        menu("dual_reception", "接待登记", "teal", [item("dual_reception_new", "登记接待", "轻量记录本人实际接待。", "本人业务动作", "接待事实", "teal", "录入"), item("dual_reception_records", "接待记录", "查看本人接待历史。", "本人接待事实", "接待追溯", "blue")]),
        menu("dual_signing", "新签客户录入", "purple", [item("dual_contract_new", "录入合同", "客户签约并发生首笔付款后录入合同和付款信息。", "本人签约资料", "合同与付款申报", "purple", "录入"), item("dual_signing_pending", "待补资料", "补充本人未完整的新签资料。", "本人草稿", "补充记录", "orange", "补充")]),
        menu("dual_food", "食材采购", "green", [item("dual_food_upload", "上传采购凭证", "拍照或上传手写采购单和支付凭证。", "本人上传", "采购草稿与识别候选", "green", "录入"), item("dual_food_check", "核对识别结果", "逐项修改食材、数量、单位、单价、金额和供应商。", "系统识别结果", "采购候选", "blue", "核对"), item("dual_food_arrival", "确认到货", "记录真实到货情况。", "采购订单", "到货事实", "teal", "确认"), item("dual_food_submit", "提交审批", "提交采购订单和凭证。", "采购候选", "待10晓磊审批", "orange", "提交")]),
        menu("dual_records", "我的记录", "orange", [item("dual_sales_records", "销售记录", "查看本人销售历史。", "销售记录", "销售追溯", "orange"), item("dual_food_records", "采购记录", "查看采购、审批、付款和核算状态。", "采购与财务结果", "采购追溯", "green")]),
      ],
    }),

    june: profile({
      empId: "EMP008", name: "刘芳羽", role: "店总兼销售", avatar: "emp008-liufangyu-avatar.jpg",
      headline: "先看全馆客户与房间，再确认运营事实",
      guidance: "确认入住、出馆、房态和未来排房；销售区只处理本人销售。",
      boundary: "不直接改财务到账，不替管家重复录入已有客户资料。",
      homeItems: ["今日入住与出馆", "待确认运营事实", "房态与排房", "我的销售待办"],
      menuTree: [
        menu("store_home", "首页", "red", [item("store_today", "今日运营事项", "查看入住、出馆、房态、排房和异常。", "运营提交与当前事实", "运营待办", "orange"), item("store_sales_today", "我的销售待办", "查看本人销售事项。", "本人销售事实", "销售待办", "green")]),
        menu("store_customers", "全馆客户", "blue", [item("store_customer_list", "客户列表", "查看全馆客户及当前状态。", "销售、管家与运营事实", "全馆客户视图", "blue"), item("store_customer_change", "客户变化", "查看今日新增、入住、变更和出馆。", "业务状态变化", "客户变化", "teal")]),
        menu("store_stay", "入住与在住", "green", [item("store_stay_pending", "待确认入住", "确认尚丽娜提交的实际到馆资料。", "管家提交", "当前在住候选", "green", "确认"), item("store_stay_current", "当前在住", "查看当前真实在住。", "运营确认事实", "当前在住", "blue"), item("store_stay_change", "入住变更", "确认延住、调房等运营变化。", "运营变化提交", "入住变更事实", "purple", "确认"), item("store_stay_checkout", "出馆确认", "确认实际出馆并推动房间进入后续状态。", "管家出馆资料", "出馆事实", "orange", "确认")]),
        menu("store_allocation", "未来排房", "purple", [item("store_allocation_overview", "未来排房总览", "查看未来房间走势和空房区间。", "排房记录", "未来排房视图", "purple"), item("store_customer_plan", "客户入住计划", "查看合同入住计划，不直接形成当前在住。", "合同入住计划", "计划清单", "blue"), item("store_room_adjustment", "房间调整", "记录调整房间、原因和时间。", "排房安排", "调整记录", "orange", "录入"), item("store_allocation_conflict", "冲突检查", "查看房间与日期冲突。", "系统校验", "冲突清单", "red")]),
        menu("store_room", "房态管理", "teal", [item("store_room_overview", "房间总览", "查看42间房当前真实状态。", "当前房态", "房间总览", "teal"), item("store_room_confirm", "房态确认", "确认现场房态变化。", "现场状态提交", "当前房态", "green", "确认"), item("store_room_exception", "房间异常", "处理维修、停用和冲突。", "运营异常", "房间处理结果", "red", "处理")]),
        menu("store_confirm", "运营确认", "orange", [item("store_pending_confirm", "待确认事项", "集中查看管家提交的入住、出馆和房间现场资料。", "尚丽娜提交", "运营确认结果", "orange", "确认"), item("store_exception", "运营异常", "处理或上报运营异常。", "运营异常", "异常处理结果", "red", "处理")]),
        menu("store_sales", "我的销售", "blue", [item("store_my_customers", "我的客户", "查看本人客户。", "本人销售事实", "客户列表", "blue"), item("store_my_contracts", "我的合同", "查看本人合同和收款确认状态。", "本人合同与财务确认", "合同列表", "purple"), item("store_my_results", "我的销售结果", "查看系统计算的本人业绩。", "系统汇总", "销售结果", "green")]),
      ],
    }),

    nana: profile({
      empId: "EMP009", name: "尚丽娜", role: "管家", avatar: "emp009-shanglina-avatar.jpg",
      headline: "维护当前在住资料，并在出馆前补齐必要客户资料",
      guidance: "已有资料自动带出，只补现场最少必要信息。",
      boundary: "不修改合同金额，不确认收款，不发布当前入住和当前房态。",
      homeItems: ["当前在住", "待补客户资料", "出馆前待补全", "已提交记录"],
      menuTree: [
        menu("butler_home", "首页", "red", [item("butler_today", "今日资料事项", "查看当前在住、待补和出馆前资料。", "当前在住与本人提交", "今日待办", "orange"), item("butler_returned", "被退回记录", "查看刘芳羽退回原因并补充。", "运营确认反馈", "补充清单", "red", "补充")]),
        menu("butler_stay", "当前在住", "blue", [item("butler_stay_list", "在住客户", "查看当前真实在住客户。", "刘芳羽确认事实", "在住列表", "blue"), item("butler_stay_detail", "在住资料", "查看并补充最少必要现场资料。", "已有客户资料与现场信息", "在住资料提交", "teal", "录入")]),
        menu("butler_customer", "客户资料", "green", [item("butler_customer_required", "必要客户资料", "补充系统尚未具备的最少必要资料。", "系统自动带出与现场信息", "客户资料", "green", "录入"), item("butler_customer_draft", "资料草稿", "继续填写自动保存的草稿。", "本人草稿", "资料草稿", "orange", "补充")]),
        menu("butler_checkout", "出馆前补全", "purple", [item("butler_checkout_pending", "待补全客户", "查看准备出馆且资料未完整的客户。", "运营计划与资料检查", "待补清单", "purple"), item("butler_checkout_submit", "提交出馆资料", "提交最少必要出馆资料给刘芳羽确认。", "现场事实", "出馆确认候选", "orange", "提交")]),
        menu("butler_history", "已出馆记录", "teal", [item("butler_checkout_records", "出馆客户记录", "查看本人维护过的已出馆资料。", "出馆确认结果", "客户资料库记录", "teal"), item("butler_submission_records", "我的提交", "查看提交、确认和退回状态。", "本人提交记录", "提交追溯", "blue")]),
      ],
    }),

    chenchangyi: profile({
      empId: "EMP010", name: "陈晶辉", role: "产护部总监", avatar: "emp010-chenjinghui-avatar.jpg", readOnly: true,
      headline: "提前看入住变化，清楚在住客户产护相关信息",
      guidance: "第一版为纯只读工作台。",
      boundary: "只允许查看、筛选、搜索、打开详情和返回，不录入、不确认、不反馈、不处理、不上报。",
      homeItems: ["未来七天入住", "当前在住", "套餐与产康套餐", "今日变化"],
      menuTree: [
        menu("care_home", "首页", "red", [item("care_today", "今日变化", "查看今天入住、出馆和资料变化。", "运营确认事实", "变化清单", "orange"), item("care_package", "套餐概览", "查看当前在住客户套餐和产康套餐。", "合同与运营确认事实", "套餐概览", "green")]),
        menu("care_future", "未来7天入住", "blue", [item("care_future_list", "入住名单", "查看未来七天计划入住客户。", "合同入住计划", "入住名单", "blue"), item("care_future_search", "筛选与搜索", "按日期、客户和套餐筛选。", "合同入住计划", "筛选结果", "teal")]),
        menu("care_current", "当前在住", "green", [item("care_current_list", "在住名单", "查看当前真实在住客户。", "当前在住", "在住名单", "green"), item("care_current_filter", "套餐筛选", "按套餐和产康套餐筛选。", "当前在住与合同套餐", "筛选结果", "blue")]),
        menu("care_detail", "客户详情", "purple", [item("care_customer_detail", "产护相关详情", "查看客户套餐、产康套餐和必要说明。", "已确认业务资料", "只读详情", "purple"), item("care_source", "资料来源", "查看信息由哪个岗位确认。", "来源记录", "来源详情", "teal")]),
        menu("care_changes", "今日变化", "orange", [item("care_change_list", "变化记录", "查看今日入住、出馆和套餐资料变化。", "业务变化记录", "变化清单", "orange"), item("care_change_detail", "变化详情", "打开单条变化的只读详情。", "变化记录", "只读详情", "blue")]),
      ],
    }),

    zhouchen: profile({
      empId: "EMP011", name: "周志朋", role: "厨师长", avatar: "emp011-zhouzhipeng-avatar.jpg", readOnly: true,
      headline: "提前看入住变化，清楚在住客户餐食要求",
      guidance: "第一版为纯只读工作台。",
      boundary: "只允许查看、筛选、搜索、打开详情和返回，不录入、不确认、不反馈、不处理、不上报。",
      homeItems: ["未来七天入住", "当前在住", "忌口与特殊餐食", "今日变化"],
      menuTree: [
        menu("kitchen_home", "首页", "red", [item("kitchen_today", "今日变化", "查看今天入住、出馆和餐食资料变化。", "运营确认事实", "变化清单", "orange"), item("kitchen_meal_overview", "餐食要求概览", "查看当前在住客户的套餐餐食要求。", "合同与现场资料", "餐食概览", "green")]),
        menu("kitchen_future", "未来7天入住", "blue", [item("kitchen_future_list", "入住名单", "查看未来七天计划入住客户。", "合同入住计划", "入住名单", "blue"), item("kitchen_future_filter", "套餐筛选", "按日期和套餐筛选。", "合同入住计划", "筛选结果", "teal")]),
        menu("kitchen_current", "当前在住", "green", [item("kitchen_current_list", "在住名单", "查看当前真实在住客户。", "当前在住", "在住名单", "green"), item("kitchen_current_filter", "餐食筛选", "按套餐、忌口和特殊要求筛选。", "当前在住与餐食资料", "筛选结果", "blue")]),
        menu("kitchen_requirements", "餐食要求", "purple", [item("kitchen_package_meal", "套餐餐食信息", "查看客户套餐对应餐食信息。", "合同套餐", "餐食详情", "purple"), item("kitchen_dietary", "忌口与特殊餐食", "查看刘芳羽确认的忌口和特殊餐食要求。", "管家提交、店总确认", "餐食要求详情", "orange")]),
        menu("kitchen_changes", "今日变化", "orange", [item("kitchen_change_list", "变化记录", "查看今日入住、出馆和餐食资料变化。", "业务变化记录", "变化清单", "orange"), item("kitchen_change_detail", "变化详情", "打开单条变化的只读详情。", "变化记录", "只读详情", "blue")]),
      ],
    }),
  };

  window.OMS_WORKSPACE_PROFILES = Object.freeze(profiles);
})();
