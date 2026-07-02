param(
    [string]$EnvPath = "D:\凰家母婴空间\OMS_V1\config\secrets\feishu.env",
    [string]$AuditRoot = "D:\凰家母婴空间\OMS_V1\live_runtime\audit\feishu_mvp"
)

$ErrorActionPreference = "Stop"

function Read-DotEnv {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Env file not found: $Path"
    }
    $vars = @{}
    Get-Content -LiteralPath $Path -Encoding UTF8 | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
            $k, $v = $line.Split("=", 2)
            $vars[$k.Trim()] = $v.Trim()
        }
    }
    return $vars
}

function Invoke-Feishu {
    param(
        [string]$Method,
        [string]$Uri,
        [hashtable]$Headers,
        [object]$Body = $null
    )
    try {
        $jsonBody = $null
        if ($null -ne $Body) {
            $jsonBody = $Body | ConvertTo-Json -Depth 30 -Compress
        }
        $response = Invoke-RestMethod -Method $Method -Uri $Uri -Headers $Headers -ContentType "application/json; charset=utf-8" -Body $jsonBody -TimeoutSec 30
        return @{
            ok = $true
            status = "success"
            response = $response
            error = $null
        }
    } catch {
        $errorBody = $null
        if ($_.Exception.Response -and $_.Exception.Response.GetResponseStream()) {
            try {
                $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
                $errorBody = $reader.ReadToEnd()
            } catch {
                $errorBody = $null
            }
        }
        return @{
            ok = $false
            status = "failed"
            response = $errorBody
            error = $_.Exception.Message
        }
    }
}

function Get-Token {
    param([hashtable]$Vars)
    $body = @{
        app_id = $Vars["FEISHU_APP_ID"]
        app_secret = $Vars["FEISHU_APP_SECRET"]
    }
    $result = Invoke-Feishu -Method "Post" -Uri "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" -Headers @{} -Body $body
    if (-not $result.ok -or $result.response.code -ne 0) {
        throw "Failed to get tenant_access_token: $($result.response | ConvertTo-Json -Depth 10 -Compress)"
    }
    return $result.response.tenant_access_token
}

function Redact-Result {
    param([object]$Value)
    $json = $Value | ConvertTo-Json -Depth 50
    $json = $json -replace '("tenant_access_token"\s*:\s*")[^"]+', '$1***REDACTED***'
    $json = $json -replace '("app_secret"\s*:\s*")[^"]+', '$1***REDACTED***'
    return $json | ConvertFrom-Json
}

$vars = Read-DotEnv -Path $EnvPath
foreach ($required in @("FEISHU_APP_ID", "FEISHU_APP_SECRET")) {
    if ([string]::IsNullOrWhiteSpace($vars[$required])) {
        throw "$required is empty in $EnvPath"
    }
}

$runId = "feishu_mvp_" + (Get-Date -Format "yyyyMMdd_HHmmss")
$runDir = Join-Path $AuditRoot $runId
New-Item -ItemType Directory -Force -Path $runDir | Out-Null

$token = Get-Token -Vars $vars
$headers = @{ Authorization = "Bearer $token" }
$now = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss zzz")

$tests = @()

# 1. Bitable MVP write: create a temporary Base, create a table, then create one record.
$bitableRollback = @()
$bitableResult = @{
    name = "bitable_write"
    status = "failed"
    api_calls = @()
    rollback_plan = @()
}

$createAppBody = @{
    name = "OMS_MVP_房态测试_" + (Get-Date -Format "yyyyMMdd_HHmmss")
}
$createApp = Invoke-Feishu -Method "Post" -Uri "https://open.feishu.cn/open-apis/bitable/v1/apps" -Headers $headers -Body $createAppBody
$bitableResult.api_calls += @{
    step = "create_bitable_app"
    method = "POST"
    uri = "https://open.feishu.cn/open-apis/bitable/v1/apps"
    request = $createAppBody
    result = $createApp
}

$appToken = $null
if ($createApp.ok -and $createApp.response.code -eq 0) {
    $appToken = $createApp.response.data.app.app_token
    $bitableRollback += "Delete temporary Base manually if API delete is unavailable: app_token=$appToken"

    $createTableBody = @{
        table = @{
            name = "房态测试表"
            default_view_name = "默认视图"
            fields = @(
                @{ field_name = "客户"; type = 1 },
                @{ field_name = "状态"; type = 1 },
                @{ field_name = "房型"; type = 1 },
                @{ field_name = "时间"; type = 1 }
            )
        }
    }
    $createTable = Invoke-Feishu -Method "Post" -Uri "https://open.feishu.cn/open-apis/bitable/v1/apps/$appToken/tables" -Headers $headers -Body $createTableBody
    $bitableResult.api_calls += @{
        step = "create_table"
        method = "POST"
        uri = "https://open.feishu.cn/open-apis/bitable/v1/apps/$appToken/tables"
        request = $createTableBody
        result = $createTable
    }

    $tableId = $null
    if ($createTable.ok -and $createTable.response.code -eq 0) {
        $tableId = $createTable.response.data.table_id
        $recordBody = @{
            fields = @{
                "客户" = "李梅"
                "状态" = "OMS上线验证"
                "房型" = "标准房"
                "时间" = $now
            }
        }
        $createRecord = Invoke-Feishu -Method "Post" -Uri "https://open.feishu.cn/open-apis/bitable/v1/apps/$appToken/tables/$tableId/records" -Headers $headers -Body $recordBody
        $bitableResult.api_calls += @{
            step = "create_record"
            method = "POST"
            uri = "https://open.feishu.cn/open-apis/bitable/v1/apps/$appToken/tables/$tableId/records"
            request = $recordBody
            result = $createRecord
        }
        if ($createRecord.ok -and $createRecord.response.code -eq 0) {
            $recordId = $createRecord.response.data.record.record_id
            $bitableRollback += "Delete test record via DELETE /open-apis/bitable/v1/apps/$appToken/tables/$tableId/records/$recordId"
            $bitableResult.status = "success"
            $bitableResult.app_token = $appToken
            $bitableResult.table_id = $tableId
            $bitableResult.record_id = $recordId
        }
    }
}
$bitableResult.rollback_plan = $bitableRollback
$tests += $bitableResult

# 2. Feishu message MVP write. Requires FEISHU_TEST_CHAT_ID or FEISHU_TEST_OPEN_ID.
$messageResult = @{
    name = "message_send"
    status = "failed"
    api_calls = @()
    rollback_plan = @("A sent Feishu message cannot be fully deleted by OMS unless message delete permissions and message_id are available; record audit and send a cancellation notice if needed.")
}
$chatId = $vars["FEISHU_TEST_CHAT_ID"]
$openId = $vars["FEISHU_TEST_OPEN_ID"]
if (-not [string]::IsNullOrWhiteSpace($chatId) -or -not [string]::IsNullOrWhiteSpace($openId)) {
    $receiveType = if (-not [string]::IsNullOrWhiteSpace($chatId)) { "chat_id" } else { "open_id" }
    $receiveId = if ($receiveType -eq "chat_id") { $chatId } else { $openId }
    $messageBody = @{
        receive_id = $receiveId
        msg_type = "text"
        content = (@{ text = "OMS 飞书连接成功测试消息" } | ConvertTo-Json -Compress)
    }
    $sendMessage = Invoke-Feishu -Method "Post" -Uri "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=$receiveType" -Headers $headers -Body $messageBody
    $messageResult.api_calls += @{
        step = "send_message"
        method = "POST"
        uri = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=$receiveType"
        request = @{ receive_id_type = $receiveType; msg_type = "text"; content = "OMS 飞书连接成功测试消息" }
        result = $sendMessage
    }
    if ($sendMessage.ok -and $sendMessage.response.code -eq 0) {
        $messageResult.status = "success"
        $messageResult.message_id = $sendMessage.response.data.message_id
    }
} else {
    $messageResult.error = "Missing FEISHU_TEST_CHAT_ID or FEISHU_TEST_OPEN_ID in feishu.env; no safe recipient is available for a real message write."
}
$tests += $messageResult

# 3. Approval MVP write. Requires FEISHU_TEST_APPROVAL_CODE and FEISHU_TEST_APPROVER_USER_ID.
$approvalResult = @{
    name = "approval_create"
    status = "failed"
    api_calls = @()
    rollback_plan = @("Approval instances usually require cancellation through Feishu Approval APIs or manual approval backend handling; keep instance_code in audit log.")
}
$approvalCode = $vars["FEISHU_TEST_APPROVAL_CODE"]
$approverUserId = $vars["FEISHU_TEST_APPROVER_USER_ID"]
$applicantUserId = $vars["FEISHU_TEST_APPLICANT_USER_ID"]
if (-not [string]::IsNullOrWhiteSpace($approvalCode) -and -not [string]::IsNullOrWhiteSpace($approverUserId) -and -not [string]::IsNullOrWhiteSpace($applicantUserId)) {
    $form = @(
        @{ id = "amount"; type = "number"; value = "100" },
        @{ id = "description"; type = "textarea"; value = "财务测试审批：测试金额 100 元" }
    )
    $approvalBody = @{
        approval_code = $approvalCode
        user_id = $applicantUserId
        open_id = ""
        department_id = ""
        form = ($form | ConvertTo-Json -Depth 10 -Compress)
        node_approver_user_id_list = @($approverUserId)
    }
    $createApproval = Invoke-Feishu -Method "Post" -Uri "https://open.feishu.cn/open-apis/approval/v4/instances" -Headers $headers -Body $approvalBody
    $approvalResult.api_calls += @{
        step = "create_approval_instance"
        method = "POST"
        uri = "https://open.feishu.cn/open-apis/approval/v4/instances"
        request = @{
            approval_code = $approvalCode
            user_id = $applicantUserId
            form_summary = "测试金额 100 元"
            approver = $approverUserId
        }
        result = $createApproval
    }
    if ($createApproval.ok -and $createApproval.response.code -eq 0) {
        $approvalResult.status = "success"
        $approvalResult.instance_code = $createApproval.response.data.instance_code
    }
} else {
    $approvalResult.error = "Missing FEISHU_TEST_APPROVAL_CODE, FEISHU_TEST_APPLICANT_USER_ID, or FEISHU_TEST_APPROVER_USER_ID in feishu.env; cannot safely create a real approval instance."
}
$tests += $approvalResult

$summary = @{
    schema_version = "oms.v1.feishu_mvp_write_test"
    run_id = $runId
    created_at = $now
    app_id = $vars["FEISHU_APP_ID"]
    token_ok = $true
    tests = $tests
    overall_status = if (($tests | Where-Object { $_.status -eq "success" }).Count -eq 3) { "success" } else { "partial_or_failed" }
    audit_log = Join-Path $runDir "result.json"
}

$redacted = Redact-Result -Value $summary
$redacted | ConvertTo-Json -Depth 80 | Set-Content -LiteralPath (Join-Path $runDir "result.json") -Encoding UTF8
$redacted | ConvertTo-Json -Depth 80
