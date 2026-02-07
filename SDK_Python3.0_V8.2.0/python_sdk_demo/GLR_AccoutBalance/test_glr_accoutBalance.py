#!/usr/bin/python
# -*- coding:GBK -*-
import json

from k3cloud_webapi_sdk.main import K3CloudApiSdk
import time
import unittest
import logging

# 首先构造一个SDK实例
api_sdk = K3CloudApiSdk("https://apiexp.open.kingdee.com/k3cloud/")

# 然后初始化SDK，需指定相关参数，否则会导致SDK初始化失败而无法使用：

# 初始化方案一：Init初始化方法，使用conf.ini配置文件
# config_path:配置文件的相对或绝对路径，建议使用绝对路径
# config_node:配置文件中的节点名称
api_sdk.Init(config_path='../conf.ini', config_node='config')


# 初始化方案二（新增）：InitConfig初始化方法，直接传参，不使用配置文件
# acct_id:第三方系统登录授权的账套ID,user_name:第三方系统登录授权的用户,app_id:第三方系统登录授权的应用ID,app_sec:第三方系统登录授权的应用密钥
# server_url:k3cloud环境url(仅私有云环境需要传递),lcid:账套语系(默认2052),org_num:组织编码(启用多组织时配置对应的组织编码才有效)
# api_sdk.InitConfig('62e25034af8811', 'Administrator', '231784_3d9r4dHJ5OgZ4aUJwe6rTxSMVjTdWooF', 'aae9d547ffde46fe9236fdea40472854')

# 此处仅构造保存接口的部分字段数据示例，使用时请参考WebAPI具体接口的实际参数列表


def Check_response(res):
    res = json.loads(res)
    if res["Result"]["IsSuccess"]:
        return True
    else:
        logging.error(res)
        return False


def gl_accountbalance_GetSysReportData(**kwargs):
    """
    科目余额表 (GL_RPT_AccountBalance) 的查询报表数据功能
    :param kwargs:  替换para中参数，示例：
    :return:
    """
    para = {
        "FieldKeys": "FBALANCEID,FBALANCENAME,FACCTTYPE,FACCTGROUP,FDETAILNUMBER,FDETAILNAME,FCyName",
        "SchemeId": "97ffa1271acc4846b209ea05ac8dec9c",
        "StartRow": 0,
        "Limit": 2000,
        "IsVerifyBaseDataField": "false",
        "Model": {
            "FACCTBOOKID": {
                "FNumber": "001"
            },
            "FCURRENCY": "1",
            "FSTARTYEAR": "2021",
            "FSTARTPERIOD": "12",
            "FENDYEAR": "2021",
            "FBALANCELEVEL": "1",
            "FENDPERIOD": "12",
            "FFORBIDBALANCE": True,
            "FBALANCEZERO": True,
            "FPERIODNOBALANCE": True,
            "FYEARNOBALANCE": True,
        },
        "PkEntryIds": []
    }
    if kwargs:
        para.update(kwargs)
    response = api_sdk.getSysReportData("GL_RPT_AccountBalance", para)
    print("科目余额表报表查询接口：", response)
    return Check_response(response)


class glAccountBalanceTestCase(unittest.TestCase):
    def testb_voucher_Save(self):
        self.assertTrue(gl_accountbalance_GetSysReportData())


if __name__ == '__main__':
    unittest.main()