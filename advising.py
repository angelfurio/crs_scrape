import os
import sys
import re
import glob

from crscraper import EnlistmentScraper
from lxml import html

import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "upac.settings")
django.setup()

from django.contrib.auth.models import User

from core.models import *

errors = {}
semester_cache = {}
course_cache = {}
class_cache = {}
faculty_cache = {}

def main():
    if len(sys.argv) not in [1, 2]:
        print("Usage: python3", sys.argv[0], "<directory_path>")
        return

    if len(sys.argv) == 2:
        DATA_DIR = sys.argv[1]
    else:
        DATA_DIR = "scraping/crscraper/__data__/advising"

    grades = []

    filepaths = sorted(glob.glob(os.path.join(DATA_DIR, "*.html")))
    current = 0
    total = len(filepaths)
    for filepath in filepaths:
        studentnumber = os.path.splitext(os.path.basename(filepath))[0]

        current += 1
        print(studentnumber, "{current}/{total} ({percent}%)".format(current=current, total=total, percent=current/total*100))

        data = EnlistmentScraper(filepath).parse()

        if not data.get('error'):
            create_objects(data)
        else:
            errors.setdefault(data['status'], []).append(studentnumber)

    print("ERRORS", sum(len(i) for i in errors.values()))
    print(errors)


def create_objects(data):
    try:
        student = Student.objects.get(sid=data['sid'])
    except Student.DoesNotExist:
        student = Student()
        student.first_name = data['first_name']
        student.last_name = data['last_name']
        student.sid = int(data['sid'])
        student.degree_program = data['degree_program']
        student.save()

    semester = cache_retrieve(semester_cache, data['semester'], get_or_create_semester, data)

    enlistment = create_enlistment(data, student, semester)
    add_classes(data['classes'], student, semester, enlistment)

def create_enlistment(data, student, semester):
    e = Enlistment()

    e.student = student
    e.semester = semester
    e.priority = data['priority']
    e.eligibility = data['eligibility']
    e.accountability = data['accountability']

    e.save()

    return e

def add_classes(classes_data, student, semester, enlistment):
    classes = []

    for class_data in classes_data:
        schedule = class_data['schedule']
        code = class_data['code']
        section = class_data['section']
        units = class_data['units']
        course_name = class_data['course']

        # TODO: support brand-new courses
        course = cache_retrieve(course_cache, course_name, get_or_create_course, class_data)
        class_ = cache_retrieve(class_cache, (section, semester, course, code), get_or_create_class, {
            'class_data': class_data,
            'course': course,
            'semester': semester,
        })

        classes.append(class_)

    for class_ in classes:
        enlistment.classes.add(class_)

    enlistment.save()

def cache_retrieve(cache, key, callback, callback_data):
    if cache.get(key):
        return cache[key]
    else:
        value = callback(callback_data)
        cache[key] = value

        return value

def get_or_create_semester(data):
    name = data['semester']
    number = data['number']

    semester_filter = Semester.objects.filter(name=name)

    if semester_filter:
        return semester_filter[0]
    else:
        semester = Semester()
        semester.name = name
        semester.number = number
        semester.save()

        return semester

def get_or_create_course(class_data):
    course_name = class_data['course']
    units_text = class_data['units']

    affects_gwa = '(' not in units_text
    units = float(units_text.replace('(', '').replace(')', ''))

    course_filter = Course.objects.filter(name=course_name, units=units)
    if course_filter:
        return course_filter[0]
    else:
        course = Course()
        course.name = course_name
        course.units = units
        course.affects_gwa = affects_gwa
        course.save()

        return course

def get_or_create_faculty(faculty_name):
    faculty_filter = Faculty.objects.filter(name=faculty_name)
    if faculty_filter:
        return faculty_filter[0]
    else:
        faculty = Faculty()
        faculty.name = faculty_name
        faculty.save()

        return faculty

def get_or_create_class(data):
    course = data['course']
    semester = data['semester']

    class_data = data['class_data']
    section = class_data['section']
    code = class_data['code']

    class_filter = Class.objects.filter(section=section, code=code, semester=semester, course=course)
    if class_filter:
        return class_filter[0]
    else:
        class_ = Class()
        class_.section = section
        class_.code = code
        class_.semester = semester
        class_.course = course
        class_.save()

        faculty_list = [cache_retrieve(faculty_cache, name, get_or_create_faculty, name) for name in class_data['faculty']]

        for faculty in faculty_list:
            class_.faculty.add(faculty)

        return class_

if __name__ == "__main__":
    main()
