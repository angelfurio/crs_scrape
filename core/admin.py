from django.contrib import admin

from core.models import Student, Semester, Enrollment, Faculty, Course, Class, Grade


admin.site.register(Student)
admin.site.register(Semester)
admin.site.register(Enrollment)
admin.site.register(Faculty)
admin.site.register(Course)
admin.site.register(Class)
admin.site.register(Grade)
