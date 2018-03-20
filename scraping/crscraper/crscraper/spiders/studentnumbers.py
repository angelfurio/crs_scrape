# -*- coding: utf-8 -*-
import os

import scrapy
from lxml import html

from .. import settings

BASE_DIR = os.path.join(settings.PROJECT_ROOT, '__data__', 'studentnumbers')

class StudentNumbersSpider(scrapy.Spider):
    name = "studentnumbers"
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
            "https://crs.upd.edu.ph/ineligibility/batch_tag",
            callback=self.batch_tag_start,
        )


    def batch_tag_start(self, response):
        years = [str(year) for year in range(2006, 2017 + 1)]

        for year in years:
            request = scrapy.FormRequest.from_response(
                response,
                formdata={
                    'snobatch': year,
                    'lastname': '',
                    'mainunit': '111',
                },
                callback=self.batch_tag,
                dont_filter=True,
                formnumber=1,
            )
            request.meta['year'] = year

            yield request


    def batch_tag(self, response):
        year = response.meta['year']
        print(year)

        with open(os.path.join(BASE_DIR, year + ".html"), "wb") as f:
            f.write(response.body)

        """
        yield {
            'sid': response.xpath('//tr[boolean(@ineligclass)]/td[position()=2]/text()').extract()
        }
        """

    def closed(self, reason):
        if reason == "finished":
            student_numbers = []

            for filepath in glob.glob('__data__/studentnumbers/*.html'):
               with open(filepath, 'r') as f:
                    doc = html.parse(f)
                    sids = doc.xpath('//tr[boolean(@ineligclass)]/td[position()=2]/text()')

                    for sid in sids:
                        student_numbers.append(sid)

            with open('studentnumbers.txt', 'w') as f:
                f.write('\n'.join(sorted(student_numbers)))

            print("DONE")
