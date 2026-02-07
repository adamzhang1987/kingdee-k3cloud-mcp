# 金蝶云星空 Python3.0 SDK 开发指南

本文档为使用金蝶云星空Python SDK的开发者提供指导说明。

## 快速开始

### 1. 安装SDK

SDK包位于项目中：`./python_sdk_v8.2.0/kingdee.cdp.webapi.sdk-8.2.0-py3-none-any.whl`

安装命令：

```bash
# 在项目根目录下执行
pip install ./python_sdk_v8.2.0/kingdee.cdp.webapi.sdk-8.2.0-py3-none-any.whl
```

### 2. 配置文件

配置文件示例（`conf.ini`）：

```ini
[config]
# 第三方系统登录授权的账套ID（即open.kingdee.com网站的第三方系统登录授权中的数据中心标识）
X-KDApi-AcctID = 2020******
# 第三方系统登录授权的用户（用于调用接口的用户）
X-KDApi-UserName = ***
# 第三方系统登录授权的应用ID（即金蝶云星空产品中的第三方系统登录授权中的应用ID）
X-KDApi-AppID = 21***_w53uT***
# 第三方系统登录授权的应用密钥（即金蝶云星空产品中的第三方系统登录授权中的应用密钥）
X-KDApi-AppSec = ******
# 服务Url地址,以k3cloud/结尾
X-KDApi-ServerUrl = https://******/k3cloud/
# 账套语系，默认2052
X-KDApi-LCID = 2052
# 组织编码，启用多组织时配置对应的组织编码才有效
# X-KDApi-OrgNum = 100
# 允许的最大连接延时，单位为秒
# X-KDApi-ConnectTimeout = 120
# 允许的最大读取延时，单位为秒
# X-KDApi-RequestTimeout = 120
# 若使用代理，配置此参数
# X-KDApi-Proxy = http://localhost:8888/
```

> 配置文件示例位于：`./python_sdk_demo/conf.ini`

### 3. 初始化SDK

SDK提供两种初始化方式：

#### 方式一：使用配置文件

```python
from k3cloud_webapi_sdk.main import K3CloudApiSdk

# 构造SDK实例
api_sdk = K3CloudApiSdk()

# 使用配置文件初始化
# config_path: 配置文件的相对或绝对路径，建议使用绝对路径
# config_node: 配置文件中的节点名称
api_sdk.Init(config_path='conf.ini', config_node='config')
```

#### 方式二：直接传参（推荐用于云环境）

```python
from k3cloud_webapi_sdk.main import K3CloudApiSdk

# 构造SDK实例并传入server_url
api_sdk = K3CloudApiSdk("https://apiexp.open.kingdee.com/k3cloud/")

# 直接传参初始化
api_sdk.InitConfig(
    acct_id='账套ID',      # 第三方系统登录授权的账套ID
    user_name='用户名',    # 第三方系统登录授权的用户
    app_id='应用ID',       # 第三方系统登录授权的应用ID
    app_sec='应用密钥',    # 第三方系统登录授权的应用密钥
    server_url='',         # k3cloud环境url(仅私有云环境需要传递)
    lcid=2052,             # 账套语系(默认2052)
    org_num=''             # 组织编码(启用多组织时配置)
)
```

## 核心接口说明

### 基础数据接口

#### 1. Save - 保存接口

```python
save_data = {
    "Model": {
        "FCreateOrgId": {"FNumber": 100},
        "FUserOrgId": {"FNumber": 100},
        "FNumber": "MATERIAL001",
        "FName": "物料名称001"
    }
}

result = api_sdk.Save("BD_Material", save_data)
```

#### 2. BatchSave - 批量保存接口

```python
save_data = {
    "Model": [
        {
            "FCreateOrgId": {"FNumber": 100},
            "FUserOrgId": {"FNumber": 100},
            "FNumber": "MATERIAL001",
            "FName": "物料名称001"
        },
        {
            "FCreateOrgId": {"FNumber": 100},
            "FUserOrgId": {"FNumber": 100},
            "FNumber": "MATERIAL002",
            "FName": "物料名称002"
        }
    ]
}

result = api_sdk.BatchSave("BD_Material", save_data)
```

#### 3. Submit - 提交接口

```python
result = api_sdk.Submit("BD_Material", {
    "Numbers": ["MATERIAL001"]
})
```

#### 4. Audit - 审核接口

```python
result = api_sdk.Audit("BD_Material", {
    "Numbers": ["MATERIAL001"]
})
```

#### 5. UnAudit - 反审核接口

```python
result = api_sdk.UnAudit("BD_Material", {
    "Numbers": ["MATERIAL001"]
})
```

#### 6. Delete - 删除接口

```python
result = api_sdk.Delete("BD_Material", {
    "Numbers": ["MATERIAL001"]
})
```

### 查询接口

#### 7. View - 查看接口

```python
result = api_sdk.View("BD_Material", {
    "Number": "MATERIAL001"
})
```

#### 8. ExecuteBillQuery - 单据查询接口

```python
result = api_sdk.ExecuteBillQuery({
    "FormId": "BD_MATERIAL",
    "FieldKeys": "FName,FNumber",
    "FilterString": "FNumber like 'MAT%'",
    "TopRowCount": 100
})
```

#### 9. BillQuery - 单据查询接口（JSON格式）

```python
result = api_sdk.BillQuery({
    "FormId": "BD_MATERIAL",
    "FieldKeys": "FName,FNumber,FCreateOrgId,FUseOrgId",
    "FilterString": "FNumber like 'MAT%'",
    "Limit": 2000
})
```

### 操作接口

#### 10. ExcuteOperation - 执行操作（禁用/反禁用等）

```python
# 禁用
result = api_sdk.ExcuteOperation("BD_Material", "Forbid", {
    "Numbers": ["MATERIAL001"]
})

# 反禁用
result = api_sdk.ExcuteOperation("BD_Material", "Enable", {
    "Numbers": ["MATERIAL001"]
})
```

### 多组织相关接口

#### 11. Allocate - 分配接口

```python
result = api_sdk.Allocate("BD_Material", {
    "PkIds": "104378",
    "TOrgIds": "100002",
    "IsAutoSubmitAndAudit": "false"
})
```

#### 12. cancelAllocate - 取消分配接口

```python
result = api_sdk.cancelAllocate("BD_Material", {
    "PkIds": "104378",
    "TOrgIds": "100002"
})
```

#### 13. SwitchOrg - 切换组织接口

```python
result = api_sdk.SwitchOrg({
    "OrgNumber": "100"
})
```

### 分组相关接口

#### 14. GroupSave - 分组保存接口

```python
result = api_sdk.GroupSave("BD_Material", {
    "GroupFieldKey": "FMaterialGroup",
    "FNumber": "GROUP001",
    "FName": "物料分组001"
})
```

#### 15. QueryGroupInfo - 查询分组信息

```python
result = api_sdk.QueryGroupInfo({
    "FormId": "BD_MATERIAL",
    "GroupFieldKey": "FMaterialGroup",
    "GroupPkIds": "123456"
})
```

#### 16. GroupDelete - 删除分组

```python
result = api_sdk.GroupDelete({
    "FormId": "BD_MATERIAL",
    "GroupFieldKey": "FMaterialGroup",
    "GroupPkIds": "123456"
})
```

### 附件相关接口

#### 17. attachmentUpload - 附件上传

```python
result = api_sdk.attachmentUpload({
    "FileName": "test.txt",
    "FormId": "BD_MATERIAL",
    "InterId": "物料内码",
    "BillNO": "物料编码",
    "AliasFileName": "别名",
    "SendByte": "base64编码的文件内容"
})
```

#### 18. attachmentDownLoad - 附件下载

```python
result = api_sdk.attachmentDownLoad({
    "FileId": "文件ID",
    "StartIndex": 0
})
```

### 弹性域接口

#### 19. FlexSave - 弹性域保存

```python
result = api_sdk.FlexSave("BD_FLEXITEMDETAILV", {
    "Model": [{
        "FFLEX8": {"FNumber": "弹性域值"}
    }]
})
```

### 报表接口

#### 20. getSysReportData - 获取系统报表数据

```python
result = api_sdk.getSysReportData("GL_RPT_AccountBalance", {
    "FieldKeys": "FBALANCEID,FBALANCENAME,FACCTTYPE",
    "SchemeId": "报表方案ID",
    "StartRow": 0,
    "Limit": 2000,
    "Model": {
        "FACCTBOOKID": {"FNumber": "001"},
        "FCURRENCY": "1",
        "FSTARTYEAR": "2021",
        "FSTARTPERIOD": "12"
    }
})
```

### 消息接口

#### 21. SendMsg - 发送消息

```python
result = api_sdk.SendMsg({
    "Model": [{
        "FTitle": "消息标题",
        "FContent": "消息内容",
        "FReceivers": "接收人用户名",
        "FType": "1"
    }]
})
```

### 通用接口

#### 22. Execute - 执行自定义接口

```python
url = "Kingdee.K3.SCM.WebApi.ServicesStub.StockReportQueryService.GetReportData,Kingdee.K3.SCM.WebApi.ServicesStub"
para = {
    "parameters": [{
        "FORMID": "STK_StockQueryRpt",
        "FSCHEMEID": "方案ID",
        "StartRow": "0",
        "Limit": "2000"
    }]
}
result = api_sdk.Execute(url, para)
```

## 示例代码

完整的示例代码位于 `./python_sdk_demo/` 目录：

- `BD_MATERIAL/` - 物料相关接口示例
  - `test_bd_material.py` - 物料完整接口测试
  - `test_bd_materialflex.py` - 弹性域保存示例
- `GLR_AccoutBalance/` - 科目余额报表查询示例
- `GetReportData/` - 自定义报表数据获取示例
- `zrun/` - 批量测试运行脚本

## 响应处理

所有接口返回JSON格式字符串，建议使用以下方式处理：

```python
import json

def check_response(response):
    """检查接口响应是否成功"""
    res = json.loads(response)

    # 标准接口响应格式
    if "Result" in res and "ResponseStatus" in res["Result"]:
        return res["Result"]["ResponseStatus"]["IsSuccess"]

    # 部分接口响应格式
    if "Result" in res and "IsSuccess" in res["Result"]:
        return res["Result"]["IsSuccess"]

    return False

# 使用示例
response = api_sdk.Save("BD_Material", save_data)
if check_response(response):
    print("操作成功")
    result = json.loads(response)
    # 获取返回的ID等信息
    entity_id = result["Result"]["Id"]
else:
    print("操作失败")
    print(response)
```

## 参数说明

### 常用表单ID（FormId）

- `BD_MATERIAL` - 物料
- `BD_Customer` - 客户
- `BD_Supplier` - 供应商
- `SAL_SaleOrder` - 销售订单
- `PUR_PurchaseOrder` - 采购订单
- `STK_InStock` - 入库单
- `STK_OutStock` - 出库单
- `GL_VOUCHER` - 凭证

更多表单ID请参考产品中WebAPI的示例说明或[Open API官网](https://openapi.open.kingdee.com/)。

### 常用操作类型（Operation）

- `Forbid` - 禁用
- `Enable` - 反禁用（启用）
- `Submit` - 提交
- `Audit` - 审核
- `UnAudit` - 反审核
- `Close` - 关闭
- `UnClose` - 反关闭

## 最佳实践

1. **使用配置文件管理凭证**
   - 将敏感信息（AppID、AppSec）存储在配置文件中
   - 不要将配置文件提交到版本控制系统

2. **错误处理**
   - 始终检查接口返回状态
   - 记录错误日志便于排查问题

3. **批量操作**
   - 对于大量数据，使用BatchSave等批量接口提高效率
   - 注意批量操作的数量限制

4. **超时设置**
   - 根据实际网络情况调整ConnectTimeout和RequestTimeout
   - 默认120秒，可根据需要调整

5. **组织切换**
   - 多组织环境下，注意及时切换到正确的组织
   - 使用SwitchOrg接口切换组织上下文

## 参考资源

- **Open API官网**: [https://openapi.open.kingdee.com/](https://openapi.open.kingdee.com/)
- **星空知识社区**: [https://vip.kingdee.com/knowledge/specialDetail/229961573895771136](https://vip.kingdee.com/knowledge/specialDetail/229961573895771136)
- **产品内WebAPI示例**: 登录系统后，在菜单中找到"WebAPI"即可查看

## 故障排查

### 常见问题

1. **SDK初始化失败**
   - 检查配置文件路径是否正确
   - 确认配置参数（AcctID、UserName、AppID、AppSec）是否正确

2. **接口调用返回401错误**
   - 检查AppID和AppSec是否正确
   - 确认用户在系统中是否有相应权限

3. **接口调用超时**
   - 调整ConnectTimeout和RequestTimeout参数
   - 检查网络连接状态

4. **数据保存失败**
   - 检查必填字段是否完整
   - 确认字段值格式是否正确
   - 查看返回的错误信息定位具体问题

---

*最后更新: 2026-02-07*
