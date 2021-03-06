#!/usr/bin/python3.6
# -*- coding: utf-8 -*-
# @Author  : Loot at the stars
# @Time    : 2022/5/12 14:22
# @File    : login.py
# @Software: PyCharm

import logging
import requests
import json
from functions import generateState, getLT, loadCfg, writeCfg
from myHeaders import *
from decode import *
import urllib3
import datetime


class Login:
    def __init__(self):
        self.userid = ""
        self.password = ""
        self.token = ""
        self.cookie = ""
        self.location_cas2skl = ""
        self.location_cas3 = ""
        self.location_token = ""
        self.location_skl = ""
        self.formData = {
            'rsa': '',
            'ul': '',
            'pl': '',
            'lt': '',
            'execution': 'e1s1',
            '_eventId': 'submit'
        }
        self.url_skl = "https://skl.hduhelp.com/"
        self.cas_state = generateState()
        self.url_skl2cas = "https://cas.hdu.edu.cn/cas/login?state=" + self.cas_state + "&service=" + "https%3A%2F%2Fskl.hdu.edu.cn%2Fapi%2Fcas%2Flogin%3Fstate%3D" + self.cas_state + "%26index%3D"

        urllib3.disable_warnings()
        self.session = requests.session()

        self.cfgData = loadCfg('config.ymal')

        if self.cfgData['User']['id'] is None or self.cfgData['User']['pwd'] is None:
            print("####首次登录，初始化...###")
            self.cfgData['User']['id'] = input("请输入学号：")
            self.cfgData['User']['pwd'] = input("请输入登录密码：")

        self.userid = str(self.cfgData['User']['id'])
        self.password = str(self.cfgData['User']['pwd'])
        if self.cfgData['params']['X-Auth-Token'] is not None:
            if (datetime.datetime.strptime(str(self.cfgData['params']['XAT_updateTime']),
                                           "%Y-%m-%d %H:%M:%S") - datetime.datetime.now()).seconds / 3600 < 144:
                self.token = str(self.cfgData['params']['X-Auth-Token'])

    # [GET] skl跳转cas认证, 获取响应头Cookie
    def skl2cas(self):
        try:
            response = self.session.get(url=self.url_skl2cas, headers=headers_skl2cas, verify=False)
            if response.status_code != 200:
                logging.debug("跳转cas认证失败!")
                return
            setCookie = response.headers["Set-Cookie"].split(';')
            for i in range(len(setCookie)):
                if 'JSESSIONID' in setCookie[i]:
                    self.cookie += setCookie[i].split(' ')[-1] + '; '
                    break
            if len(self.cookie) == 0:
                logging.error("获取Cookie失败！")

            logging.debug(self.cookie)
            self.formData['lt'] = getLT(response)
            self.formData['ul'] = str(len(self.userid))
            self.formData['pl'] = str(len(self.password))
            self.formData['rsa'] = cacuRsa(self.userid, self.password, self.formData['lt'])
        except Exception as e:
            logging.error(e)

    # [POST] cas认证登录
    def cas1(self):
        headers = headers_cas1
        try:
            headers["Cookie"] = self.cookie + ";" + " Language=zh_CN"
            headers["Referer"] = self.url_skl2cas
            response = self.session.post(url=self.url_skl2cas, headers=headers, data=self.formData, verify=False,
                                         allow_redirects=False)
            if response.status_code != 302:
                logging.debug("cas认证失败!")
                return
            self.location_cas2skl = response.headers["Location"]
            logging.debug(self.location_cas2skl)

            setCookie = response.headers["Set-Cookie"].split(';')
            for i in range(len(setCookie)):
                if 'CASTGC' in setCookie[i]:
                    self.cookie += setCookie[i].split(',')[-1]
                    break
        except Exception as e:
            logging.error(e)

    # 请求skl路径
    def cas2(self):
        headers = headers_cas2
        try:
            response = self.session.get(url=self.location_cas2skl, headers=headers, verify=False, allow_redirects=False)
            if response.status_code != 302:
                logging.debug("cas跳转skl失败!")
                return
            self.location_cas3 = response.headers["Location"]
            logging.debug(self.location_cas3)

        except Exception as e:
            logging.error(e)

    def cas3(self):
        headers = headers_cas2
        headers["Host"] = "cas.hdu.edu.cn"
        headers["Cookies"] = self.cookie + "; Language=zh_CN"
        try:
            response = self.session.get(url=self.location_cas3, headers=headers, verify=False, allow_redirects=False)
            if response.status_code != 302:
                logging.debug("获取skl_location失败!")
                return
            self.location_token = response.headers["Location"]
        except Exception as e:
            logging.error(e)

    def getToken(self):
        headers = headers_cas2skl
        try:
            response = self.session.get(url=self.location_token, headers=headers, verify=False, allow_redirects=False)
            if response.status_code != 302:
                logging.debug("获取skl_token失败!")
                return
            self.token = response.headers["X-Auth-Token"]
            self.location_skl = response.headers["Location"]

            self.cfgData['params']['X-Auth-Token'] = self.token
            self.cfgData['params']['XAT_updateTime'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            writeCfg('config.ymal', self.cfgData)

        except Exception as e:
            logging.error(e)

    def skl_login(self):
        url = ""
        if len(self.token) == 0:
            self.skl2cas()
            self.cas1()
            self.cas2()
            self.cas3()
            self.getToken()
            url = self.location_skl
        else:
            url = "https://skl.hduhelp.com/"
        headers = headers_cas2skl
        try:
            response = self.session.get(url=url, headers=headers, verify=False)
            if response.status_code != 200:
                logging.debug("skl登录失败!")
                return
            logging.info("skl登录成功！")
            logging.debug(response.text)
            return self.userid, self.token
        except Exception as e:
            logging.error(e)


if __name__ == '__main__':
    myLogin = Login()
    myLogin.skl_login()
