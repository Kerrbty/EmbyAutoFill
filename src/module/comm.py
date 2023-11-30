#! /usr/bin/env python
# -*- coding:utf-8 -*-

import os,sys
import requests
import urllib3
import re
import time

urllib3.disable_warnings()

http_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.89 Safari/537.36',
    'Accept': '*/*'
}

# 日志打印时间 
def logger(*nums):
    print(time.strftime("[%Y-%m-%d][%H:%M:%S] ", time.localtime()), end="")
    for argv in nums:
        print(argv, end=" ")
    print()
    sys.stdout.flush()

# 猜测网页编码 
def get_encoding(html):
    if re.search('charset="gb2312"', html) or re.search('charset=gb2312', html):
        return "gb2312"
    elif re.search('charset="gbk"', html) or re.search('charset=gbk', html):
        return "gbk"
    elif re.search('charset="utf-8"', html) or re.search('charset=utf-8', html):
        return "utf-8"
    else:
        return "utf-8"
        
# 获取网页文本
def _http_request(url, data = None, post = False, headers = http_headers):
    try:
        # 获取网页
        http = requests.session()
        http.keep_alive = False
        if post:
            r = http.post(url, timeout=(5, 10), headers=headers, data=data, verify=False)
        else:
            r = http.get(url, timeout=(5, 10), headers=headers, verify=False)
        # 设置网页编码
        r.encoding = get_encoding(r.text)
        # 记录cookie
        if r.cookies:
            cookie = ''
            for k,v in r.cookies.items():
                cookie = cookie + str(k) + '=' + str(v) + ';'
            headers["Cookie"] = cookie
        # 返回页面数据 
        return r.text
    except Exception as e:
        # 打印完整的异常信息
        traceback.print_exc()
        return None

def get_html(url, retry = 3, headers = http_headers):
    times = 0
    html = None
    while times < retry:
        html = _http_request(url, None, False, headers)
        if html:
            break
        times = times+1
    return html

def post_html(url, data=None, retry = 3, headers = http_headers):
    times = 0
    html = None
    while times < retry:
        html = _http_request(url, data, True, headers)
        if html:
            break
        times = times+1
    return html

def _get_content(url):
    try:
        http = requests.session()
        http.keep_alive = False
        data = http.get(url, timeout=3, headers=http_headers, verify=False)
        return data.content
    except:
        return None

# 获取远程二进制数据(下载文件等) 
def get_content(url):
    count = 0
    while True:
        data = _get_content(url)
        if data:
            break
        count = count + 1
        if count > 3:
            break
    return data

