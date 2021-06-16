# -*- coding: UTF-8 -*-
""" 网络爬虫爬电话号码 """

from bs4 import BeautifulSoup
import requests
import requests.exceptions
from urllib.parse import urlsplit
from collections import deque
import re
import os
import csv
from requests.packages import urllib3

urllib3.disable_warnings()
import xlsxwriter
import time

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36"
}


class PhoneNumberCrawler:
    """ 电话号码爬虫 """
    # 电话号码正则表达式
    # 针对山东的区号写的正则表达式
    __phoneNumber_addr_pattern = r"\(?04\d{2}[-)]\d{7,8}|86-\(?4\d{2}[-)]\d{7,8}|04\d{2}-+\d{7,8}|04\d{2}—+\d{7,8}|04\d{2}\s?-\s?\d{7,8}|（04\d{2}）\s?\d{7,8}"

    def getwebsites(self, urls):
        websites = deque()  # 网址列表
        if type(urls) is deque:
            websites = urls
        elif type(urls) is list:
            websites = deque(urls)
        elif type(urls) is str:
            data = list()
            if os.path.exists(urls):
                data = self.__readCSVData(urls)
            else:
                data = urls.split(',')
            websites = list(data)
        else:
            pass
        return websites

    def crawl(self, website):
        """
        爬取
        \n参数: urls - 网址列表或者文件(.txt,.csv)
        """
        new_urls = deque()  # 网址列表
        processed_urls = set()  # 已爬的网址
        phoneNumbers = dict()  # 电话号码

        if type(website) is deque:
            new_urls = website
        elif type(website) is list:
            new_urls = deque(website)
        elif type(website) is str:
            data = list()
            if os.path.exists(website):
                data = self.__readCSVData(website)
            else:
                data = website.split(',')
            new_urls = deque(data)
        else:
            print("不支持的参数!")
            return phoneNumbers

        """ 开始爬取 """
        # 遍历网址直到结束
        start = time.time()
        while len(new_urls):
            # 从队列头部推出一个网址
            url = new_urls.popleft()
            processed_urls.add(url)

            # 提取基本网址与路径已解决相对链接
            parts = urlsplit(url)
            base_url = "{0.scheme}://{0.netloc}".format(parts)
            path = url[:url.rfind('/') + 1] if '/' in parts.path else url

            # 获取网址内容
            print("Processing %s" % url)

            # 爬虫的假死问题要处理一下
            global response
            try:
                nameSuffix = url.split('.')[-1]
                if nameSuffix == 'rar' or nameSuffix == 'zip' or nameSuffix == 'pdf' or nameSuffix == 'docx' or nameSuffix == 'doc' or nameSuffix == 'jpg' or nameSuffix == 'JPG' or nameSuffix == 'ppt' or nameSuffix == 'pptx' or nameSuffix == 'mp3' or nameSuffix == 'mp4' or nameSuffix == 'avi' or nameSuffix == 'exe':
                    continue
                response = requests.get(url, headers=headers, verify=False, timeout=15) # 超时时间设为15秒
                if response.status_code == 404:
                    continue
                # 考虑所爬取网页的编码方式，默认编码方式是utf-8
                charset_ = 'utf-8'
                charset_result = requests.utils.get_encodings_from_content(response.text)
                if len(charset_result) > 0:
                    charset_ = charset_result[0]
                response.encoding = charset_
            except (requests.exceptions.MissingSchema, requests.exceptions.ConnectionError, requests.exceptions.ConnectTimeout):
                # 忽略页面错误
                NETWORK_STATUS = False
                continue
			# except requests.exceptions.Timeout:
            except :
                REQUEST_TIMEOUT =True
                continue

            # 提取页面标题

            title = re.findall('<title>(.+)</title>', response.text, re.I)

            if len(title) > 0:
                title = title[0]
            else:
                continue

            # 提取页面中的所有phoneNumber,并且将它们添加到结果集
            new_phoneNumbers = list(re.findall(self.__phoneNumber_addr_pattern, response.text, re.I))
            if len(new_phoneNumbers) > 0:
                for phoneNumber in new_phoneNumbers:
                    if phoneNumber not in phoneNumbers:
                        phoneNumbers.setdefault(phoneNumber, []).append(1)
                        phoneNumbers.setdefault(phoneNumber, []).append(title)
                    else:
                        phoneNumbers[phoneNumber][0] = phoneNumbers[phoneNumber][0] + 1
                phoneNumbers = dict(sorted(phoneNumbers.items(), key=lambda i: i[1], reverse=True))
                if len(phoneNumbers) >= 15:
                    temp = dict()
                    cnt = 0
                    for phoneNumber, value in phoneNumbers.items():
                        temp.update({phoneNumber: value})
                        cnt = cnt + 1
                        if cnt >= 15:
                            break
                    phoneNumbers = temp

                print(len(phoneNumbers))
                print(phoneNumbers)

            # ----------------遍历时间太长或者获取电话号码够15个就跳出此函数----------------
            end = time.time()
            if len(phoneNumbers) >= 15 or (end - start) >= 60:
                return phoneNumbers

            # 给文档创建beautiful soup
            soup = BeautifulSoup(response.text, features="lxml")

            # 找到并处理文档中所有的锚
            for anchor in soup.find_all('a'):
                # 从锚中提取链接
                link = anchor.attrs['href'] if 'href' in anchor.attrs else ''
                # 处理内部链接
                if link.startswith('/'):
                    link = base_url + link
                elif not link.startswith('http'):
                    link = path + link

                # 添加新链接
                # 当新链接的格式不规范是，这时候就要进行异常处理了
                try:
                    partsTemp = urlsplit(link)
                    base_urlTemp = "{0.scheme}://{0.netloc}".format(partsTemp)
                    if base_urlTemp == base_url and not link in new_urls and not link in processed_urls:  # 只爬取本站点的内容、已经爬过的地址不用爬了
                        new_urls.append(link)
                except:
                    continue
        return phoneNumbers

    def __readCSVData(self, filename):
        """ 读取文件 """
        data = list()
        with open(filename, 'r') as f:
            f_csv = csv.reader(f)
            for row in f_csv:
                data.append(row[0])
        return data


def save_excel(phoneNumbers_list):
    # 填充爬取的课程信息
    # page1  行数 1 50     50*(1-1) + 1
    # page2  行数 51 100   50*(2-1) + 1
    # page3  行数 101 150  50*(3-1) + 1
    for num, phoneNumber in enumerate(phoneNumbers_list):
        row = len(phoneNumbers_list) * (index - 1) + num + 1
        worksheet.write(row, 0, phoneNumber)
        worksheet.write(row, 1, phoneNumbers_list[phoneNumber][0])
        worksheet.write(row, 2, phoneNumbers_list[phoneNumber][1])


def main(index, phoneNumbers_list):
    save_excel(phoneNumbers_list)  # 写入到excel


def get_filename(file_dir):
    L = []
    for root, dirs, files in os.walk(file_dir):
        for file in files:
            name = os.path.splitext(file)[0]
            L.append(name)
    return L


if __name__ == '__main__':

    # urls = 'http://www.themoscowtimes.com'
    # urls = ['http://www.themoscowtimes.com']
    # urls = 'http://zuzhibu.dlut.edu.cn/'
    file_dir = './websitesData/'
    filename_list = get_filename(file_dir)

    for filename_ in filename_list:
        phoneNumberCrawl = PhoneNumberCrawler()
        url = file_dir + filename_ + '.txt'
        websites = phoneNumberCrawl.getwebsites(url)
        allPhoneNumbers = dict()

        for website in websites:
            phoneNumbers = phoneNumberCrawl.crawl(website)
            for phoneNumber, value in phoneNumbers.items():
                allPhoneNumbers.update({phoneNumber: value})
            print('--------------------%s 爬取完成！！！！！！--------------------' % website)

        # 设置文件名
        # try:
        #     res = requests.get(websites[0], headers=headers, verify=False)
        #     res.encoding = 'utf-8'
        # except (requests.exceptions.MissingSchema, requests.exceptions.ConnectionError):
        #     print('Error: 没有找到标签或读取标签失败')
        #
        # name = re.findall('<title>(.+)</title>', res.text, re.I)[0]
        name = filename_

        # 存入excel
        # phoneNumbers = {'shuji@dlut.edu.cn': [1818, '大连理工大学'], 'office@dlut.edu.cn': [2147, '大连理工大学'], 'general@dlut.edu.cn': [658, '大连理工大学']}
        workbook = xlsxwriter.Workbook("./phoneNumbersData/" + name + ".xlsx")  # 创建excel
        worksheet = workbook.add_worksheet("first_sheet")
        worksheet.write(0, 0, "电话号码")
        worksheet.write(0, 1, "出现频率")
        worksheet.write(0, 2, "所属部门")

        print(len(allPhoneNumbers))

        index = 1
        main(index, allPhoneNumbers)
        workbook.close()
        print('--------------------电话号码爬完了！！！！！！--------------------')