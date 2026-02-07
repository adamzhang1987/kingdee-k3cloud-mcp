#!/usr/bin/python
# -*- coding:utf-8 -*-
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

# 初始化方案二（新增）：InitConfig初始化方法，直接传参，不使用配置文件
# acct_id:第三方系统登录授权的账套ID,user_name:第三方系统登录授权的用户,app_id:第三方系统登录授权的应用ID,app_sec:第三方系统登录授权的应用密钥
# server_url:k3cloud环境url(仅私有云环境需要传递),lcid:账套语系(默认2052),org_num:组织编码(启用多组织时配置对应的组织编码才有效)
# api_sdk.InitConfig('62e25034af8811', 'Administrator', '231784_3d9r4dHJ5OgZ4aUJwe6rTxSMVjTdWooF', 'aae9d547ffde46fe9236fdea40472854')

# 此处仅构造保存接口的部分字段数据示例，使用时请参考WebAPI具体接口的实际参数列表
current_time = time.strftime('%Y%m%d%H%M%S', time.localtime())
save_data = {
    "FCreateOrgId": {"FNumber": 100},
    "FUserOrgId": {"FNumber": 100},
    "FNumber": "xtwl" + current_time + "10001",
    "FName": "物料名称" + current_time + "10001"
}
FNumber = "xtwl" + current_time + "10001"


def Check_response(res):
    res = json.loads(res)
    if res["Result"]["ResponseStatus"]["IsSuccess"]:
        return True
    else:
        logging.error(res)
        return False


def material_Save(**kwargs):
    """
    本接口用于实现物料 (BD_MATERIAL) 的保存功能
    :param kwargs:  替换para中参数，示例： Model = {"FCreateOrgId": {"FNumber": 100},"FUserOrgId": {"FNumber": 100},"FNumber": "Webb10001","FName": "物料名称10001"}
    :return:
    """
    para = {
        "NeedUpDateFields": [],
        "NeedReturnFields": [],
        "IsDeleteEntry": "True",
        "SubSystemId": "",
        "IsVerifyBaseDataField": "False",
        "IsEntryBatchFill": "True",
        "ValidateFlag": "True",
        "NumberSearch": "True",
        "IsAutoAdjustField": "False",
        "InterationFlags": "",
        "IgnoreInterationFlag": "",
        "IsControlPrecision": "False",
        "Model": {}
    }
    if kwargs:
        para.update(kwargs)
    response = api_sdk.Save("BD_Material", para)
    print("物料保存接口：", response)
    if Check_response(response):
        res = json.loads(response)
        materialid = res["Result"]["Id"]
        return Check_response(response), materialid
    return False, ""


def material_Submit(**kwargs):
    """
    本接口用于实现物料 (BD_MATERIAL) 的提交功能
    :param kwargs:  替换para中参数，示例：   Numbers = []
    :return:
    """
    para = {"CreateOrgId": 0, "Numbers": [], "Ids": "", "SelectedPostId": 0,
            "NetworkCtrl": "",
            "IgnoreInterationFlag": "",
            }
    if kwargs:
        para.update(kwargs)
    response = api_sdk.Submit("BD_Material", para)
    print("物料提交接口：", response)
    return Check_response(response)


def material_Audit(**kwargs):
    """
    本接口用于实现物料 (BD_MATERIAL) 的审核功能
    :param kwargs:  替换para中参数，示例：   Numbers = []
    :return:
    """
    para = {"CreateOrgId": 0, "Numbers": [], "Ids": "", "SelectedPostId": 0,
            "NetworkCtrl": "",
            "IgnoreInterationFlag": "",
            "IsVerifyProcInst": "",
            }
    if kwargs:
        para.update(kwargs)
    response = api_sdk.Audit("BD_Material", para)
    print("物料审核接口：", response)
    return Check_response(response)


def material_FlexSave(**kwargs):
    """
    本接口用于实现弹性域保存功能
    输入参数
    :param kwargs:  替换para中参数，示例：
    :return:
    """
    para = {"Model":[{"FFLEX8":{"FNumber": kwargs["FNumber"]}}]}
    response = api_sdk.FlexSave("BD_FLEXITEMDETAILV",para)
    print("弹性域保存接口：", response)
    return Check_response(response)


class MaterialTestCase(unittest.TestCase):

    def testa_material_Save(self):
        result = material_Save(Model=save_data)
        self.assertTrue(result[0])

    def testb_material_Submit(self):
        self.assertTrue(material_Submit(Numbers=[FNumber]))

    def testc_material_Audit(self):
        self.assertTrue(material_Audit(Numbers=[FNumber]))

    def testd_material_flexsave(self):
        self.assertTrue(material_FlexSave(FNumber=FNumber))



if __name__ == '__main__':
    unittest.main()
