# coding:utf-8

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.common.by import By
import time
from selenium.webdriver.chrome.options import Options
from lxml import etree
from queue import Queue
import threading


class NetEase(object):

    def __init__(self):
        self.chrome_options = Options()
        self.chrome_options.add_argument('--headless')
        self.chrome_options.add_argument('--disable-gpu')

        self.driver = webdriver.Chrome()
        self.wait = WebDriverWait(self.driver, 10)

        self.funs_list = {"https://music.163.com/user/fans?id=29879272"}

        self.sig = 0

    def get_fans_page(self, url):   # 用户首页，点击粉丝

        self.driver.get(url)

        self.wait.until(ec.presence_of_element_located((By.TAG_NAME, "iframe")))
        time.sleep(3)

        js = "var box = document.getElementsByClassName('g-btmbar')[0];box.parentNode.removeChild(box);"
        self.driver.execute_script(js)   # 干掉下面的播放栏

        self.driver.switch_to.frame('g_iframe')

        fans_page = self.driver.find_element_by_id('fan_count').click()
        time.sleep(3)
        return fans_page

    def get_page_source(self, url):
        self.get_fans_page(url)
        page_source = self.driver.page_source
        selector = etree.HTML(page_source, parser=etree.HTMLParser(encoding='utf-8'))
        return selector   # 网页源码

    def get_funs_num(self, url):  # 粉丝数(用户主页中)
        page_sourse = self.get_page_source(url)
        funs_num = page_sourse.xpath('.//strong[@id="fan_count"]/text()')[0]
        return funs_num

    def fun_info_xpath(self, page_sourse):

        funs_info = page_sourse.xpath('.//ul[@id="main-box"]/li')

        funs_name_list = []
        fun_home_url_list = []
        funs_funs_num_list = []
        attentions_list = []
        attentions_num_list = []

        for fun_info in funs_info:
            fun_home_url = fun_info.xpath('./div[1]/p[1]/a/@href')[0]
            fun_home_url = 'https://music.163.com' + fun_home_url  # 粉丝主页url

            funs_funs_num = fun_info.xpath('./div[@class="info"]/p[2]/a[3]/em/text()')[0]  # 粉丝数
            funs_name = fun_info.xpath('./div[@class="info"]/p[1]/a/text()')[0]  # 粉丝名字
            attentions = fun_info.xpath('.//a[text()="关注"]/@href')[0]  # 关注的人   连接
            attentions_num = fun_info.xpath('.//a[text()="关注"]/em/text()')[0]  # 关注的人的数目

            funs_name_list.append(funs_name)
            funs_funs_num_list.append(funs_funs_num)
            fun_home_url_list.append(fun_home_url)
            attentions_list.append(attentions)
            attentions_num_list.append(attentions_num)

        funs_info_zip = zip(funs_name_list, fun_home_url_list, funs_funs_num_list, attentions_list, attentions_num_list)

        return funs_info_zip

    def get_funs_info(self, url):      # 粉丝信息
        page_sourse = self.get_page_source(url)
        return self.fun_info_xpath(page_sourse)

    def next_page(self):
        js = "window.scrollTo(0,document.body.scrollHeight)"  # 滚动到底部
        self.driver.execute_script(js)
        time.sleep(3)
        next_page_button = self.driver.find_element_by_xpath('.//a[text()="下一页"]')
        last_page_sig = next_page_button.get_attribute('class')
        return next_page_button if 'disable' not in last_page_sig else None   # 有的粉丝只有一页

    def funs(self, url):

        if self.sig == 0:
            funs_info = self.get_funs_info(url)
        else:
            funs_info = self.fun_info_xpath(url)

        # 粉丝
        for fun_info in funs_info:    # fname, furl, fnum, fattention, fattention_num
            if int(fun_info[2]) > 0:
                self.funs_list.add(fun_info[1])
            else:
                continue       # 一页粉丝抓完

        # 翻页
        next_page = self.next_page()
        if next_page:

            self.sig = 1
            time.sleep(3)
            self.next_page().click()  # 如果有下一页就点

            next_page_source = self.driver.page_source   # 下一页源码
            nps = etree.HTML(next_page_source, parser=etree.HTMLParser(encoding='utf-8'))
            return self.funs(nps)  # 下一页源码
        else:
            # 关注
            self.driver.find_element_by_id('follow_count').click()   # 点关注
            time.sleep(3)
            follows_source = self.driver.page_source  # 源码
            gz = etree.HTML(follows_source, parser=etree.HTMLParser(encoding='utf-8'))
            follows_info = self.fun_info_xpath(gz)
            return self.follows(follows_info)

    def follows(self, follows_info):

        new_list = []

        for follow_info in follows_info:    # fname, furl, fnum, fattention, fattention_num
            if type(follow_info) == 'tuple':
                new_list.append(follow_info)

        for f in new_list:
            if int(f[2]) > 0:
                self.funs_list.add(f[1])
            else:
                continue       # 一页关注抓完

        next_page = self.next_page()
        if next_page:

            self.next_page().click()
            next_follow_source = self.driver.page_source  # 下一页源码
            gz = etree.HTML(next_follow_source, parser=etree.HTMLParser(encoding='utf-8'))
            return self.follows(gz)  # 下一页源码
        else:
            print('一个账号爬完')

    def run(self):
        pass


if __name__ == '__main__':
    n = NetEase()
    n.funs("https://music.163.com/#/user/follows?id=344032069")
