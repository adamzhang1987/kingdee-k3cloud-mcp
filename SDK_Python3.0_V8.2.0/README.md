# Python3.0版SDK说明

## 下载并安装k3cloud_webapi_sdk

使用pip安装指令格式：

```bash
pip install {后缀为.whl的SDK包文件的本地完整目录}
```

例如：

```bash
pip install F:\Python\kingdee.cdp.webapi.sdk-8.0.4-py3-none-any.whl
```

## 配置文件参数说明

以`conf.ini`命令配置文件名称为例，节点为`config`（配置参数名称不区分大小写）：

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
# X-KDApi-ServerUrl = https://******/k3cloud/
# 账套语系，默认2052
# X-KDApi-LCID = 2052
# 组织编码，启用多组织时配置对应的组织编码才有效
# X-KDApi-OrgNum = 100
# 允许的最大连接延时，单位为秒
# X-KDApi-ConnectTimeout = 120
# 允许的最大读取延时，单位为秒
# X-KDApi-RequestTimeout = 120
# 若使用代理，配置此参数
# X-KDApi-Proxy = http://localhost:8888/
```

> **说明**：2021-08-31已更新，新增支持使用参数初始化方法，可不依赖配置文件。（见示例工程）

## 使用k3cloud_webapi_sdk的示例

### 接口通用示例参考

所有接口的参数格式，均可参考产品中WebAPI的示例说明，或者登陆OPEN API官方网站查看API文档：[https://openapi.open.kingdee.com/](https://openapi.open.kingdee.com/)

### 前提：初始化SDK

通用部分，初始化一次即可，保存好SDK示例，可反复使用直接调用接口：

```python
#!/usr/bin/python
# -*- coding:UTF-8 -*-

from k3cloud_webapi_sdk.main import K3CloudApiSdk

# 首先构造一个SDK实例
api_sdk = K3CloudApiSdk()

# 然后初始化SDK，需指定相关参数，否则会导致SDK初始化失败而无法使用：

# 初始化方案一：Init初始化方法，使用conf.ini配置文件
# config_path:配置文件的相对或绝对路径，建议使用绝对路径
# config_node:配置文件中的节点名称
# api_sdk.Init(config_path='conf.ini', config_node='config')

# 初始化方案二（新增）：InitConfig初始化方法，直接传参，不使用配置文件
# acct_id:第三方系统登录授权的账套ID
# user_name:第三方系统登录授权的用户
# app_id:第三方系统登录授权的应用ID
# app_sec:第三方系统登录授权的应用密钥
# server_url:k3cloud环境url(仅私有云环境需要传递)
# lcid:账套语系(默认2052)
# org_num:组织编码(启用多组织时配置对应的组织编码才有效)
api_sdk.InitConfig('', '', '', '')
```

### 保存接口

```python
# 此处仅构造保存接口的部分字段数据示例，使用时请参考WebAPI具体接口的实际参数列表
current_time = time.strftime('%Y%m%d%H%M%S', time.localtime())
save_data = {"Model": {
    "FCreateOrgId": {"FNumber": 100},
    "FUserOrgId": {"FNumber": 100},
    "FNumber": "Webb" + current_time + "10001",
    "FName": "物料名称" + current_time + "10001"
}}

# 调用sdk中的保存接口
print(api_sdk.Save("BD_Material", save_data))
```

### 批量保存接口

```python
def gen_seq(loop_count):
    # 此方法仅为生成物料编码的演示数据而写，使用时以实际数据为准
    prefix = time.strftime('%Y%m%d%H%M%S', time.localtime())
    list_num = []
    for index in range(0, loop_count):
        list_num.append(prefix + str(10000 + index + 1))
    return list_num

count = 10
list_seq = gen_seq(count)
# 构造批量保存接口的部分字段数据，使用时请参考WebAPI具体接口的实际参数列表
list_data = []
for i in range(0, count):
    list_data.append({
        "FCreateOrgId": {"FNumber": 100},
        "FUserOrgId": {"FNumber": 100},
        "FNumber": "Webb" + list_seq[i],
        "FName": "物料名称-" + list_seq[i]
    })
save_data = {"Model": list_data}

# 调用sdk中的批量保存接口（同步模式）
print(api_sdk.BatchSave("BD_Material", save_data))
```

### 单据查询接口

```python
# 比如查询"物料"(BD_MATERIAL)单据中的"名称"和"编码"字段
print(api_sdk.ExecuteBillQuery(
    {"FormId": "BD_MATERIAL", "FieldKeys": "FName,FNumber", "FilterString": "FNumber like 'Webb%'", "TopRowCount": 5}))
```

### 查看接口

```python
# 比如查询"物料"(BD_MATERIAL)单据中的"名称"和"编码"字段
print(api_sdk.View("BD_MATERIAL", {"Number": "Webb2019101514453410001"}))
```

### 提交接口

```python
print(api_sdk.Submit("BD_MATERIAL", {"Numbers": ["Webb2019101514453410001"]}))
```

### 审核接口

```python
print(api_sdk.Audit("BD_MATERIAL", {"Numbers": ["Webb2019101514453410001"]}))
```

### 反审核接口

```python
print(api_sdk.UnAudit("BD_MATERIAL", {"Numbers": ["Webb2019101514453410001"]}))
```

### 删除接口

```python
print(api_sdk.Delete("BD_MATERIAL", {"Numbers": ["Webb2019101514453410001"]}))
```

### 操作接口（以禁用、反禁用为例）

```python
# 禁用
print(api_sdk.ExcuteOperation("BD_MATERIAL", "Forbid", {"Numbers": ["Webb2019101514453410002"]}))

# 反禁用
# print(api_sdk.ExcuteOperation("BD_MATERIAL", "Enable", {"Numbers": ["Webb2019101514453410002"]}))
```

### 分配接口（需启用多组织）

```python
print(api_sdk.Allocate("BD_MATERIAL", {"PkIds": 104378, "TOrgIds": "", "IsAutoSubmitAndAudit": "false"}))
```

## 更多资源

### 更多接口

请参考SDK文档中的完整接口列表。

### 更多知识

请前往**星空知识社区OpenAPI学习**：
- 知识社区：[https://vip.kingdee.com/knowledge/specialDetail/229961573895771136](https://vip.kingdee.com/knowledge/specialDetail/229961573895771136)
- Open API官网：[https://openapi.open.kingdee.com/](https://openapi.open.kingdee.com/)
