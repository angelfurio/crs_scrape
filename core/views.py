import os
import json

from django.shortcuts import render

from core.models import Course, Semester, Grade, Student, Faculty, Class


def home(request):
    SEMESTER_NUMBER = 171
    data = {}
    courses = [
        'Math 17',
        'Math 53',
        'Math 54',
        'Math 55',
        'Stat 130',
        'CS 11',
        'CS 12',
        'CS 21',
        'CS 30',
        'CS 32',
        'CS 130',
        'CS 131',
        'CS 133',
        'CS 135',
        'CS 140',
        'CS 145',
        'CS 150',
        'CS 153',
        'CS 165',
        'CS 180',
        'CS 191',
        'CS 192',
        'CS 195',
        'CS 198',
        'CS 199',
    ]
    courses = [Course.objects.get(name=i) for i in courses]

    courses_data = []

    for course in courses:
        semester = Semester.objects.get(number=SEMESTER_NUMBER)

        grades = Grade.objects.filter(class_attr__course=course, class_attr__semester=semester).order_by('grade')
        takers = course.must_take()
        passed = course.passed(SEMESTER_NUMBER)
        failed = course.failed(SEMESTER_NUMBER)
        total = passed + failed

        sections = {}
        for grade in grades:
            section = grade.class_attr

            if section not in sections:
                sections[section] = {
                    'grades': [],
                    'title': grade.class_attr,
                    'passed': 0,
                    'failed': 0,
                    'total': 0,
                    'passing_rate': 0,
                }

            sections[section]['grades'].append(grade)

            sections[section]['total'] += 1
            if grade.passing():
                sections[section]['passed'] += 1
            else:
                sections[section]['failed'] += 1

        for section in sections:
            sections[section]['passing_rate'] = 0.0 if sections[section]['total'] == 0 else sections[section]['passed'] / sections[section]['total'] * 100.0

        courses_data.append({
            'name': course.name,
            'grades': grades,
            'sections': sections,
            'passed': passed,
            'failed': failed,
            'total': total,
            'passing_rate': 0.0 if total == 0 else passed / total * 100.0,
            'must_take': takers,
            'must_take_count': len(takers),
        })

    data['courses'] = courses_data

    return render(request, 'index.html', data)


def ge(request):
    data = {}

    ges = [
        'Chem 1',
        'Math 1',
        'Physics 10',
        'Nat Sci 1',
        'Math 2',
    ]
    ges = [Course.objects.get(name=ge_name) for ge_name in ges]
    ge_data = []
    students = {}

    for ge in ges:
        ge_students = [i for i in Student.objects.filter(degree_program='BS Computer Science') if i.active() and i.has_passed(ge)]

        for student in ge_students:
            students.setdefault(student, []).append(ge.name)

        ge_data.append({
            'course': ge,
            'students': ge_students,
        })

    sorted_students = []
    for student in sorted(students, key=lambda a: str(a)):
        sorted_students.append((str(student), ', '.join(students[student])))

    data['students'] = sorted_students
    data['ge_data'] = ge_data

    
    return render(request, 'ge.html', data)


def bypassed_191_rule(request):
    cs32 = Course.objects.get(name="CS 32")
    cs191 = Course.objects.get(name="CS 191")
    cs191grades = Grade.objects.filter(class_attr__course=cs191, student__degree_program="BS Computer Science")

    not_junior = []
    not_half_units = []
    not_all_core = []
    no_cs32 = []
    output = []

    for grade in cs191grades:
        s = grade.student
        sem = grade.class_attr.semester
        sem_before = sem.before()

        info = s.junior_info(semester=sem_before)
        is_junior = info['is_junior']
        units = int(info['units_credited'])
        passed_all_first_half = info['passed_all_first_half']
        cs32_passed = True

        if not passed_all_first_half:
            not_all_core.append(s)

        if not s.has_passed(cs32, semester=sem):
            no_cs32.append(s)
            cs32_passed = False

        if not is_junior:
            not_junior.append(s)
            output.append((
                str(s),
                units,
                "Yes" if units >= 73 else "",
                "Yes" if units >= 70 else "",
                "Yes" if units >= 67 else "",
                "Yes" if units >= 60 else "",
                "Yes" if units >= 57 else "",
            ))

    total = []

    for i in range(len(output[0])):
        total.append(str(len([True for k in output if k[i]])))

    data = {}

    data['output'] = sorted(output)
    data['not_junior'] = not_junior
    data['not_half_units'] = not_half_units
    data['not_all_core'] = not_all_core
    data['no_cs32'] = no_cs32
    data['total'] = total

    return render(request, '191.html', data)


def standing(request):
    data = {}

    info = []

    #for student in Student.bscs.all():
    for student in [i for i in Student.bscs.all() if i.active()]:
        print(student)
        d = student.standing_info()
        d['sid'] = student.sid
        d['last_name'] = student.last_name
        d['first_name'] = student.first_name

        info.append(d)

    data['info'] = info

    return render(request, 'standing.html', data)

def must_take_191(request):
    data = {}

    info = []

    for student in [i for i in Student.bscs.all() if i.active()]:
        print(student)
        d = student.standing_info()
        d['sid'] = student.sid
        d['last_name'] = student.last_name
        d['first_name'] = student.first_name

        if d['must_take_191']:
            info.append(d)

    info = sorted(info, key=lambda a: (a['standing'], a['waive_junior'], a['experiment']))

    data['info'] = info

    return render(request, 'must_take_191.html', data)

def not_covered(request):
    data = {}

    info = []

    for student in [i for i in Student.bscs.all() if i.active()]:
        print(student)
        d = student.standing_info()

        d['sid'] = student.sid
        d['last_name'] = student.last_name
        d['first_name'] = student.first_name
        d['kwatro135'] = ""
        d['failed_cs11'] = ""
        d['failed_cs12'] = ""
        d['failed_cs21'] = ""
        d['failed_cs30'] = ""
        d['failed_cs32'] = ""
        d['failed_cs133'] = ""
        d['failed_cs135'] = ""
        d['failed_cs140'] = ""
        d['failed_cs150'] = ""
        d['failed_math17'] = ""
        d['failed_math53'] = ""
        d['failed_math54'] = ""
        d['failed_math55'] = ""

        if d['denied_191'] and not d['experiment']:
            if student.grade_set.filter(grade="4.00", class_attr__semester__number=162, class_attr__course__name="CS 135"):
                d['kwatro135'] = "X"
            if [i for i in student.grade_set.filter(class_attr__course__name="CS 11") if not i.passing()]:
                d['failed_cs11'] = "X"
            if [i for i in student.grade_set.filter(class_attr__course__name="CS 12") if not i.passing()]:
                d['failed_cs12'] = "X"
            if [i for i in student.grade_set.filter(class_attr__course__name="CS 21") if not i.passing()]:
                d['failed_cs21'] = "X"
            if [i for i in student.grade_set.filter(class_attr__course__name="CS 30") if not i.passing()]:
                d['failed_cs30'] = "X"
            if [i for i in student.grade_set.filter(class_attr__course__name="CS 32") if not i.passing()]:
                d['failed_cs32'] = "X"
            if [i for i in student.grade_set.filter(class_attr__course__name="CS 133") if not i.passing()]:
                d['failed_cs133'] = "X"
            if [i for i in student.grade_set.filter(class_attr__course__name="CS 135") if not i.passing()]:
                d['failed_cs135'] = "X"
            if [i for i in student.grade_set.filter(class_attr__course__name="CS 140") if not i.passing()]:
                d['failed_cs140'] = "X"
            if [i for i in student.grade_set.filter(class_attr__course__name="CS 150") if not i.passing()]:
                d['failed_cs150'] = "X"
            if [i for i in student.grade_set.filter(class_attr__course__name="Math 17") if not i.passing()]:
                d['failed_math17'] = "X"
            if [i for i in student.grade_set.filter(class_attr__course__name="Math 53") if not i.passing()]:
                d['failed_math53'] = "X"
            if [i for i in student.grade_set.filter(class_attr__course__name="Math 54") if not i.passing()]:
                d['failed_math54'] = "X"
            if [i for i in student.grade_set.filter(class_attr__course__name="Math 55") if not i.passing()]:
                d['failed_math55'] = "X"

            info.append(d)

    info = sorted(info, key=lambda a: (a['waive_junior'], a['experiment'], a['total_failed'], a['failed_csmath_count'], a['kwatro135']))

    data['info'] = info

    return render(request, 'experiment.html', data)

def experiment(request):
    data = {}

    info = []

    for student in [i for i in Student.bscs.all() if i.active()]:
        print(student)
        d = student.standing_info()
        d['sid'] = student.sid
        d['last_name'] = student.last_name
        d['first_name'] = student.first_name
        d['kwatro135'] = ""
        d['failed_cs11'] = ""
        d['failed_cs12'] = ""
        d['failed_cs21'] = ""
        d['failed_cs30'] = ""
        d['failed_cs32'] = ""
        d['failed_cs133'] = ""
        d['failed_cs135'] = ""
        d['failed_cs140'] = ""
        d['failed_cs150'] = ""
        d['failed_math17'] = ""
        d['failed_math53'] = ""
        d['failed_math54'] = ""
        d['failed_math55'] = ""

        if d['waive_junior'] or d['experiment']:
            if student.grade_set.filter(grade="4.00", class_attr__semester__number=162, class_attr__course__name="CS 135"):
                d['kwatro135'] = "X"
            if [i for i in student.grade_set.filter(class_attr__course__name="CS 11") if not i.passing()]:
                d['failed_cs11'] = "X"
            if [i for i in student.grade_set.filter(class_attr__course__name="CS 12") if not i.passing()]:
                d['failed_cs12'] = "X"
            if [i for i in student.grade_set.filter(class_attr__course__name="CS 21") if not i.passing()]:
                d['failed_cs21'] = "X"
            if [i for i in student.grade_set.filter(class_attr__course__name="CS 30") if not i.passing()]:
                d['failed_cs30'] = "X"
            if [i for i in student.grade_set.filter(class_attr__course__name="CS 32") if not i.passing()]:
                d['failed_cs32'] = "X"
            if [i for i in student.grade_set.filter(class_attr__course__name="CS 133") if not i.passing()]:
                d['failed_cs133'] = "X"
            if [i for i in student.grade_set.filter(class_attr__course__name="CS 135") if not i.passing()]:
                d['failed_cs135'] = "X"
            if [i for i in student.grade_set.filter(class_attr__course__name="CS 140") if not i.passing()]:
                d['failed_cs140'] = "X"
            if [i for i in student.grade_set.filter(class_attr__course__name="CS 150") if not i.passing()]:
                d['failed_cs150'] = "X"
            if [i for i in student.grade_set.filter(class_attr__course__name="Math 17") if not i.passing()]:
                d['failed_math17'] = "X"
            if [i for i in student.grade_set.filter(class_attr__course__name="Math 53") if not i.passing()]:
                d['failed_math53'] = "X"
            if [i for i in student.grade_set.filter(class_attr__course__name="Math 54") if not i.passing()]:
                d['failed_math54'] = "X"
            if [i for i in student.grade_set.filter(class_attr__course__name="Math 55") if not i.passing()]:
                d['failed_math55'] = "X"

            info.append(d)

    info = sorted(info, key=lambda a: (a['waive_junior'], a['experiment'], a['total_failed'], a['failed_csmath_count'], a['kwatro135']))

    data['info'] = info

    return render(request, 'experiment.html', data)


def immortal(request):
    data = {}

    info = []

    for student in [i for i in Student.bscs.all() if i.active()]:
        print(student)
        d = student.standing_info()
        d['sid'] = student.sid
        d['last_name'] = student.last_name
        d['first_name'] = student.first_name
        d['batch'] = student.batch()
        d['passed_cs130'] = ""
        d['passed_cs133'] = ""
        d['passed_cs135'] = ""
        d['passed_cs140'] = ""
        d['passed_cs191'] = ""

        if [i for i in student.grade_set.filter(class_attr__course__name="CS 130") if i.passing()]:
            d['passed_cs130'] = "Y"
        if [i for i in student.grade_set.filter(class_attr__course__name="CS 133") if i.passing()]:
            d['passed_cs133'] = "Y"
        if [i for i in student.grade_set.filter(class_attr__course__name="CS 135") if i.passing()]:
            d['passed_cs135'] = "Y"
        if [i for i in student.grade_set.filter(class_attr__course__name="CS 140") if i.passing()]:
            d['passed_cs140'] = "Y"
        if [i for i in student.grade_set.filter(class_attr__course__name="CS 191") if i.passing()]:
            d['passed_cs191'] = "Y"

        d['subject_immortality'] = 'Y' if d['immortal'] else ''
        d['dean_immortality'] = 'Y' if d['units_left'] <= 30 else ''
        d['immortal'] = "Y" if d['subject_immortality'] or d['dean_immortality'] else ""
        d['ah_left'] = 15 - d['ah_credited']
        d['ssp_left'] = 15 - d['ssp_credited']
        d['mst_left'] = 12 - d['mst_credited']
        d['eng_left'] = 9 - d['eng_credited']
        d['ph_left'] = 6 - d['ph_credited']

        d['cs_elective'] = d['cs_elective'].name if d['cs_elective'] else ""
        d['mse_elective'] = d['mse_elective'] if d['mse_elective'] else ""
        d['free_elective'] = d['free_elective'].name if d['free_elective'] else ""

        info.append(d)

    info = sorted(info, key=lambda a: (a['last_name'], a['first_name']))

    data['info'] = info

    return render(request, 'immortal.html', data)

def gwa(request):
    data = {}

    info = []

    for student in [i for i in Student.bscs.all() if i.active()]:
        print(student)

        d = student.standing_info()
        d['sid'] = student.sid
        d['last_name'] = student.last_name
        d['first_name'] = student.first_name
        d['batch'] = student.batch()
        
        
        credited = d['credited']

        numerator = 0.0
        denominator = 0.0
        for course in credited:
            for grade in student.grades(course):
                try:
                    units = int(course.units)
                    numerator += float(grade) * units
                    denominator += units
                except ValueError:
                    pass

        if denominator == 0:
            continue

        d['gwa'] = round(numerator / denominator, 4)
        d['gwa_units'] = denominator

        info.append(d)

    data['info'] = info

    return render(request, 'gwa.html', data)

def batch_render(request, active):
    data = {}

    info = {}

    if active:
        students = [i for i in Student.bscs.all() if i.active()]
    else:
        students = [i for i in Student.bscs.all()]

    for student in students:
        d = {}

        d['sid'] = student.sid
        d['last_name'] = student.last_name
        d['first_name'] = student.first_name

        batch = student.batch()
        d['batch'] = batch

        if batch not in info:
            info[batch] = []

        info[batch].append(d)

    sorted_info = []
    for key in sorted(info):
        sorted_info.append((key, sorted(info[key], key=lambda x: (x['last_name'], x['first_name']))))

    data['info'] = sorted_info

    return render(request, 'batch.html', data)

def batch(request):
    return batch_render(request, active=True)

def batch_all(request):
    return batch_render(request, active=False)

def batch(request):
    data = {}

    info = {}

    for student in [i for i in Student.bscs.all() if i.active()]:
    #for student in [i for i in Student.bscs.all()]:
        d = {}

        d['sid'] = student.sid
        d['last_name'] = student.last_name
        d['first_name'] = student.first_name

        batch = student.batch()
        d['batch'] = batch

        if batch not in info:
            info[batch] = []

        info[batch].append(d)

    sorted_info = []
    for key in sorted(info):
        sorted_info.append((key, sorted(info[key], key=lambda x: (x['last_name'], x['first_name']))))

    data['info'] = sorted_info

    return render(request, 'batch.html', data)

def generate(request):
    data = {}

    info = []
    
    comm3fil = Course.objects.get(name="Comm 3 Fil")
    comm3eng = Course.objects.get(name="Comm 3 Eng")

    eng1 = Course.objects.get(name="Eng 1")
    philo1 = Course.objects.get(name="Philo 1")
    eng10 = Course.objects.get(name="Eng 10")
    fil40 = Course.objects.get(name="Fil 40")
    kas1 = Course.objects.get(name="Kas 1")
    sts = Course.objects.get(name="STS")

    cs11 = Course.objects.get(name="CS 11")
    cs12 = Course.objects.get(name="CS 12")
    cs21 = Course.objects.get(name="CS 21")
    cs30 = Course.objects.get(name="CS 30")
    cs32 = Course.objects.get(name="CS 32")
    cs130 = Course.objects.get(name="CS 130")
    cs131 = Course.objects.get(name="CS 131")
    cs133 = Course.objects.get(name="CS 133")
    cs135 = Course.objects.get(name="CS 135")
    cs140 = Course.objects.get(name="CS 140")
    cs145 = Course.objects.get(name="CS 145")
    cs150 = Course.objects.get(name="CS 150")
    cs153 = Course.objects.get(name="CS 153")
    cs165 = Course.objects.get(name="CS 165")
    cs180 = Course.objects.get(name="CS 180")
    cs191 = Course.objects.get(name="CS 191")
    cs192 = Course.objects.get(name="CS 192")
    cs194 = Course.objects.get(name="CS 194")
    cs195 = Course.objects.get(name="CS 195")
    cs196 = Course.objects.get(name="CS 196")
    cs198 = Course.objects.get(name="CS 198")
    cs199 = Course.objects.get(name="CS 199")
    math17 = Course.objects.get(name="Math 17")
    math53 = Course.objects.get(name="Math 53")
    math54 = Course.objects.get(name="Math 54")
    math55 = Course.objects.get(name="Math 55")

    physics71 = Course.objects.get(name="Physics 71")
    physics72 = Course.objects.get(name="Physics 72")
    stat130 = Course.objects.get(name="Stat 130")
    pi100 = Course.objects.get(name="PI 100")

    shortcut = {}

    shortcut['comm3'] = comm3eng

    shortcut['eng1'] = eng1
    shortcut['philo1'] = philo1
    shortcut['eng10'] = eng10
    shortcut['fil40'] = fil40
    shortcut['kas1'] = kas1
    shortcut['sts'] = sts

    shortcut['math17'] = math17
    shortcut['math53'] = math53
    shortcut['math54'] = math54
    shortcut['math55'] = math55

    shortcut['cs11'] = cs11
    shortcut['cs12'] = cs12
    shortcut['cs21'] = cs21
    shortcut['cs30'] = cs30
    shortcut['cs32'] = cs32
    shortcut['cs130'] = cs130
    shortcut['cs131'] = cs131
    shortcut['cs133'] = cs133
    shortcut['cs135'] = cs135
    shortcut['cs140'] = cs140
    shortcut['cs145'] = cs145
    shortcut['cs150'] = cs150
    shortcut['cs153'] = cs153
    shortcut['cs165'] = cs165
    shortcut['cs180'] = cs180
    shortcut['cs191'] = cs191
    shortcut['cs192'] = cs192
    shortcut['cs194'] = cs194
    shortcut['cs195'] = cs195
    shortcut['cs196'] = cs196
    shortcut['cs198'] = cs198
    shortcut['cs199'] = cs199

    shortcut['physics71'] = physics71
    shortcut['physics72'] = physics72
    shortcut['stat130'] = stat130
    shortcut['pi100'] = pi100

    periods = {}
    items = {}

    def make_item(course, course_key, period_num):
        if period_num not in periods:
            periods[period_num] = []

        periods[period_num].append(course)
        items[course_key] = period_num

    make_item(cs11, 'cs11', 11)
    make_item(math17, 'math17', 11)

    make_item(cs12, 'cs12', 12)
    make_item(cs30, 'cs30', 12)
    make_item(math53, 'math53', 12)

    make_item(cs21, 'cs21', 21)
    make_item(cs32, 'cs32', 21)
    make_item(cs133, 'cs133', 21)
    make_item(math54, 'math54', 21)

    make_item(cs135, 'cs135', 22)
    make_item(cs140, 'cs140', 22)
    make_item(cs150, 'cs150', 22)
    make_item(math55, 'math55', 22)
    make_item(physics71, 'physics71', 22)

    make_item(cs130, 'cs130', 31)
    make_item(cs165, 'cs165', 31)
    make_item(cs191, 'cs191', 31)
    make_item(stat130, 'stat130', 31)

    make_item(cs131, 'cs131', 32)
    make_item(cs145, 'cs145', 32)
    make_item(cs153, 'cs153', 32)
    make_item(cs180, 'cs180', 32)
    make_item(cs192, 'cs192', 32)
    make_item(cs192, 'cs194', 32)

    make_item(cs195, 'cs195', 33)

    make_item(cs198, 'cs198', 41)
    make_item(physics72, 'physics72', 41)

    make_item(cs196, 'cs196', 42)
    make_item(cs199, 'cs199', 42)
    make_item(pi100, 'pi100', 42)

    for student in [i for i in Student.bscs.all() if i.active()]:
        d = {}

        d['sid'] = student.sid
        d['last_name'] = student.last_name
        d['first_name'] = student.first_name
        d['batch'] = student.batch()

        """
        if d['batch'] != "2016":
            continue
        """

        print(student)

        si = student.standing_info()

        d['credited'] = int(si['units_credited'])
        d['left'] = int(si['units_left'])

        d['status'] = "Delayed" if (73 - d['left']) >= 26 else "On time"

        d['junior'] = 'N'
        d['senior'] = 'N'
        
        if si['standing'] in ['JUNIOR', 'SENIOR']:
            d['junior'] = 'Y'

        if si['standing'] == 'SENIOR':
            d['senior'] = 'Y'

        d['junior_units'] = int(73 - si['units_credited'])
        if d['junior_units'] <= 0:
            d['junior_units'] = ""

        d['senior_units'] = int(110 - si['units_credited'])
        if d['senior_units'] <= 0:
            d['senior_units'] = ""

        d['credited_list'] = si['credited_names'].replace(",", ", ")
        d['not_credited_list'] = si['not_credited_names'].replace(",", ", ")

        d['cse'] = si['cs_elective'].name if si['cs_elective'] else ""
        d['mse'] = si['mse_elective'].name if si['mse_elective'] else ""
        d['free'] = si['free_elective'].name if si['free_elective'] else ""

        d['ah_left'] = int(15 - si['ah_credited'])
        d['ssp_left'] = int(15 - si['ssp_credited'])
        d['mst_left'] = int(12 - si['mst_credited'])

        d['core_required_list'] = si['needed_core_names'].replace(",", ", ")

        d['required_ges'] = []

        required_ge_mapping = {
            "comm3": "Comm 3",
            "eng10": "Eng 10",
            "fil40": "Fil 40",
            "philo1": "Philo 1",
            "kas1": "Kas 1",
            "sts": "STS",
            "eng1": "Eng 1",
        }
        for key in ("comm3", "eng10", "fil40", "philo1", "kas1", "sts", "eng1"):
            if not si["passed_" + key]:
                d['required_ges'].append(required_ge_mapping[key])

        d['required_ges'] = ', '.join(d['required_ges'])
        d['passed_pe_list'] = si['passed_pe_list'].replace(",", ", ")
        d['passed_ah_names'] = si['passed_ah_names']
        d['passed_ssp_names'] = si['passed_ssp_names']
        d['passed_mst_names'] = si['passed_mst_names']

        inner = {}

        for key, course in shortcut.items():
            if student.has_passed(course):
                inner[key] = "D"
            elif key == 'comm3' and student.has_passed(comm3fil):
                inner[key] = "D"
            elif key in ('eng1', 'fil40', 'eng10', 'kas1', 'sts', 'comm3', 'philo1'):
                inner[key] = "G"
            elif student.can_take(course):
                current_period_num = 0
                if d['batch'] == "2017":
                    current_period_num = 12
                elif d['batch'] == "2016":
                    current_period_num = 22
                elif d['batch'] == "2015":
                    current_period_num = 32
                else:
                    current_period_num = 42

                if items[key] == current_period_num:
                    inner[key] = "M"
                elif items[key] < current_period_num:
                    inner[key] = "F"
                else:
                    inner[key] = "C"
            else:
                inner[key] = "X"

        inner['cse'] = "D" if d['cse'] else "E"
        inner['mse'] = "D" if d['mse'] else "E"
        inner['free'] = "D" if d['free'] else "E"

        passed_eng1 = si['passed_eng1'] == "Y"
        passed_eng10 = si['passed_eng10'] == "Y"
        passed_fil40 = si['passed_fil40'] == "Y"
        passed_comm3 = si['passed_comm3'] == "Y"
        passed_kas1 = si['passed_kas1'] == "Y"
        passed_philo1 = si['passed_philo1'] == "Y"
        passed_sts = si['passed_sts'] == "Y"
        
        free_ah = int(si['ah_credited']) // 3 - passed_eng1 - passed_eng10 - passed_fil40 - passed_comm3
        free_ssp = int(si['ssp_credited']) // 3 - passed_kas1 - passed_philo1
        free_mst = int(si['mst_credited']) // 3 - passed_sts

        for i in range(1, 6):
            inner['ah' + str(i)] = 'G'
            inner['ssp' + str(i)] = 'G'
            inner['mst' + str(i)] = 'G'

        for i in range(1, free_ah + 1):
            inner['ah' + str(i)] = 'D' if i <= free_ah else 'G'

        for i in range(1, free_ssp + 1):
            inner['ssp' + str(i)] = 'D' if i <= free_ssp else 'G'

        for i in range(1, free_mst + 1):
            inner['mst' + str(i)] = 'D' if i <= free_mst else 'G'

        pe = si['passed_pe_count']
        for i in range(1, 5):
            inner['pe' + str(i)] = 'D' if i <= pe else 'G'

        inner['nstp1'] = "D" if si['passed_nstp1'] else "G"
        inner['nstp2'] = "D" if si['passed_nstp2'] else "G"

        d['data'] = inner

        with open(os.path.join("json", str(d['sid'])), "w") as f:
            f.write(json.dumps(d))

    answer = ""
    while not answer:
        answer = input("Update live copy [y/N]? ").lower()

    if answer == "y":
        print("Compressing...")
        os.system("cd json && tar -cz * > ../json.tar.gz")

        print("Deleting old data...")
        os.system('ssh -t git@jfmcoronel.com "rm batch2016/*"')

        print("Transferring archive...")
        os.system("scp json.tar.gz git@jfmcoronel.com:batch2016/")

        print("Extracting archive...")
        os.system('ssh -t git@jfmcoronel.com "cd batch2016 && tar -zxf json.tar.gz && rm json.tar.gz"')

        print("Done!")

    return render(request, 'batch.html', data)
