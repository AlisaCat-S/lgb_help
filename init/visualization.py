import time
import traceback
import ddddocr
import numpy as np
import base64
import random

from config.url_conf import URLS
from utils.http_utils import HTTPClient
from utils.find_ansers import FindAnswers
from utils.webdriver import WebDriver
from selenium.webdriver.common.by import By
from config.LgbConfig import CHROME_CHROME_PATH, CHROME_TIMEOUT
from config.LgbConfig import MIN_TIME, MAX_TIME
from config.LgbConfig import CORRECT_ANSWER_NUM
from config.LgbConfig import ONLY_QUERYINFO, QUERYINFO_WRITE_FILE, QUERYINFO_WRITE_FILE_PATH


class Visualization:
    def __init__(self) -> None:
        self.user = ""
        self.passwd = ""
        self.http_client = HTTPClient()
        self.find_answers = FindAnswers()
        self.question_answer_postion = {}
        self.answer_ques_num = 0
        for i in range(26):
            self.question_answer_postion[chr(65+i)] = i
        self.result_dict = None

    def wait_get_url_done(self):
        js = "return document.readyState"
        start_time = time.time()
        while time.time() - start_time <= CHROME_TIMEOUT:
            # loading   interactive  complete
            res = self.browser.execute_script(js)
            if 'complete' == res:
                break
        time.sleep(2)  # 必须等待html源码完成更新在读取,希望更改

    def exec_script_click(self, obj_elem, pos):
        time.sleep(0.1)
        try:
            if pos >= 0:
                self.browser.execute_script(
                    "arguments[0].click();", obj_elem[pos])
            else:
                self.browser.execute_script("arguments[0].click();", obj_elem)
        except:
            traceback.print_exc()

    def start(self):
        self.browser.get(URLS['web_home']['req_url'])
        self.wait_get_url_done()
        self.browser.find_element(By.CLASS_NAME, "challenge-btn").click()
        self.wait_get_url_done()
        tip = '今日挑战次数已用尽，请明天再来哦~'
        html = self.browser.page_source
        if tip in html:
            print(tip)
            return False
        start_answering = self.browser.find_element(
            By.CLASS_NAME, "start-answering")
        self.browser.execute_script(
            "arguments[0].click();", start_answering)  # 开始答题
        self.wait_get_url_done()
        return True

    def auth(self):
        def getVcode(base64img):
            base64img = base64img.split(",")[1]
            image = base64.b64decode(base64img, altchars=None, validate=False)
            nparr = np.fromstring(image, np.uint8)
            frame = nparr.tobytes()

            ocr = ddddocr.DdddOcr(old=True, show_ad=False)
            res = ocr.classification(frame)
            return res
        self.browser.get(URLS['web_login']['req_url'])
        self.wait_get_url_done()
        self.browser.find_element(By.CLASS_NAME, "phoneNumber").find_element(
            By.CLASS_NAME, "el-input__inner").send_keys(self.user)
        self.browser.find_element(By.CLASS_NAME, "password ").find_element(
            By.CLASS_NAME, "el-input__inner").send_keys(self.passwd)
        base64img = self.browser.find_element(By.CLASS_NAME, "imgCode").find_element(
            By.XPATH, ".//img").get_attribute("src")
        vcode = getVcode(base64img)
        self.browser.find_element(By.CLASS_NAME, "vCode").find_element(
            By.CLASS_NAME, "el-input__inner").send_keys(vcode)
        self.browser.find_element(By.CLASS_NAME, "signIn").click()
        self.wait_get_url_done()

    def login(self):
        check_txt = ['挑战答题', '姓名', '我的积分', '手机号码']
        tip = '您目前处于未登录状态, 请重新登录'
        login_sucess_txt = '登录成功'
        re_try = URLS['web_login']['re_try']

        self.browser.delete_all_cookies()
        while re_try > 0:
            self.auth()
            html = self.browser.page_source
            if self.browser.current_url == URLS['web_home']['req_url'] and \
                all(key in html for key in check_txt) and \
                    tip not in html:
                print("登录成功")
                re_try = -1
                break
            re_try -= 1
            print("尝试登录中:", URLS['web_login']['re_try'] - re_try)

    def judge_finish(self) -> bool:
        if self.answer_ques_num >= CORRECT_ANSWER_NUM:
            print("======已达设定最大答题数目,答题结束======")
            return True
        check_txt = '恭喜您！答对15道题目'
        tip = '每天只能挑战一次哦~'
        check_elements = ['question-type', 'topic',
                          'question-text', 'questionBox', 'question-answer']
        html = self.browser.page_source
        if check_txt in html:
            print("<------恭喜您，满分！！！------>")
            return True
        if not all([True if item in html else False for item in check_elements]):
            print("======服务器返回异常,账号答题结束======")
            return True
        question_type, topic, question_answer = self.find_answer_element()
        if not all([question_type, topic, question_answer]):
            print(tip)
            return True
        return False

    def find_answer_element(self):
        question_type = self.browser.find_element(
            By.CLASS_NAME, "question-type").find_element(By.XPATH, ".//span").text
        topic = self.browser.find_element(By.CLASS_NAME, "topic").find_element(
            By.CLASS_NAME, "question-text").text
        question_answer = self.browser.find_element(By.CLASS_NAME, "questionBox").find_element(
            By.CLASS_NAME, "question-answer").find_elements(By.CLASS_NAME, "foo-answer")
        return question_type, topic, question_answer

    def answer(self):
        if self.browser.current_url != URLS['web_answer']['req_url']:
            self.browser.get(URLS['web_answer']['req_url'])
            self.wait_get_url_done()
        while not self.judge_finish():
            question_type, topic, question_answer = self.find_answer_element()
            quesid_, answer_ = self.get_correct_answer(
                question_type, topic, question_answer)

            if question_type == '单选题' or question_type == '判断题':
                self.exec_script_click(
                    question_answer, self.question_answer_postion.get(answer_[0]))
            elif question_type == '多选题':
                for v in answer_:
                    self.exec_script_click(
                        question_answer, self.question_answer_postion.get(v))
                    time.sleep(0.1)
                submit = self.browser.find_element(By.CLASS_NAME, "section-group").find_element(
                    By.CLASS_NAME, "submission").find_element(By.XPATH, ".//a")
                self.exec_script_click(submit, -1)
            self.wait_get_url_done()
            tips = self.browser.find_element(By.CLASS_NAME, "Tips").find_element(
                By.CLASS_NAME, "Continue").find_element(By.XPATH, ".//a")
            self.exec_script_click(tips, -1)
            self.wait_get_url_done()
            self.answer_ques_num += 1  # 答题数+1
            time.sleep(random.randint(MIN_TIME, MAX_TIME))

    def get_correct_answer(self, question_type, topic, question_answer):
        quesid_ = ''
        answer_ = []

        if self.judge_finish():
            return quesid_, answer_

        quesTypeStr = question_type
        quesid_, content = topic.split('.')
        answerOptions = [key.text.replace('\n', '').split('.')[-1]
                         for key in question_answer]
        answer_, _ = self.find_answers.get_result(
            quesTypeStr, content, answerOptions)
        print("running:", quesid_, quesTypeStr,
              content, answerOptions, answer_)
        if all([quesid_, answer_]):
            return quesid_, answer_
        else:
            retry_flag = True
            while retry_flag:
                retry_flag = False
                t_str = input("没有找到答案>>>>>>>>>>>>手动输入答案:").upper()
                if not t_str:
                    retry_flag = True
                for v in t_str:
                    if ord(v)-64 > len(answerOptions):
                        retry_flag = True
            return quesid_, list(t_str)

    def query_account_info(self):
        self.browser.get(URLS['web_home']['req_url'])
        self.wait_get_url_done()
        check_elements = ['challenge-box',
                          'challenge-info', 'competition-rank']
        html = self.browser.page_source
        if not all([True if item in html else False for item in check_elements]):
            print("======无数据，无法查询信息======")
            return  # 无数据
        self.browser.find_element(By.CLASS_NAME, 'competition-rank').click()
        self.wait_get_url_done()
        challenge_infos = self.browser.find_element(
            By.CLASS_NAME, "challenge-box").find_elements(By.CLASS_NAME, "challenge-info")
        memberName = '姓名:' + \
            challenge_infos[0].find_element(By.XPATH, ".//span/b").text
        mobile = '手机号码:' + \
            challenge_infos[1].find_element(
                By.XPATH, ".//span").text.split(' ')[-1]
        points = '我的积分:' + \
            challenge_infos[0].find_elements(
                By.XPATH, ".//span")[-1].text.split('：')[-1]
        surplusNum = '剩余抽奖次数:' + \
            challenge_infos[1].find_elements(
                By.XPATH, ".//span")[-1].text.split('：')[-1]
        thirdEnterpriseName = '单位信息:' + self.browser.find_elements(
            By.CLASS_NAME, "table-list")[-1].find_element(By.CLASS_NAME, 'list-area').text
        table_list = self.browser.find_elements(By.CLASS_NAME, "table-list")
        rank_str = ' '
        for v in table_list:
            area = v.find_element(By.CLASS_NAME, 'list-area').text
            rank = v.find_element(By.CLASS_NAME, 'list-ranking').text
            rank_str += area + ':' + rank
            rank_str += ' '
        print(memberName, mobile, points, thirdEnterpriseName, surplusNum, rank_str)
        if QUERYINFO_WRITE_FILE:
            with open(QUERYINFO_WRITE_FILE_PATH, 'a', encoding='utf-8') as f:
                t_str = ' '.join((memberName, mobile, points,
                                 thirdEnterpriseName, surplusNum))
                f.write(t_str + rank_str + '\n')

    def task(self):
        self.browser = WebDriver(load_images=True, driver_type=WebDriver.CHROME,
                                 timeout=CHROME_TIMEOUT, executable_path=CHROME_CHROME_PATH)
        self.browser.implicitly_wait(CHROME_TIMEOUT)
        self.login()
        if not ONLY_QUERYINFO and self.start():
            self.answer()
        self.query_account_info()
        self.browser.quit()

    def main(self, user, passwd):
        self.answer_ques_num = 0
        self.user = user
        self.passwd = passwd
        self.task()
