from lxml import html


class EnlistmentScraper:
    
    def __init__(self, filepath):
        self.filepath = filepath
        with open(self.filepath, 'r') as f:
            self.doc = html.parse(f)

    def parse(self):
        doc = self.doc

        error = self._get_error(doc)
        if error:
            return {
                'error': True,
                'status': error,
            }

        semester = doc.xpath("//h1[contains(node(), 'Online Advising for')]/text()")[0].replace("Online Advising for ", "")
        number = self._get_semester_number(semester)

        info_table = doc.xpath("//table//tr//td[contains(node(), 'Computer Science')]/../..")[0]
        degree_program = doc.xpath("//table//tr//td[contains(node(), 'Computer Science')]//text()")[0]
        last_name, first_name = info_table.xpath("tr[1]/td[2]//text()")[0].split(", ")
        sid = info_table.xpath("tr[1]/td[1]//text()")[0].replace("-", "")
        priority = info_table.xpath("tr[4]/td[2]//text()")[0]
        eligibility = info_table.xpath("tr[5]/td[2]//text()")[0]
        accountability = info_table.xpath("tr[6]/td[2]//text()")[0]

        classes = []

        if not doc.xpath("//*[contains(text(), 'There are no enlisted classes')]"):
            class_table = doc.xpath("//table//tr//th[contains(node(), 'Class Code')]/../..")[0]
            for row in [[td.xpath("text()") for td in tr.xpath("td")] for tr in class_table.xpath(".//tr")][1::2]:
                # 0: Class Code
                # 1: Class
                # 2: Schedule/Instructors
                # 3: Credits
                # 4: Action
                code_list, class_list, schedinst_list, units_list, _ = row

                class_count = len(code_list)

                for i in range(class_count):
                    code = code_list[i]
                    class_ = class_list[i].replace(" - ", " ").replace("  ", " ")
                    units = units_list[i]

                    schedinst_count = len(schedinst_list)
                    
                    if class_count * 2 == schedinst_count:
                        schedinst = [schedinst_list[i*2], schedinst_list[i*2+1]]
                    else:
                        schedinst = [schedinst_list[i], "CONCEALED"]

                    schedule, faculty = schedinst
                    faculty = [i.strip() for i in faculty.split("; ")]

                    # Connect class trailing number with dash
                    last_token = class_.rsplit(" ", maxsplit=1)[-1]
                    if len(last_token) == 1 and last_token.isnumeric():
                        index = class_.rindex(" ")
                        class_ = class_[:index] + '-' + class_[index+1:]

                    course = ' '.join(class_.split(' ')[:-1])
                    section = class_.split(' ')[-1]

                    classes.append({
                        'code': code,
                        'course': course,
                        'section': section,
                        'schedule': schedule,
                        'faculty': faculty,
                        'units': units,
                    })

        return {
            'sid': sid,
            'last_name': last_name,
            'first_name': first_name,
            'degree_program': degree_program,
            'classes': classes,
            'semester': semester,
            'number': number,
            'priority': priority,
            'eligibility': eligibility,
            'accountability': accountability,
        }

    def _get_error(self, doc):
        if not doc.xpath('//td[contains(node(), "Computer Science")]'):
            return "NOT_WITHIN_SCOPE"
        
        return None

    def _get_semester_number(self, semester):
        if 'Summer' in semester:
            suffix = '3'
            prefix = str(int(semester.split()[1][2:]) - 1)
        elif 'Midyear' in semester:
            suffix = '4'
            prefix = str(int(semester.split()[2][2:]) - 1)
        else:
            if 'First' in semester:
                suffix = '1'
            else:
                suffix = '2'
            prefix = semester.split()[3][2:4]

        number  = int(prefix + suffix)

        return number


def pp_file(filepath):
    pretty_print(from_file(filepath))

def pretty_print(data):
    if data.get('error'):
        print(data['status'])
        return

    print(data['sid'])
    print(data['last_name'])
    print(data['first_name'])
    print(data['degree_program'])
    
    for semester in data['semesters']:
        print()
        print(semester['semester'])
        print(semester['number'])
        print(semester['status'])
        print()

        for grade in semester['grades']:
            print(grade)

def from_file(filepath):
    with open(filepath, 'r') as f:
        doc = html.parse(f)

    error = _get_error(doc)
    if error:
        return {
            'error': True,
            'status': error,
        }

    name = _get_name(doc)
    sid = _get_student_number(doc)
    degree_program = _get_degree_program(doc)
    semesters = _get_semesters(doc)

    return {
        'sid': sid,
        'last_name': name['last_name'],
        'first_name': name['first_name'],
        'degree_program': degree_program,
        'semesters': semesters,
    }

def _get_error(doc):
    if doc.xpath('//*[contains(node(), "not within scope")]'):
        return "NOT_WITHIN_SCOPE"
    elif doc.xpath('//*[contains(node(), "existing grades")]'):
        return "NO_EXISTING_GRADES"
    
    return None

def _get_student_number(doc):
    return doc.xpath('//td[contains(node(), "in Computer Science")]/../../tr[2]/td[1]')[0].text.replace('-', '')

def _get_name(doc):
    last_name, first_name, _ = [i.strip() for i in str(doc.xpath('//td[contains(node(), "in Computer Science")]/../../tr[1]/td[1]')[0].text).split(',')]

    return {
        'last_name': last_name,
        'first_name': first_name,
    }

def _get_degree_program(doc):
    # TODO: support other degree programs
    if doc.xpath('//td[contains(node(), "Bachelor of Science in Computer Science")]'):
        return "BS Computer Science"
    elif doc.xpath('//td[contains(node(), "Master of Science in Computer Science")]'):
        return "MS Computer Science"
    else:
        return "PhD Computer Science"

def _get_semesters(doc):
    semesters = []
    ths = doc.xpath('//table//th[contains(node(), "20")]')

    for th in ths:
        semesters.append(_parse_semester_table(th))

    return semesters

def _parse_semester_table(th):
    return {
        'semester': _get_semester(th),
        'number': _get_semester_number(th),
        'status': _get_status(th),
        'grades': _get_class_grades(th),
    }

def _get_semester(th):
    return th.text

def _get_semester_number(th):
    semester = th.text

    if 'Summer' in semester:
        suffix = '3'
        prefix = str(int(semester.split()[1][2:]) - 1)
    elif 'Midyear' in semester:
        suffix = '4'
        prefix = str(int(semester.split()[2][2:]) - 1)
    else:
        if 'First' in semester:
            suffix = '1'
        else:
            suffix = '2'
        prefix = semester.split()[3][2:4]

    number  = int(prefix + suffix)

    return number

def _get_status(th):
    semester = th.text

    if th.xpath('../../../tbody/tr//td[contains(node(), "Leave of Absence")]'):
        return 'LOA'
    elif th.xpath('../../../tbody/tr//td[contains(node(), "Residency")]'):
        return 'Residency'
    elif 'Summer' not in semester and 'Midyear' not in semester and not th.xpath('../../../tbody/tr//td[contains(node(), "CS ")]') and not th.xpath('../../../tbody/tr//td[contains(node(), "Stat 130")]') and th.xpath('/*//td[contains(node(), "Bachelor of Science in Computer Science")]'):
        return 'VSO'

    return "Regular"

def _get_class_grades(th):
    grades = []
    trs = th.xpath('../../../tbody/tr')

    for tr in trs:
        tds = tr.xpath('td')
        # 0: Tag
        # 1: Class Code
        # 2: Class
        # 3: Faculty
        # 4: Units
        # 5: Grade
        # 6: Completion
        # 7: Comment
        td_text = [str(td.text).strip() for td in tds]

        if len(td_text) > 5:
            grade = td_text[5].replace('\xa0', '')
            class_ = td_text[2].replace('\xa0', '')
            units = td_text[4]
            faculty = _parse_faculty(td_text[3])
            code = td_text[1]

            # 26511 SEA 30 WFU 1, 1st Sem AY 16-17
            # Math 55 X3 - 1
            # Comm 3 THV 1
            # CWTS 1-2 - CMC 1
            # CWTS2 - CSWCD CD 2
            # Econ 11 WI 2
            # Econ 100.1 FJ 1
            # BA 180.1 WFY - 1
            # Econ 100.2 HI 3
            # Econ 11 TI 3
            # Econ 11 TJ 2
            # Econ 11 TI 2
            # Econ 11 HJ 2
            # CWTS2 - CSWCD CD 1
            # CWTS2 - CSWCD CD 4
            # Econ 11 TI 1
            # Econ 11 TL 3
            # Econ 11 WJ 3
            # Econ 11 TI 4
            # Econ 11 TK 1
            # SEA 30 WFU 2
            # SEA 30 THR 2
            # Econ 11 WJ 2
            # Econ 11 HI 3
            # SEA 30 THR 2
            # Econ 11 WE 2
            # Econ 11 WI 3
            # Econ 11 WI 1
            # Econ 11 WI  3
            # Econ 11 WJ 3
            # Econ 11 WI  3
            # Econ 11 TK 1
            # Econ 11 HI 2
            # Econ 11 HE 3
            # Econ 11 HE 3
            # CWTS 1 - FA Mon 1
            # CWTS 2 - FA Mon 1
            # SEA 30 WFW 2
            # SEA 30 WFU 3
            # SEA 30 THR 1
            # SEA 30 THU 2
            # SEA 30 THU 2
            # SEA 30 WFW 3
            # SEA 30 WFU 1
            # SEA 30 WFW 3
            # SEA 30 WFW 2
            # SEA 30 WFU 2
            # CWTS 1 - FA Mon 1
            # CWTS 2 - FA Mon 1
            # SEA 30 WFW 2
            # Econ 11 TI 1
            # SEA 30 WFU 1
            # Econ 11 WI 1
            # Film 10 MTWThF 2
            # SEA 30 WFW 3
            # CWTS 1 - FA Mon 1
            # CWTS 2 - FA Mon 1
            # Econ 11 HI 1
            # Econ 11 HJ 1
            # SEA 30 WFW 3
            class_ = class_.replace(" - ", " ")
            class_ = class_.replace("  ", " ")
            last = class_.rsplit(" ", maxsplit=1)[-1]
            if len(last) == 1 and last.isnumeric():
                index = class_.rindex(" ")
                class_ = class_[:index] + '-' + class_[index+1:]
            # CS 133 Hybrid UG/G
            if class_.split()[0] == "CS":
                course_name = " ".join(class_.split()[:2])
                section_start_index = len(course_name) + 1
                class_ = class_[:section_start_index] + class_[section_start_index:].replace(" ", "-")

            d = {}
            d['course'] = ' '.join(class_.split(' ')[:-1])
            d['section'] = class_.split(' ')[-1]
            d['units'] = units
            d['grade'] = grade
            d['faculty'] = faculty
            d['code'] = code

            grades.append(d)

    return grades

def _parse_faculty(faculty_str):
    return [i.strip() for i in faculty_str.split(';')]
