import os
import sys
import re
import glob

import crscraper
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
        DATA_DIR = "scraping/crscraper/__data__/grades"

    grades = []

    filepaths = sorted(glob.glob(os.path.join(DATA_DIR, "*.html")), reverse=True)
    current = 0
    total = len(filepaths)
    for filepath in filepaths:
        studentnumber = os.path.splitext(os.path.basename(filepath))[0]

        current += 1
        print(studentnumber, "{current}/{total} ({percent}%)".format(current=current, total=total, percent=current/total*100))

        data = crscraper.from_file(filepath)

        if not data.get('error'):
            create_objects(data)
        else:
            errors.setdefault(data['status'], []).append(studentnumber)

    print("ERRORS", sum(len(i) for i in errors.values()))
    print(errors)

    print("Adding hardcoded prerequisites...")
    add_prerequisites()

    print("Adding hardcoded substitutes...")
    add_substitutes()


def create_objects(data):
    student = create_student(data)
    process_semester_cache(data, student)

def create_student(data):
    # TODO: move to model manager
    student = Student()
    student.first_name = data['first_name']
    student.last_name = data['last_name']
    student.sid = data['sid']
    student.degree_program = data['degree_program']
    student.save()

    return student

def cache_retrieve(cache, key, callback, callback_data):
    if cache.get(key):
        return cache[key]
    else:
        value = callback(callback_data)
        cache[key] = value

        return value

def process_semester_cache(data, student):
    for semester_data in data['semesters']:
        process_semester(semester_data, student)

def process_semester(semester_data, student):
    name = semester_data['semester']
    status = semester_data['status']

    semester = cache_retrieve(semester_cache, name, get_or_create_semester, semester_data)
    e = Enrollment()
    e.student = student
    e.semester = semester
    e.status = status
    e.save()

    process_semester_grades(semester_data['grades'], semester, student)

def get_or_create_semester(semester_data):
    name = semester_data['semester']
    semester_filter = Semester.objects.filter(name=name)

    if semester_filter:
        return semester_filter[0]
    else:
        semester = Semester()
        semester.name = name
        semester.number = semester_data['number']
        semester.save()

        return semester

def process_semester_grades(grades_data, semester, student):
    for grade_data in grades_data:
        course_name = grade_data['course']
        section = grade_data['section']
        grade = grade_data['grade']

        course = cache_retrieve(course_cache, course_name, get_or_create_course, grade_data)
        class_ = cache_retrieve(class_cache, (section, semester, course), get_or_create_class, {
            'grade_data': grade_data,
            'course': course,
            'semester': semester,
        })

        g = Grade()
        g.class_attr = class_
        g.grade = grade
        g.student = student
        g.save()

def get_or_create_course(grade_data):
    course_name = grade_data['course']
    units_text = grade_data['units']

    affects_gwa = '(' not in units_text
    units = float(units_text.replace('(', '').replace(')', ''))

    course_filter = Course.objects.filter(name=course_name, units=units)
    if course_filter:
        return course_filter[0]
    else:
        course = Course()
        course.name = course_name
        if course_name.startswith("PE "):
            course.units = 0
        elif any((course_name.startswith(i) for i in ('CWTS', 'ROTC Mil Sci ', 'LTS ', 'NSTP Common Module'))):
            course.units = 0
        else:
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

    grade_data = data['grade_data']
    section = grade_data['section']
    code = grade_data['code']

    class_filter = Class.objects.filter(section=section, code=code, semester=semester, course=course)
    if class_filter:
        return course_filter[0]
    else:
        faculty_list = []
        faculty_name_list = grade_data['faculty']

        for faculty_name in faculty_name_list:
            faculty = cache_retrieve(faculty_cache, faculty_name, get_or_create_faculty, faculty_name)
            faculty_list.append(faculty)

        class_ = Class()
        class_.section = section
        class_.code = code
        class_.semester = semester
        class_.course = course
        class_.save()

        for faculty in faculty_list:
            class_.faculty.add(faculty)

        return class_

def add_prerequisites():
    add_prerequisite('Math 53', 'Math 17')
    add_prerequisite('Math 54', 'Math 53')
    add_prerequisite('Math 55', 'Math 54')
    add_prerequisite('CS 12', 'CS 11')
    add_prerequisite('CS 21', 'CS 12')
    add_prerequisite('CS 30', 'Math 17')
    add_prerequisite('CS 32', 'CS 12')
    add_prerequisite('CS 130', 'Math 55')
    add_prerequisite('CS 131', 'CS 130')
    add_prerequisite('CS 135', 'CS 30')
    add_prerequisite('CS 133', 'CS 30')
    add_prerequisite('CS 135', 'CS 32')
    add_prerequisite('CS 140', 'CS 21')
    add_prerequisite('CS 145', 'CS 140')
    add_prerequisite('CS 150', 'CS 32')
    add_prerequisite('CS 153', 'CS 140')
    add_prerequisite('CS 165', 'CS 135')
    add_prerequisite('CS 180', 'CS 32')
    add_prerequisite('CS 191', 'CS 32')
    add_prerequisite('CS 192', 'CS 191')
    add_prerequisite('CS 195', 'CS 192')
    add_prerequisite('CS 198', 'CS 192')
    add_prerequisite('CS 199', 'CS 198')

    add_prerequisite('Stat 130', 'Math 55')

def add_prerequisite(base_name, prereq_name):
    print("Adding", base_name, "prerequisite:", prereq_name)

    base = Course.objects.get(name=base_name)
    prereq = Course.objects.get(name=prereq_name)

    base.prerequisites.add(prereq)

def add_substitutes():
    # CS from other UP units
    add_substitute('CS 11', 'CS 12')
    add_substitute('CS 11', 'CS 32')

    # CS from EEE
    add_substitute('CS 11', 'EEE 11')

    # Math from other UP units
    add_substitute('Math 17', 'Math 53')
    add_substitute('Math 17', 'Math 54')
    add_substitute('Math 17', 'CS 130')

    # BS Math
    add_substitute('Math 17', 'Math 60')
    add_substitute('Math 53', 'Math 63')
    add_substitute('Math 54', 'Math 64')

    # Pre-2010 curriculum
    add_substitute('CS 191', 'CS 192')
    add_substitute('CS 153', 'EEE 8')
    add_substitute('CS 195', 'EEE 8')

def add_substitute(base_name, sub_name):
    print("Adding", base_name, "substitute:", sub_name)

    base = Course.objects.get(name=base_name)
    sub = Course.objects.get(name=sub_name)

    base.substitutes.add(sub)

if __name__ == "__main__":
    main()
