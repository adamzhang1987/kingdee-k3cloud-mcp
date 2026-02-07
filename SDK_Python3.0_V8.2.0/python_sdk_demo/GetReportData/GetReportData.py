#!/usr/bin/python
# -*- coding:UTF-8 -*-
import json
import logging

from k3cloud_webapi_sdk.main import K3CloudApiSdk
import time
import unittest


# 首先构造一个SDK实例
api_sdk = K3CloudApiSdk("https://apiexp.open.kingdee.com/k3cloud/")

# 然后初始化SDK，需指定相关参数，否则会导致SDK初始化失败而无法使用：

# 初始化方案一：Init初始化方法，使用conf.ini配置文件
# config_path:配置文件的相对或绝对路径，建议使用绝对路径
# config_node:配置文件中的节点名称
api_sdk.Init(config_path='../conf.ini', config_node='config')

para = {
    "parameters": [
        {
            "FORMID": "STK_StockQueryRpt",
            "FSCHEMEID": "6760e3871be1c2",
            "StartRow": "0",
            "Limit": "2000",
            "CurQueryId": "",
            "FieldKeys": ""
        }
    ]
}
url = "Kingdee.K3.SCM.WebApi.ServicesStub.StockReportQueryService.GetReportData,Kingdee.K3.SCM.WebApi.ServicesStub"
response = api_sdk.Execute(url,para)
print("分页报表：" + response)
