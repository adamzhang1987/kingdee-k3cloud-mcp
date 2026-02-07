#!/usr/bin/python
# -*- coding:GBK -*-
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


def material_ExecuteBillQuery(**kwargs):
    """
    本接口用于实现物料 (BD_MATERIAL) 的单据查询功能
    :param kwargs:  替换para中参数，示例：FieldKeys=“Fname",Limit=1000
    :return:
    """
    para = {
        "FormId": "BD_MATERIAL",
        "FieldKeys": "FName,FNumber",
        "FilterString": "'FNumber'=""",
        "OrderString": "",
        "TopRowCount": 100,
        "StartRow": 0,
        "Limit": 2000,
        "SubSystemId": ""
    }
    if kwargs:
        para.update(kwargs)
    response = api_sdk.ExecuteBillQuery(para)
    print("物料单据查询接口：" + response)
    res = json.loads(response)
    if len(res) > 0:
        return True
    return False


def material_BillQuery(**kwargs):
    """
    本接口用于实现物料 (BD_MATERIAL) 的单据查询(json)功能
    :param kwargs:  替换para中参数，示例：FieldKeys=“Fname",Limit=1000
    :return:
    """
    para = {
        "FormId": "BD_MATERIAL",
        "FieldKeys": "FName,FNumber,FCreateOrgId,FUseOrgId,",
        "FilterString": "'FNumber'=""",
        "OrderString": "",
        "TopRowCount": 100,
        "StartRow": 0,
        "Limit": 2000,
        "SubSystemId": ""
    }
    if kwargs:
        para.update(kwargs)
    response = api_sdk.BillQuery(para)
    print("物料单据查询接口：" + response)
    res = json.loads(response)
    if len(res) > 0:
        return True
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


def material_Allocate(**kwargs):
    """
    本接口用于实现物料 (BD_MATERIAL) 的分配功能
    :param kwargs:  替换para中参数，示例：   PkIds ="" ,TOrgIds=""
    :return:
    """
    para = {"PkIds": "", "TOrgIds": ""}
    if kwargs:
        para.update(kwargs)
    response = api_sdk.Allocate("BD_Material", para)
    print("物料分配接口：", response)
    return Check_response(response)


def material_cancelAllocate(**kwargs):
    """
    本接口用于实现物料 (BD_MATERIAL) 的取消分配功能
    :param kwargs:  替换para中参数，示例：   PkIds ="" ,TOrgIds=""
    :return:
    """

    para = {"PkIds": "", "TOrgIds": ""}
    if kwargs:
        para.update(kwargs)
    response = api_sdk.cancelAllocate("BD_Material", para)
    print("物料取消分配接口：", response)
    return Check_response(response)


def material_UnAudit(**kwargs):
    """
    本接口用于实现物料 (BD_MATERIAL) 的反审核功能
    输入参数
    :param kwargs:  替换para中参数，示例：   Numbers = []
    :return:
    """
    para = {"PkIds": "", "TOrgIds": ""}
    if kwargs:
        para.update(kwargs)
    response = api_sdk.UnAudit("BD_Material", para)
    print("物料反审核接口：", response)
    return Check_response(response)


def material_attachmentUpload(**kwargs):
    """
    本接口用于实现物料 (BD_MATERIAL) 的上传功能
    输入参数
    :param kwargs:  替换para中参数，示例：   InterId="", BillNO="
    :return:
    """
    para = {"FileName": "1016.txt",
            "FEntryKey": "",
            "FormId": "BD_MATERIAL",
            "IsLast": True,
            "InterId": "",
            "BillNO": "",
            "AliasFileName": "test",
            "SendByte": "6L+Z5piv5rWL6K+V5paH5Lu25ZKMYmFzZTY05a2X56ym5Liy5LqS6L2s"
            }
    if kwargs:
        para.update(kwargs)
    response = api_sdk.attachmentUpload(para)
    print("物料附件上传接口：", response)
    if Check_response(response):
        res = json.loads(response)
        fileid = res["Result"]["FileId"]
        return Check_response(response), fileid
    return False, ""


def material_attachmentDownLoad(**kwargs):
    """
    本接口用于实现物料 (BD_MATERIAL) 的下载功能
    输入参数
    :param kwargs:  替换para中参数，示例：   Numbers = []
    :return:
    """
    para = {"FileId": "", "StartIndex": 0}
    if kwargs:
        para.update(kwargs)
    response = api_sdk.attachmentDownLoad(para)
    print("物料附件下载接口：", response)
    return Check_response(response)


def material_ExcuteOperation(type, **kwargs):
    """

    :param type: Forbid：禁用 Enable：反禁用
    :param kwargs:
    :return:
    """

    para = {"CreateOrgId": 0, "Numbers": [], "Ids": "", "PkEntryIds": [],
            "NetworkCtrl": "",
            "IgnoreInterationFlag": "",
            }
    if kwargs:
        para.update(kwargs)
    response = api_sdk.ExcuteOperation("BD_Material", type, para)
    print(f"物料{type}接口：", response)
    return Check_response(response)


def material_View(**kwargs):
    """
    本接口用于实现物料 (BD_MATERIAL) 的反查看功能
    输入参数
    :param kwargs:  替换para中参数，示例：   Number = web0002
    :return:
    """
    para = {"CreateOrgId": 0, "Number": "", "Id": "", "IsSortBySeq": "false", }
    if kwargs:
        para.update(kwargs)
    response = api_sdk.View("BD_Material", para)
    print("物料反查看接口：", response)
    return Check_response(response)


def material_Delete(**kwargs):
    """
    本接口用于实现物料 (BD_MATERIAL) 的删除功能
    输入参数
    :param kwargs:  替换para中参数，示例：   Number = web0002
    :return:
    """
    para = {"CreateOrgId": 0, "Numbers": [], "Ids": "", "NetworkCtrl": ""}
    if kwargs:
        para.update(kwargs)
    response = api_sdk.Delete("BD_Material", para)
    print("物料删除接口：", response)
    return Check_response(response)


def material_GroupSave(**kwargs):
    """
    本接口用于实现物料 (BD_MATERIAL) 的分组保存功能
    输入参数
    :param kwargs:  替换para中参数，示例：   FNumber = "",  FName=""
    :return:
    """
    para = {
        "GroupFieldKey": "",
        "GroupPkId": 0,
        "FParentId": 0,
        "FNumber": "",
        "FName": "",
        "FDescription": ""
    }
    if kwargs:
        para.update(kwargs)
    response = api_sdk.GroupSave("BD_Material", para)
    print("物料分组保存接口：", response)
    if Check_response(response):
        res = json.loads(response)
        groupid = res["Result"]["ResponseStatus"]["SuccessEntitys"][0]["Id"]
        return Check_response(response), groupid
    return False, ""


def material_QueryGroupInfo(**kwargs):
    """
    本接口用于实现物料 (BD_MATERIAL) 的分组查询功能
    输入参数
    :param kwargs:  替换para中参数，示例：   GroupPkIds=''
    :return:
    """
    para = {
        "FormId": "BD_MATERIAL",
        "GroupFieldKey": "FMaterialGroup",
        "GroupPkIds": "",
        "Ids": ""
    }
    if kwargs:
        para.update(kwargs)
    response = api_sdk.QueryGroupInfo(para)
    print("物料分组查询接口：", response)
    return Check_response(response)


def material_GroupDelete(**kwargs):
    """
    本接口用于实现物料 (BD_MATERIAL) 的分组删除功能
    输入参数
    :param kwargs:  替换para中参数，示例：   GroupPkIds = ''
    :return:
    """
    para = {
        "FormId": "BD_MATERIAL",
        "GroupFieldKey": "FMaterialGroup",
        "GroupPkIds": "",
    }
    if kwargs:
        para.update(kwargs)
    response = api_sdk.GroupDelete(para)
    print("物料分组删除接口：", response)
    return Check_response(response)


def material_SwitchOrg(**kwargs):
    """
    本接口用于实现物料 (BD_MATERIAL) 的切换组织功能
    输入参数
    :param kwargs:  替换para中参数，示例：   OrgNumber = ''
    :return:
    """
    para = { "OrgNumber": ""}
    if kwargs:
        para.update(kwargs)
    response = api_sdk.SwitchOrg(para)
    print("物料切换组织接口：", response)
    return Check_response(response)


def material_SendMsg(**kwargs):
    """
    本接口用于实现发送消息功能
    输入参数
    :param kwargs:  替换para中参数，示例：
    :return:
    """
    para = {"Model":[{"FTitle":"我是标题","FContent":"我是内容","FReceivers":"demo","FType":"1"}]}
    if kwargs:
        para.update(kwargs)
    response = api_sdk.SendMsg(para)
    print("发送消息接口：", response)
    return Check_response(response)


def material_BatchSave(n):
    """
    本接口用于实现物料 (BD_MATERIAL) 的批量保存功能
    输入参数
    :param kwargs:  替换para中参数，示例：
    :return:
    """

    modellist = []
    for i in range(n):
        current_time = time.strftime('%Y%m%d%H%M%S', time.localtime())
        model_data = {
            "FCreateOrgId": {"FNumber": 100},
            "FUserOrgId": {"FNumber": 100},
            "FNumber": "xtwl" + current_time + "10001",
            "FName": "物料名称" + current_time + "10001"
        }
        modellist.append(model_data)
        time.sleep(1)


    para = {
        "NumberSearch": "true",
        "ValidateFlag": "true",
        "IsDeleteEntry": "true",
        "IsEntryBatchFill": "true",
        "NeedUpDateFields": [],
        "NeedReturnFields": [],
        "SubSystemId": "",
        "InterationFlags": "",
        "Model": modellist,
        "BatchCount": 0,
        "IsVerifyBaseDataField": "false",
        "IsAutoAdjustField": "false",
        "IgnoreInterationFlag": "false",
        "IsControlPrecision": "false",
        "ValidateRepeatJson": "false"
    }
    response = api_sdk.BatchSave("BD_Material", para)
    print("物料批量保存接口：", response)
    return Check_response(response)






class MaterialTestCase(unittest.TestCase):
    materialid = ""
    fileid = ""
    groupid = ""

    def testa_material_Save(self):
        result = material_Save(Model=save_data)
        self.assertTrue(result[0])
        MaterialTestCase.materialid = result[1]

    def testb_material_Submit(self):
        self.assertTrue(material_Submit(Numbers=[FNumber]))

    def testc_material_Audit(self):
        self.assertTrue(material_Audit(Numbers=[FNumber]))

    def testd_material_Allocate(self):
        self.assertTrue(material_Allocate(PkIds=MaterialTestCase.materialid, TOrgIds="100002"))

    def teste_material_cancelAllocate(self):
        self.assertTrue(material_cancelAllocate(PkIds=MaterialTestCase.materialid, TOrgIds="100002"))

    def testf_material_UnAudit(self):
        self.assertTrue(material_UnAudit(Numbers=[FNumber]))

    def testg_material_attachmentUpload(self):
        result = material_attachmentUpload(InterId=MaterialTestCase.materialid, BillNO=FNumber)
        self.assertTrue(result[0])
        MaterialTestCase.fileid = result[1]

    def testh_material_attachmentDownLoad(self):
        self.assertTrue(material_attachmentDownLoad(FileId=MaterialTestCase.fileid))

    def testi_material_ExcuteOperation(self):
        self.assertTrue(material_ExcuteOperation("Forbid", Numbers=[FNumber]))

    def testj_material_ExcuteOperation(self):
        self.assertTrue(material_ExcuteOperation("Enable", Numbers=[FNumber]))

    def testk_material_View(self):
        self.assertTrue(material_View(Number=FNumber))

    def testl_material_ExecuteBillQuery(self):
        self.assertTrue(material_ExecuteBillQuery(Limit=1000, FilterString="FNumber=" + "\'" + FNumber + "\'"))

    def testl_material_BillQuery(self):
        self.assertTrue(material_BillQuery(Limit=1000, FilterString="FNumber=" + "\'" + FNumber + "\'"))

    def testm_material_Delete(self):
        self.assertTrue(material_Delete(Numbers=FNumber))

    def testn_material_GroupSave(self):
        result = material_GroupSave(FNumber=FNumber, FName=FNumber)
        self.assertTrue(result[0])
        MaterialTestCase.groupid = result[1]

    def testo_material_QueryGroupInfo(self):
        self.assertTrue(material_QueryGroupInfo(GroupPkIds=MaterialTestCase.groupid))

    def testp_material_GroupDelete(self):
        self.assertTrue(material_GroupDelete(GroupPkIds=MaterialTestCase.groupid))

    def testq_material_SwitchOrg(self):
        self.assertTrue(material_SwitchOrg(OrgNumber=200))

    #切换组织后重新切换回来
    def testr_material_SwitchOrg(self):
        self.assertTrue(material_SwitchOrg(OrgNumber=100))

    def testr_material_SendMsg(self):
        self.assertTrue(material_SendMsg())

    def tests_material_material_BatchSave(self):
        self.assertTrue(material_BatchSave(2))


if __name__ == '__main__':
    unittest.main()
