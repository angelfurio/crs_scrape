# -*- coding: utf-8 -*-
import os

import scrapy

from .. import settings

BASE_DIR = os.path.join(settings.PROJECT_ROOT, '__data__', 'advising')
if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

class AdvisingSpider(scrapy.Spider):
    name = "advising"
    allowed_domains = ["crs.upd.edu.ph"]
    start_urls = ['http://crs.upd.edu.ph/']

    def parse(self, response):
        return scrapy.FormRequest.from_response(
            response,
            formdata={'txt_login': self.settings.get('USERNAME'), 'pwd_password': self.settings.get('PASSWORD')},
            callback=self.after_login,
        )

    def after_login(self, response):
        if b"Login Error" in response.body:
            self.logger.error("Login failed")
            return
        
        return scrapy.Request(
            "https://crs.upd.edu.ph/user/switch_role/175328",
            callback=self.online_advising_start,
            dont_filter=True,
        )

    def online_advising_start(self, response):
        # TODO: shuffle
        with open("studentnumbers.txt") as f:
            lines = f.readlines()
            self.total = len(lines)
            self.current = 0

            for line in lines:
                studentnumber = line.strip().replace("-", "")

                if not os.path.isfile(os.path.join(BASE_DIR, studentnumber + ".html")):
                    request = scrapy.Request(
                        "https://crs.upd.edu.ph/online_advising/advise/120171/" + studentnumber,
                        callback=self.online_advising,
                        dont_filter=True,
                    )
                    request.meta['studentnumber'] = studentnumber

                    yield request
                else:
                    self.current += 1
                    self.print_log(studentnumber, "skipping")

    def online_advising(self, response):
        studentnumber = response.meta['studentnumber']

        with open(os.path.join(BASE_DIR, studentnumber + ".html"), "wb") as f:
            f.write(response.body)

        self.current += 1
        self.print_log(studentnumber)


    def print_log(self, studentnumber, msg=""):
        if msg:
            msg = " - " + msg

        print("{} / {} ({}%) - {} - {}".format(
            self.current,
            self.total,
            self.current / self.total * 100,
            studentnumber,
            msg,)
        )

