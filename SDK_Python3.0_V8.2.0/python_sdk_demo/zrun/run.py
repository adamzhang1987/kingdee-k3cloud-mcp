import unittest
import os
def allcas():
    case_dir = "../"
    print(os.path.abspath(case_dir))
    testcase = unittest.TestSuite()
    discover = unittest.defaultTestLoader.discover(case_dir,pattern="test*.py",top_level_dir=None)


    for test_suit in discover:    #循环添加到测试套件中
        for test_case in test_suit:
            testcase.addTest(test_case)
    print(testcase)
    return testcase

if __name__ == '__main__':
    runer = unittest.TextTestRunner()
    runer.run(allcas())

