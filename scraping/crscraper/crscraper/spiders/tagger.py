# -*- coding: utf-8 -*-
import os
import getpass
import json

import scrapy
from lxml import html

class TaggerSpider(scrapy.Spider):
    name = "tagger"
    allowed_domains = ["crs.upd.edu.ph"]
    start_urls = ['http://crs.upd.edu.ph/']

    # TODO: make setting variable instead
    INELIG_FILE = "inelig.json"

    def parse(self, response):
        username = input("Username: ")
        password = getpass.getpass("Password: ")

        return scrapy.FormRequest.from_response(
            response,
            formdata={'txt_login': username, 'pwd_password': password},
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
            #"https://crs.upd.edu.ph/ineligibility/tag_multiple_studentnos",
            #callback=self.multi_tag_start,
            "https://crs.upd.edu.ph/ineligibility/manage_student/",
            callback=self.indiv_tag_start,
        )

    def indiv_tag_start(self, response):
        with open(self.INELIG_FILE) as f:
            data = json.load(f)

        for entry in data:
            sid = entry['sid']
            msg = entry['msg']

            request = scrapy.Request(
                "https://crs.upd.edu.ph/ineligibility/manage_student/" + str(sid),
                callback=self.indiv_tag,
            )
            request.meta['sid'] = sid
            request.meta['msg'] = msg

            yield request

    def indiv_tag(self, response):
        crs_internal_sid = response.xpath("//input[@id='hdn_studentid']/@value").extract_first()
        sid = response.meta['sid']
        msg = response.meta['msg']

        request = scrapy.FormRequest.from_response(
            response,
            formdata={
                'ineligreason': "36", # 36 = For pre-advising
                'newstatus': "19", # 19 = Not advised
                'remarks': msg,
                'studentid': crs_internal_sid,
                'activetab': "acadinelig",
            },
            callback=self.done,
            dont_filter=True,
            formnumber=3,
        )
        request.meta['sid'] = sid
        request.meta['msg'] = msg

        yield request

    def done(self, response):
        print(response.meta['sid'], response.meta['msg'])

    """
    def multi_tag_start(self, response):
        inelig_groups = {}
        inelig_cases = []

        for rule1 in [False, True]:
            for rule2 in [False, True]:
                for rule3 in [False, True]:
                    case = (rule1, rule2, rule3)

                    inelig_groups[case] = []
                    inelig_cases.append(case)

        # JSON format: [{
        #   "code": "<code>",
        #   "sids": ["<sid1>", "<sid2>", ...],
        # }, ...]
        with open(self.INELIG_FILE) as f:
            inelig_json = json.load(f)

        # Populate inelig mapping
        for entry in inelig_json:
            code = entry['code']
            sids = entry['sids']

            case = self.make_case_from_code(code)
            inelig_groups[case] = sids

        # Tag students grouped by ineligibility possibility (cases)
        for inelig_case in inelig_cases:
            inelig_group = inelig_groups[inelig_case]

            if inelig_group:
                request = scrapy.FormRequest.from_response(
                    response,
                    formdata={
                        'studentnos': "\n".join(inelig_group),
                    },
                    callback=self.multi_tag,
                    dont_filter=True,
                    formnumber=1,
                )
                request.meta['message'] = self.make_message(inelig_case)

                yield request


    def multi_tag(self, response):
        print(response.meta['message'])

        with open(response.meta['message'].replace(":", "").replace(",", "") + ".html", "wb") as f:
            f.write(response.body)


    def make_message(self, inelig_case):
        rule1, rule2, rule3 = inelig_case
        msg_list = []

        if rule1:
            msg_list.append("Rule 1")

        if rule2:
            msg_list.append("Rule 2")

        if rule3:
            msg_list.append("Rule 3")

        if len(msg_list) == 1:
            return "Violation: " + msg_list[0]
        else:
            return "Violations: " + ", ".join(msg_list)


    def make_case_from_code(self, code):
        code = int(code)

        return tuple([bool(code & (1 << i)) for i in range(2, -1, -1)])
    """
