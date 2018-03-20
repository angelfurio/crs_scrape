# -*- coding: utf-8 -*-
import os
import getpass
import json
import logging
from collections import OrderedDict

import scrapy
from lxml import html

class NotDoneSpider(scrapy.Spider):
    name = "notdone"
    allowed_domains = ["crs.upd.edu.ph"]
    start_urls = ['http://crs.upd.edu.ph/']

    # TODO: make setting variable instead
    SID_FILE = "notdone.txt"

    def __init__(self, *args, **kwargs):
        logger = logging.getLogger('scrapy.downloadermiddlewares.redirect')
        logger.setLevel(logging.WARNING)
        super().__init__(*args, **kwargs)

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
            "https://crs.upd.edu.ph/validation",
            callback=self.notdone_start,
        )

    def notdone_start(self, response):
        with open(self.SID_FILE) as f:
            lines = [i.strip() for i in f.readlines()]

        self.status = OrderedDict.fromkeys(lines)
        self.units = OrderedDict.fromkeys(lines)
        self.error = []
        self.current = 0
        self.total = len(lines)

        for sid in lines:
            request = scrapy.Request(
                "https://crs.upd.edu.ph/validation",
                callback=self.indiv_not_done,
                dont_filter=True,
            )
            request.meta['sid'] = sid

            yield request

    def indiv_not_done(self, response):
        sid = response.meta['sid']

        self.current += 1
        print(sid, self.current, "/", self.total, str(self.current / self.total * 100.0) + "%")

        crs_internal_aytermid = response.xpath("//input[@id='hid_aytermid']/@value").extract_first()

        request = scrapy.FormRequest.from_response(
            response,
            formdata={
                'studentno': sid,
                'aytermid': crs_internal_aytermid,
            },
            callback=self.done,
            dont_filter=True,
            formnumber=0,
        )
        request.meta['sid'] = sid

        yield request

    def done(self, response):
        sid = response.meta['sid']

        if response.url == "https://crs.upd.edu.ph/validation/manage":
            self.status[sid] = "N"
        elif response.url == "https://crs.upd.edu.ph/validation":
            body = response.body.decode('utf8')

            if "Student has already been assessed!" in body:
                self.status[sid] = "Y"
            elif "Student is ineligible!" in body:
                self.status[sid] = "I"
            elif "No Student Profile" in body:
                self.status[sid] = "X"
            elif "Student not within scope" in body:
                self.error.append(sid)
                del self.status[sid]
            else:
                self.error.append(sid)
                del self.status[sid]
        else:
            input("ERROR FOR " + sid + ": " + response.url)

        if sid in self.status and self.status[sid]:
            request = scrapy.Request(
                "https://crs.upd.edu.ph/online_advising/advise/120172/" + sid,
                callback=self.check_enlisted_units,
            )

            request.meta['sid'] = sid

            return request

    def check_enlisted_units(self, response):
        sid = response.meta['sid']
        body = response.body.decode('utf8')

        if "Total Units" not in body:
            self.units[sid] = 0
        else:
            doc = html.fromstring(body)
            units = int(doc.xpath('//b[text()="Total Units:"]/following-sibling::span[1]/text()')[0].replace(".0", ""))
            print(sid, "has", units, "units")

            self.units[sid] = units

    def closed(self, reason):
        if reason == "finished":
            output = []

            with open("notdone_output.txt", "w") as f:
                for key, value in self.status.items():
                    output.append("\t".join((key, value, str(self.units[key]) + "\n")))
            
                f.writelines(output)

            print("Not in scope:", len(self.error), self.error)
            print("DONE")
