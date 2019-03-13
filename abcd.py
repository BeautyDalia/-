# coding:utf-8

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.common.by import By
import time
from selenium.webdriver.chrome.options import Options
from lxml import etree
import pymysql


class NetEase(object):

    def __init__(self):
        self.chrome_options = Options()
        self.chrome_options.add_argument('--headless')
        self.chrome_options.add_argument('--disable-gpu')

        self.driver = webdriver.Chrome()  # 无头
        self.wait = WebDriverWait(self.driver, 10)

        self.sig = 0

        self.db = pymysql.connect("127.0.0.1", "root", "123456", "netease")
        self.cursor = self.db.cursor()

        self.fans_num = 0
        self.attention_num = 0

    def get_fans_page(self, url):   # 用户首页，点击粉丝

        self.driver.get(url)
        self.wait.until(ec.presence_of_element_located((By.TAG_NAME, "iframe")))
        time.sleep(3)
        try:
            js = "var box = document.getElementsByClassName('g-btmbar')[0];box.parentNode.removeChild(box);"
            self.driver.execute_script(js)   # 干掉下面的播放栏
        finally:
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
        name = page_sourse.xpath('.//h2[@id="j-name-wrap"]/span[1]/text()')
        return [funs_num, name]

    def fun_info_xpath(self, page_sourse):

        funs_info = page_sourse.xpath('.//ul[@id="main-box"]/li')

        funs_name_list = []
        fun_home_url_list = []
        funs_funs_num_list = []
        attentions_list = []
        attentions_num_list = []

        for fun_info in funs_info:
            fun_home_url = fun_info.xpath('./div[1]/p[1]/a/@href')[0]
            fun_home_url = 'https://music.163.com/#' + fun_home_url  # 粉丝主页url

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

    def next_page(self):    # 有可能下一页不能点，有可能没有下一页
        js = "window.scrollTo(0,document.body.scrollHeight)"  # 滚动到底部
        self.driver.execute_script(js)
        try:
            next_page_button = self.driver.find_element_by_xpath('.//a[text()="下一页"]')
            last_page_sig = next_page_button.get_attribute('class')
            return next_page_button if 'disable' not in last_page_sig else None   # 有的粉丝只有一页
        except:
            return None

    def funs(self, url_or_pagesource):

        if self.sig == 0:
            funs_info = self.get_funs_info(url_or_pagesource)
        else:
            funs_info = self.fun_info_xpath(url_or_pagesource)

        # 粉丝
        for fun_info in funs_info:    # fname, furl, fnum, fattention, fattention_num
            if int(fun_info[2]) > 0:
                sql = """insert into all_users(username, url, fans) values ('{}', '{}', {})""".format(str(fun_info[0]), fun_info[1], int(fun_info[2]))
                self.into_mysql(sql, '粉丝')   # 用户信息写入数据库
            else:
                continue       # 一页粉丝抓完

        # 翻页
        next_page = self.next_page()
        if next_page:
            self.sig = 1
            self.next_page().click()  # 如果有下一页就点
            time.sleep(3)
            # self.wait.until(ec.presence_of_element_located((By.XPATH, ".//ul[@id='main-box']/li[last()]")))
            try:
                next_page_source = self.driver.page_source   # 下一页源码
            except Exception as e:
                print('=========>>>获取fans源码错误：', e)
                self.next_page().click()  # 如果有下一页就点
                time.sleep(3)
                next_page_source = self.driver.page_source   # 下一页源码

            nps = etree.HTML(next_page_source, parser=etree.HTMLParser(encoding='utf-8'))
            return self.funs(nps)  # 下一页源码
        else:
            # 关注
            js = "window.scrollTo(0,0)"  # 滚动到顶部
            self.driver.execute_script(js)

            self.driver.find_element_by_id('follow_count').click()   # 点关注
            time.sleep(3)
            # self.wait.until(ec.presence_of_all_elements_located((By.XPATH, ".//ul[@id='main-box']/li")))

            follows_source = self.driver.page_source  # 源码
            gz = etree.HTML(follows_source, parser=etree.HTMLParser(encoding='utf-8'))
            follows_info = self.fun_info_xpath(gz)
            return self.follows(follows_info)

    def follows(self, follows_info):

        new_list = []

        for follow_info in follows_info:    # fname, furl, fnum, fattention, fattention_num
            if isinstance(follow_info, tuple):
                new_list.append(follow_info)
        for f in new_list:
            if int(f[2]) > 0:
                sql = """insert into all_users(username, url, fans) values ('{}', '{}', {})""".format(str(f[0]), f[1], int(f[2]))
                self.into_mysql(sql, '关注')    # 用户信息写入数据库
            else:
                continue       # 一页关注抓完

        next_page = self.next_page()
        if next_page:

            self.next_page().click()
            time.sleep(3)
            self.wait.until(ec.presence_of_element_located((By.XPATH, ".//ul[@id='main-box']/li[last()]")))

            try:
                next_follow_source = self.driver.page_source  # 下一页源码

            except Exception as e:
                print('=========>>>获取follow源码错误：', e)
                self.next_page().click()  # 如果有下一页就点
                time.sleep(3)
                next_follow_source = self.driver.page_source   # 下一页源码
            gz = etree.HTML(next_follow_source, parser=etree.HTMLParser(encoding='utf-8'))

            ff = self.fun_info_xpath(gz)   # 关注列表
            return self.follows(ff)
        else:
            print('一个账号爬完')
            self.sig = 0
            self.fans_num = 0
            self.attention_num = 0
            self.update_sql(self.driver.current_url)

    def to_sql(self, url):
        fans_num = self.get_funs_num(url)
        num = int(fans_num[0])
        name = str(fans_num[1][0])

        if int(fans_num[0]) > 200000:
            sql = """insert into user_info(user_name, url, fans_num) values ('{}','{}',{})""".format(name, url, num)
            return self.into_mysql(sql, '粉丝')

    def into_mysql(self, sql, who):

        try:
            # 执行sql语句
            self.cursor.execute(sql)
            # 提交到数据库执行
            self.db.commit()
            if who == '粉丝':
                self.fans_num += 1
                print('{}数大于0的用户数据写入成功，当前写入第{}个用户'.format(who, self.fans_num))

            if who == '关注':
                self.attention_num += 1
                print('{}数大于0的用户数据写入成功，当前写入第{}个用户'.format(who, self.attention_num))

        except Exception as e:
            # 如果发生错误则回滚
            self.db.rollback()
            print('**写入数据库发生错误，错误为：', e)

    def read_mysql(self):
        sql = """select * from all_users where isused=0 limit 10"""

        try:
            # 执行SQL语句
            self.cursor.execute(sql)
            # 获取所有记录列表
            results = self.cursor.fetchall()
            for (uid, fname, url, fans, isused) in results:
                yield url
        except Exception as e:
            print("**查询出现错误，错误为：", e)

    def update_sql(self, url):
        url_id = url.split('?')[-1]
        nurl = 'https://music.163.com/#/user/home?' + url_id
        sql = "UPDATE all_users SET isused = 1 WHERE url = '{}'".format(nurl)
        print('*******', sql)
        try:
            # 执行SQL语句
            self.cursor.execute(sql)
            # 提交到数据库执行
            self.db.commit()
            print('用户账号状态更新，用户为：', url)
        except Exception as e:
            # 发生错误时回滚
            self.db.rollback()
            print("**更新出现错误，错误为：", e)

    def run(self):
        for url in self.read_mysql():
            # try:
            self.to_sql(url)
            self.funs(url)
            # except Exception as e:
            #     print('=======>>>请求发生错误，错误内容为：', e)
            #     print('=======>>>发生错误url为：', url)
            #     continue
        if self.read_mysql():
            self.run()


if __name__ == '__main__':
    n = NetEase()
    n.run()
    # n.funs('https://music.163.com/#/user/home?id=650120')
