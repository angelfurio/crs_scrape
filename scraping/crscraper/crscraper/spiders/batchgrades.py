# -*- coding: utf-8 -*-
import os

import scrapy

from .. import settings

BASE_DIR = os.path.join(settings.PROJECT_ROOT, '__data__', 'grades')

class BatchGradesSpider(scrapy.Spider):
    name = "batchgrades"
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
            callback=self.switch_role,
            dont_filter=True,
        )

    def switch_role(self, response):
        return scrapy.Request(
            "https://crs.upd.edu.ph/viewgrades",
            callback=self.view_grades_start,
        )

    def view_grades_start(self, response):
        # TODO: shuffle
        with open("studentnumbers.txt") as f:
            lines = f.readlines()
            self.total = len(lines)
            self.current = 0

            for line in lines:
                studentnumber = line.strip().replace("-", "")

                if not os.path.isfile(BASE_DIR + studentnumber + ".html"):
                    request = scrapy.FormRequest.from_response(
                        response,
                        formdata={'studentno': studentnumber},
                        callback=self.view_grades,
                        dont_filter=True
                    )
                    request.meta['studentnumber'] = studentnumber

                    yield request
                else:
                    self.current += 1
                    self.print_log(studentnumber, "skipping")

    def view_grades(self, response):
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

