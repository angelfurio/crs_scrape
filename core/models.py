import itertools

from django.db import models
from django.db.models import Q

class BSCSManager(models.Manager):
    def get_queryset(self):
        return super(BSCSManager, self).get_queryset().filter(degree_program="BS Computer Science")

class Student(models.Model):
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    sid = models.IntegerField(unique=True)
    degree_program = models.CharField(max_length=50)

    objects = models.Manager()
    bscs = BSCSManager()

    def active(self):
        s171 = Enrollment.objects.filter(student=self, semester=Semester.objects.get(number=171)).exclude(status='VSO').count()

        if s171:
            return True

        vso_last_sem = Enrollment.objects.filter(student=self, semester=Semester.objects.get(number=171), status='VSO').count()

        if vso_last_sem:
            return False

        return Enrollment.objects.filter(student=self, semester=Semester.objects.get(number=172)).exclude(status='VSO').count()
    
    def batch(self):
        def convert(x):
            return '20' + str(x.number).zfill(3)[:-1]

        cs11_sem = self.first_take_sem("CS 11")
        cs12_sem = self.first_take_sem("CS 12")
        cs32_sem = self.first_take_sem("CS 32")
        math17_sem = self.first_take_sem("Math 17")

        if not cs11_sem and not cs12_sem and not cs32_sem:
            # No CS 11 yet; error
            print("\t\t*\tERROR - NO CS 11/12/32", self)
            return "?"
        elif cs11_sem and cs11_sem == math17_sem:
            # Most likely regular BS CS student or non-UP unit transferee
            # TODO: handle Math APE
            return convert(cs11_sem)
        elif not math17_sem and cs11_sem:
            # Skipped Math 17
            # Most likely UP unit transferee
            return convert(cs11_sem)
        else:
            # Most likely shiftee
            if cs11_sem:
                suffix = str(cs11_sem.number)[-1]

                if suffix == '1':
                    print("1ST SEM SHIFTEE WITH CS 11\t", cs11_sem.number, self)
                elif suffix == '2':
                    print("\t2ND SEM SHIFTEE WITH CS 11\t", cs11_sem.number, self)

                return convert(cs11_sem)
            elif cs12_sem:
                suffix = str(cs12_sem.number)[-1]

                if suffix == '1':
                    # First CS 12 taken during 1st sem
                    # Probably EEE 1st sem shiftee
                    # Batch is minus one year
                    # Case covers midyear CS 12 (<year-1>4)

                    # Count units passed during CS 12 sem for Daling exception
                    # FIXME: ensure no x.5 units
                    #if (sum([int(i.class_attr.course.units) for i in Grade.objects.filter(student=self, class_attr__semester=cs12_sem)]) == 6):

                    if self.sid in [201502929, 201481817]:
                        print("\t\t\t*\tEXCEPTION - HARDCODED 2016\t", self)
                        return "2016"

                    print("\t*\tSHIFTEE WITH EQUIVALENT CS 11 AND 1ST SEM CS 12\t", cs12_sem.number, self)
                    return '20' + str(cs12_sem.number // 10 - 1).zfill(2)
                else:
                    return convert(cs12_sem)
            else:
                if cs32_sem:
                    print("\t\t\t*\tWARNING - SHIFTEE STRAIGHT TO CS 32\t", self)
                    return convert(cs32_sem)
                else:
                    # Error
                    print("\t\t\t*\tERROR - SHIFTEE WITH NO CS 11/12/32\t", self)
                    return "?"

        return 1
    
    def first_take_sem(self, course):
        if type(course) == str:
            course = Course.objects.get(name=course)

        grades = Grade.objects.filter(student=self, class_attr__course=course).order_by('class_attr__semester__number')

        return grades[0].class_attr.semester if grades else None

    def has_passed(self, course, semester=None):
        if type(course) == str:
            course = Course.objects.get(name=course)

        grades = Grade.objects.filter(student=self, class_attr__course=course)

        if semester:
            # TODO: make semesters comparable
            grades = grades.filter(class_attr__semester__number__lte=semester.number)

        if any(i.passing() for i in grades):
            return True

        # TODO: make more generic
        if course.name == 'Math 17' and (
            (self.has_passed(Course.objects.get(name='Math 11'), semester=semester) and self.has_passed(Course.objects.get(name='Math 14'), semester=semester))
            or self.has_passed(Course.objects.get(name='Math 53'), semester=semester)
            or self.has_passed(Course.objects.get(name='Math 54'), semester=semester)
            or self.has_passed(Course.objects.get(name='Math 55'), semester=semester)):
            return True

        if course.name == 'Math 53' and (
            self.has_passed(Course.objects.get(name='Math 54'), semester=semester)
            or self.has_passed(Course.objects.get(name='Math 55'), semester=semester)):
            return True

        if course.name == 'Physics 71' and self.has_passed(Course.objects.get(name='Physics 72'), semester=semester):
            return True

        if course.name == 'CS 11' and self.has_passed(Course.objects.get(name='EEE 11'), semester=semester):
            return True

        if course.name == 'CS 11' and self.has_passed(Course.objects.get(name='CS 32'), semester=semester):
            return True

        if course.name == 'CS 12' and self.has_passed(Course.objects.get(name='CS 32'), semester=semester):
            return True

        return False


    def can_take(self, course):
        for prereq in course.prerequisites.all():
            if not any(i.passing() for i in Grade.objects.filter(student=self, class_attr__course=prereq)):
                return False

        return True

    def standing_info(self, semester=None):
        """
        1-1 [17]
        * GE AH 1 Comm in English [3]
        * GE SSP 1 Philo 1 [3]
        * GE MST 1 Free Choice [3]
        * Math 17 [5]
        * CS 11 [3]
        * PE

        1-2 [17]
        * GE SSP 2 Free Choice [3]
        * GE AH 2 Free Choice [3]
        * CS 30 [3]
        * Math 53 [5]
        * CS 12 [3]
        * PE

        2-1 [18]
        * GE AH 3 Eng 10 [3]
        * Math 54 [5]
        * CS 32 [3]
        * CS 133 [3]
        * CS 21 [4]
        * PE
        * NSTP

        2-2 [19]
        * GE AH 4 Fil 40 [3]
        * CS 135 [3]
        * Math 55 [3]
        * Physics 71 [4]
        * CS 140 [3]
        * CS 150 [3]
        * PE
        * NSTP

        3-1 [18]
        * GE AH 5 Comm 3 [3]
        * CS 130 [3]
        * Stat 130 [3]
        * CS 145 [3]
        * CS 165 [3]
        * CS 191 [3]

        3-2 [19]
        * GE SSP 3 Kas 1 [3]
        * CS 131 [3]
        * CS Elective [3]
        * CS 180 [3]
        * CS 192 [3]
        * CS 153 [3]
        * CS 194 [1]

        3-3 [3]
        * CS 195 [3]

        4-1 [19]
        * GE SSP 4 Free Choice [3]
        * GE MST 2 STS [3]
        * GE MST 3 Free Choice [3]
        * CS 198 [3]
        * Physics 72 [4]
        * MSE [3]

        4-2 [16]
        * GE SSP 5 Free Choice [3]
        * CS 196 [1]
        * CS 199 [3]
        * CS 200
        * GE MST 4 Free Choice [3]
        * PI 100 [3]
        * Free [3]

        Extra
        * 6 units in Philippine Studies
        * 9 units in English/Communication
        """

        required = [
            # 1-1
            'Math 17',
            'CS 11',

            # 1-2
            'CS 30',
            'Math 53',
            'CS 12',

            # 2-1
            'Math 54',
            'CS 32',
            'CS 133',
            'CS 21',
            
            # 2-2
            'CS 135',
            'Math 55',
            'Physics 71',
            'CS 140',
            'CS 150',

            # 3-1
            'CS 130',
            'Stat 130',
            'CS 145',
            'CS 165',
            'CS 191',

            # 3-2
            'CS 131',
            'CS 180',
            'CS 192',
            'CS 153',
            'CS 194',

            # 3-3
            'CS 195',

            # 4-1
            'CS 198',
            'Physics 72',

            # 4-2
            'CS 196',
            'CS 199',
            'PI 100',
        ]

        csmath_mapping = {
            '1-1': [
                'CS 11',
                'Math 17',
            ],
            '1-2': [
                'CS 12',
                'CS 30',
                'Math 53',
            ],
            '2-1': [
                'CS 21',
                'CS 32',
                'CS 133',
                'Math 54',
            ],
            '2-2': [
                'CS 135',
                'CS 140',
                'CS 150',
                'Math 55',
            ],
            '3-1': [
                'CS 130',
                'CS 165',
                'CS 191',
            ],
            '3-2': [
                'CS 131',
                'CS 145',
                'CS 153',
                'CS 180',
                'CS 192',
                'CS 194',
            ],
            '3-3': [
                'CS 195',
            ],
            '4-1': [
                'CS 198',
            ],
            '4-2': [
                'CS 196',
                'CS 199',
            ],
        }

        ah = [
            "Eng 10", # required
            "Comm 3", # required
            "Comm 3 Eng", # required
            "Comm 3 Fil", # required
            "Fil 40", # required
            "Aral Pil 12",
            "Araling Kapampangan 10",
            "Art Stud 1",
            "Art Stud 2",
            "BC 10",
            "CW 10",
            "EL 50",
            "Eng 1", # pseudo-required
            "Eng 11",
            "Eng 12",
            "Eng 30",
            "FA 28",
            "FA 30",
            "Fil 25",
            "Film 10",
            "Film 12",
            "Humad 1",
            "Humanidades 1",
            "J 18",
            "Kom 1",
            "MPs 10",
            "MuD 1",
            "MuL 13",
            "MuL 9",
            "Pan Pil 12",
            "Pan Pil 17",
            "Pan Pil 19",
            "Pan Pil 40",
            "Pan Pil 50",
            "Phil Stud 12", # new GE
            "Theatre 10",
            "Theatre 11",
            "Theatre 12",
        ]

        ssp = [
            "Kas 1", # required
            "Philo 1", # required
            #"Anthro 1",
            "Anthro 10",
            "Archaeo 2",
            "Arkiyoloji 1",
            "Econ 11",
            "Econ 31",
            "Geog 1",
            "Kas 2",
            "Lingg 1",
            "Philo 10",
            "Philo 11",
            "Soc Sci 1",
            "Soc Sci 2",
            "Soc Sci 3",
            "Socio 10",
        ]

        mst = [
            "STS", # required
            "BIO 1",
            #"Chem 1",  # Contentious GE
            "EEE 10",
            "ES 10",
            "Env Sci 1",
            "FN 1",
            "GE 1",
            "Geol 1",
            "MBB 1",
            "MS 1",
            #"Math 1",  # Contentious GE
            #"Math 2",
            "Nat Sci 1",
            "Nat Sci 2",
            #"Physics 10",  # Contentious GE
        ]

        eng = [
            "Eng 10",
            "Eng 1",
            "Eng 11",
            "Eng 12",
            "Eng 30",
            "Comm 3 Eng",
            "CW 10",
        ]

        ah_ssp = [
            "SEA 30",
        ]

        ssp_mst = [
            "CE 10",
        ]

        super_ge = [
            "L Arch 1",
        ]
        
        ph = [
            "L Arch 1",
            "SEA 30",

            # AH
            "Aral Pil 12",
            "Araling Kapampangan 10",
            "FA 28",
            "Fil 40",
            "Humad 1",
            "Humanidades 1",
            "MuL 9",
            "Pan Pil 12",
            "Pan Pil 17",
            "Pan Pil 19",
            "Pan Pil 40",
            "Pan Pil 50",
            "Theatre 11",

            # SSP
            "Arkiyoloji 1",
            "Kas 1",
            "Socio 10",
        ]

        not_elective = [
            "Chem 1",
            "Physics 10",
            "Math 1",
            "CE 26",
            "ChE 26",
            "EEE 11",
            "EEE 13",
            "ES 26",
            "GE 120",
            "Math 2",
            "Math 11",
            "Math 14",
            "Math 60",
            "Math 63",
            "Math 64",
            "Math 65",
            "Math 100",
            "Math 114",
            "Stat 101",
        ]

        """
        Araling Kampangan 10
        J 18
        Econ 31
        """

        def try_get(courses):
            ret = []

            for name in courses:
                try:
                    ret.append(Course.objects.get(name=name))
                except Course.DoesNotExist:
                    continue

            return ret


        required = [Course.objects.get(name=i) for i in required]
        csmath_mapping = {
            key: [Course.objects.get(name=i) for i in csmath_mapping[key]]
            for key in csmath_mapping
        }
        ah = try_get(ah)
        ssp = try_get(ssp)
        mst = try_get(mst)
        eng = try_get(eng)
        ph = try_get(ph)
        ah_ssp = try_get(ah_ssp)
        ssp_mst = try_get(ssp_mst)
        super_ge = try_get(super_ge)
        not_elective = try_get(not_elective)

        units_passed = 0
        ah_passed = 0 
        ssp_passed = 0 
        mst_passed = 0 
        eng_passed = 0 
        ph_passed = 0 
        ah_ssp_passed = 0 
        ssp_mst_passed = 0 
        super_ge_passed = 0 
        cse_passed = 0
        true_mse_passed = 0 
        core_passed = 0 

        ah_credited = 0 
        ssp_credited = 0 
        mst_credited = 0 
        ah_ssp_credited = 0 
        ssp_mst_credited = 0 
        super_ge_credited = 0 
        eng_credited = 0 
        ph_credited = 0 

        passed_nstp1 = False
        passed_nstp2 = False

        not_credited = set([i.class_attr.course for i in self.grade_set.all()])
        credited = []

        passed_pe_list = []
        passed_ah_list = []
        passed_ssp_list = []
        passed_mst_list = []

        passed_eng1 = self.has_passed("Eng 1")
        passed_comm3 = self.has_passed("Comm 3 Eng") or self.has_passed("Comm 3 Fil") or self.has_passed("Comm 3")
        passed_eng10 = self.has_passed("Eng 10")
        passed_fil40 = self.has_passed("Fil 40")
        passed_kas1 = self.has_passed("Kas 1")
        passed_philo1 = self.has_passed("Philo 1")
        passed_sts = self.has_passed("STS")

        ah_max = 15
        ssp_max = 15
        mst_max = 12

        if not passed_eng1:
            ah_max -= 3

        if not passed_eng10:
            ah_max -= 3

        if not passed_fil40:
            ah_max -= 3

        if not passed_kas1:
            ssp_max -= 3

        if not passed_philo1:
            ssp_max -= 3

        if not passed_sts:
            mst_max -= 3

        if not passed_comm3:
            ah_max -= 3

        for course in required:
            if self.has_passed(course, semester=semester):
                units_passed += course.units
                core_passed += course.units

                credited.append(course)

        for course in ah:
            if self.has_passed(course, semester=semester):
                if ah_passed < ah_max:
                    ah_credited += course.units
                    credited.append(course)
                    passed_ah_list.append(course)
                units_passed += course.units
                ah_passed += course.units

        for course in ssp:
            if self.has_passed(course, semester=semester):
                if ssp_passed < ssp_max:
                    ssp_credited += course.units
                    credited.append(course)
                    passed_ssp_list.append(course)
                units_passed += course.units
                ssp_passed += course.units

        for course in mst:
            if self.has_passed(course, semester=semester):
                if mst_passed < mst_max:
                    mst_credited += course.units
                    credited.append(course)
                    passed_mst_list.append(course)
                units_passed += course.units
                mst_passed += course.units

        for course in eng:
            if self.has_passed(course, semester=semester):
                eng_passed += course.units
                if eng_credited != 9:
                    eng_credited += course.units

        for course in ph:
            if self.has_passed(course, semester=semester):
                ph_passed += course.units
                if ph_credited != 6:
                    ph_credited += course.units

        """
        Strategy: Credit from least to most broad
        * Try to finish AH using AH-SSP
        * Try to finish MST using SSP-MST
        * Try to finish SSP using AH-SSP, SSP-MST
        * Try to finish AH, MST, SSP using Super GE
        """

        ah_ssp_left = []
        ssp_mst_left = []
        super_ge_left = []

        for course in ah_ssp:
            if self.has_passed(course, semester=semester):
                ah_ssp_passed += course.units
                units_passed += course.units
                ah_ssp_left.append(course)

        for course in ssp_mst:
            if self.has_passed(course, semester=semester):
                ssp_mst_passed += course.units
                units_passed += course.units
                ssp_mst_left.append(course)

        for course in super_ge:
            if self.has_passed(course, semester=semester):
                super_ge_passed += course.units
                units_passed += course.units
                super_ge_left.append(course)

        for i in range(int((ah_max - ah_credited) / 3)):
            if ah_ssp_left:
                g = ah_ssp_left[0]
                ah_credited += g.units
                ah_ssp_credited += g.units
                ah_ssp_left.remove(g)
                credited.append(g)
                passed_ah_list.append(course)
            else:
                break

        for i in range(int((mst_max - mst_credited) / 3)):
            if ssp_mst_left:
                g = ssp_mst_left[0]
                mst_credited += g.units
                ssp_mst_credited += g.units
                ssp_mst_left.remove(g)
                credited.append(g)
                passed_mst_list.append(course)
            else:
                break

        # TODO: do this in chronological order for GWA
        # TODO: fix handling of decimal GE units

        for i in range(int((ssp_max - ssp_credited) // 3)):
            if ah_ssp_left:
                g = ah_ssp_left[0]
                ssp_credited += g.units
                ah_ssp_credited += g.units
                ah_ssp_left.remove(g)
                credited.append(g)
            elif ssp_mst_left:
                g = ssp_mst_left[0]
                ssp_credited += g.units
                ssp_mst_credited += g.units
                ssp_mst_left.remove(g)
                credited.append(g)
                passed_ssp_list.append(course)
            else:
                break

        for i in range(int((mst_max - mst_credited) / 3)):
            if super_ge_left:
                g = super_ge_left[0]
                mst_credited += g.units
                super_ge_credited += g.units
                super_ge_left.remove(g)
                credited.append(g)
                passed_mst_list.append(course)
            else:
                break

        for i in range(int((ah_max - ah_credited) / 3)):
            if super_ge_left:
                g = super_ge_left[0]
                ah_credited += g.units
                super_ge_credited += g.units
                super_ge_left.remove(g)
                credited.append(g)
                passed_ah_list.append(course)
            else:
                break

        for i in range(int((ssp_max - ssp_credited) / 3)):
            if super_ge_left:
                g = super_ge_left[0]
                ssp_credited += g.units
                super_ge_credited += g.units
                super_ge_left.remove(g)
                credited.append(g)
                passed_ssp_list.append(course)
            else:
                break

        """
        Strategy:
        * Evaluate up to two (2) CS 197 passing grades
          * Credit first as CS elective
          * Credit second as MSE elective
        * For each CS 17X, 2XX passing grade:
          * Evaluate as CS elective if not yet satisfied
          * Evaluate as MSE elective if not yet satisfied
          * Evaluate as free elective if not yet satisfied
        * For each Math 1XX passing grade:
          * Evaluate as MSE elective if not yet satisfied
          * Evaluate as free elective if not yet satisfied
        """

        cs197_counter = 0
        has_cs_elective = False
        has_mse_elective = False
        has_free_elective = False
        cs_elective = None
        mse_elective = None
        free_elective = None

        grades = Grade.objects.filter(student=self, class_attr__course__name__startswith="CS 197")
        if semester:
            grades = grades.filter(class_attr__semester__number__lte=semester.number)
        for grade in grades:
            if grade.passing():
                cs197_counter += 1

                if not has_cs_elective:
                    has_cs_elective = True
                    cs_elective = grade.class_attr.course
                elif not has_mse_elective:
                    has_mse_elective = True
                    mse_elective = grade.class_attr.course
                elif not has_free_elective:
                    has_free_elective = True
                    free_elective = grade.class_attr.course
                else:
                    break

                course = grade.class_attr.course

                units_passed += course.units
                cse_passed += course.units

                credited.append(course)

                if cs197_counter == 2:
                    break

        grades = Grade.objects.filter(student=self, class_attr__course__name__regex="(^CS 2\d\d$)|(^CS 17\d$)")
        if semester:
            grades = grades.filter(class_attr__semester__number__lte=semester.number)
        for grade in grades:
            if grade.passing():
                if not has_cs_elective:
                    has_cs_elective = True
                    cs_elective = grade.class_attr.course
                elif not has_mse_elective:
                    has_mse_elective = True
                    mse_elective = grade.class_attr.course
                elif not has_free_elective:
                    has_free_elective = True
                    free_elective = grade.class_attr.course
                else:
                    break

                course = grade.class_attr.course

                units_passed += course.units
                cse_passed += course.units

                credited.append(course)

        grades = Grade.objects.filter(student=self, class_attr__course__name__regex="^Math 1\d\d(\.\d)?$")
        if semester:
            grades = grades.filter(class_attr__semester__number__lte=semester.number)
        for grade in grades:
            # TODO: do not hardcode
            if grade.class_attr.course.name in ["Math 100", "Math 100.1", "Math 114"]:
                continue

            if grade.passing():
                if not has_mse_elective:
                    has_mse_elective = True
                    mse_elective = grade.class_attr.course
                elif not has_free_elective:
                    has_free_elective = True
                    free_elective = grade.class_attr.course
                else:
                    break

                course = grade.class_attr.course

                units_passed += course.units
                true_mse_passed += course.units

                credited.append(course)

        grades = Grade.objects.filter(student=self, class_attr__course__name__regex="(^PE 1 )|(^PE 2 )|(^PE 3 )|(^PE 4 )")
        if semester:
            grades = grades.filter(class_attr__semester__number__lte=semester.number)
        for grade in grades:
            if grade.passing():
                credited.append(grade.class_attr.course)
                passed_pe_list.append(grade)

                if len(passed_pe_list) == 4:
                    break

        grades = Grade.objects.filter(student=self, class_attr__course__name__regex="(^CWTS.*1)|(^ROTC Mil Sci 1$)|(^LTS 1)|(^NSTP Common Module)")
        if semester:
            grades = grades.filter(class_attr__semester__number__lte=semester.number)
        for grade in grades:
            if grade.passing():
                credited.append(grade.class_attr.course)
                passed_nstp1 = True
                break

        grades = Grade.objects.filter(student=self, class_attr__course__name__regex="(^CWTS.*2)|(^ROTC Mil Sci 2$)|(^LTS 2)|(^NSTP Common Module)")
        if semester:
            grades = grades.filter(class_attr__semester__number__lte=semester.number)
        for grade in grades:
            if grade.passing():
                credited.append(grade.class_attr.course)
                passed_nstp2 = True
                break

        not_credited = [i for i in (not_credited - set(credited)) if self.has_passed(i)]
        """
        not_credited = [i for i in (not_credited - set(credited)) if \
            not (
                i.name.startswith("LTS")
                or i.name.startswith("PE")
                or i.name.startswith("CWTS")
                or i.name.startswith("NSTP")
                or i.name.startswith("ROTC")
            ) and self.has_passed(i)
        ]
        """

        def is_mse(name):
            prefixes = [
                "ChE ",
                "CE ",
                "CoE ",
                "ECE ",
                "EEE ",
                "EE ",
                "EnE ",
                "ES ",
                "EM ",
                "GE ",
                "GIM ",
                "GS ",
                "GmE ",
                "GsE ",
                "IE ",
                "MatE ",
                "MetE ",

                "App Physics ",
                "BIO ",
                "Chem ",
                "Env Sci ",
                "ES ",
                "Geol ",
                "Math ",
                "Meteo ",
                "MBB ",
                "MS ",
                "MSE ",
                "Physics ",
            ]

            for i in prefixes:
                if name.startswith(i):
                    return True

            return False

        if not has_mse_elective:
            for course in sorted(set(not_credited) - (set(not_elective) | set(ah) | set(ssp) | set(mst) | set(ah_ssp) | set(ssp_mst) | set(super_ge)), key=lambda a: a.name):
                if (course.units == 3 or course.units == 5) and is_mse(course.name):
                    if (not semester and self.has_passed(course)) or self.has_passed(course, semester=semester):
                        print(course)
                        units_passed += 3  # Always count as 3; Chem 16
                        not_credited.remove(course)
                        credited.append(course)
                        has_mse_elective = True
                        mse_elective = course
                        break

        if not has_free_elective:
            for course in sorted(set(not_credited) - (set(not_elective) | set(ah) | set(ssp) | set(mst) | set(ah_ssp) | set(ssp_mst) | set(super_ge)), key=lambda a: a.name):
                if (course.units == 3 or course.units == 5):
                    if (not semester and self.has_passed(course)) or self.has_passed(course, semester=semester):
                        units_passed += 3  # Always count as 3; Chem 16
                        not_credited.remove(course)
                        credited.append(course)
                        has_free_elective = True
                        free_elective = course
                        break

        required_csmath_junior = set(itertools.chain.from_iterable(
            [value for key, value in
                csmath_mapping.items() if key in [
                    '1-1',
                    '1-2',
                    '2-1',
                    '2-2',
                ]
            ]
        ))

        required_csmath_senior = set(itertools.chain.from_iterable(
            [value for key, value in
                csmath_mapping.items() if key in [
                    '1-1',
                    '1-2',
                    '2-1',
                    '2-2',
                    '3-1',
                    '3-2',
                    '3-3',
                ]
            ]
        ))

        passed_csmath_junior = False
        passed_csmath_senior = False

        if required_csmath_junior - set(credited) == set():
            passed_csmath_junior = True

        if required_csmath_senior - set(credited) == set():
            passed_csmath_senior = True

        units_credited = sum(i.units for i in credited)
        if Course.objects.get(name="Chem 16") in credited:
            units_credited -= 2

        taken_cs133 = self.grade_set.filter(class_attr__course__name="CS 133")
        """
        passed_majority_junior_waive = False
        junior_waive_must_pass = ["CS 135", "CS 140", "CS 150"]
        if taken_cs133:
            junior_waive_must_pass = ["CS 133"] + junior_waive_must_pass
        junior_waive_must_pass = [Course.objects.get(name=i) for i in junior_waive_must_pass]

        passed_junior_waive_units = 0

        for course in junior_waive_must_pass:
            if self.has_passed(course):
                passed_junior_waive_units += course.units

        total_junior_waive_units = sum(i.units for i in junior_waive_must_pass)
        print(passed_junior_waive_units, type(passed_junior_waive_units), total_junior_waive_units, type(total_junior_waive_units))
        passed_majority_junior_waive = passed_junior_waive_units / total_junior_waive_units >= 0.5
        """

        junior_curriculum = passed_csmath_junior and units_credited >= 71
        senior_curriculum = passed_csmath_senior and units_credited >= 108
        passed_half_units = units_credited >= 73
        passed_75percent_units = units_credited >= 110
        units_left = 146 - units_credited

        passed_cs32 = self.has_passed("CS 32")

        standing = "SENIOR" if passed_75percent_units or senior_curriculum \
            else ("JUNIOR" if passed_half_units or junior_curriculum else "")

        waive_junior = False
        waive_senior = False
        experiment = False

        #if standing == "" and passed_cs32 and units_credited >= 60 and units_left <= 93:
        if standing == "" and passed_cs32 and units_left <= 93:
            experiment = True

        if standing != "SENIOR" and units_left <= 51:
            standing = "SENIOR"
            waive_senior = True
        """
        elif standing == "" and units_credited >= 60 and passed_majority_junior_waive:
            standing = "JUNIOR"
            waive_junior = True
        """

        failed = [i for i in self.grade_set.all() if not i.passing() and i.grade != ""]
        failed_csmath = []
        failed_others = []

        for grade in failed:
            cls = grade.class_attr
            name = cls.course.name
            if name.startswith("CS ") or name.startswith("Math "):
                failed_csmath.append(cls)
            else:
                failed_others.append(cls)

        failed_csmath_count = len(failed_csmath)
        failed_others_count = len(failed_others)
        total_failed = failed_csmath_count + failed_others_count

        passed_cs191 = self.has_passed("CS 191")
        passed_cs192 = self.has_passed("CS 192")
        passed_cs198 = self.has_passed("CS 198")

        must_take_191 = passed_cs32 and not passed_cs191 and not passed_cs192
        denied_191 = standing == "" and passed_cs32 and not passed_cs191
        denied_198 = standing != "SENIOR" and passed_cs192 and not passed_cs198

        needed_core = set(required) - set(credited)
        to_remove = set([i for i in needed_core if self.has_passed(i)])
        needed_core = needed_core - to_remove

        immortal_courses = set([Course.objects.get(name=i) for i in ["CS 130", "CS 133", "CS 135", "CS 140", "CS 191"]])
        immortal_passed = set(credited) & set(immortal_courses)
        immortal = (immortal_passed == immortal_courses)

        if eng_credited != 9 and ah_credited == 15:
            units_left += 9 - eng_credited

        if ph_credited != 6 and (15 - ah_credited + 15 - ssp_credited) < 6 - ph_credited:
            units_left += 6 - ph_credited

        passed_pe_count = len(passed_pe_list)

        return {
            "standing": standing,
            "credited": credited,
            "credited_names": ",".join(sorted(str(i.name) for i in credited)),
            "not_credited": not_credited,
            "not_credited_names": ",".join(sorted(str(i.name) for i in not_credited)),
            "immortal": immortal,
            "ah_credited": ah_credited,
            "ssp_credited": ssp_credited,
            "mst_credited": mst_credited,
            "passed_ah_list": passed_ah_list,
            "passed_ssp_list": passed_ssp_list,
            "passed_mst_list": passed_mst_list,
            "passed_ah_names": ",".join(sorted(str(i.name) for i in passed_ah_list)),
            "passed_ssp_names": ",".join(sorted(str(i.name) for i in passed_ssp_list)),
            "passed_mst_names": ",".join(sorted(str(i.name) for i in passed_mst_list)),
            "ah_ssp_credited": ah_ssp_credited,
            "ssp_mst_credited": ssp_mst_credited,
            "super_ge_credited": mst_credited,
            "ah_ssp_uncredited": ah_ssp_left,
            "ssp_mst_uncredited": ssp_mst_left,
            "super_ge_uncredited": super_ge_left,
            "eng_credited": eng_credited,
            "ph_credited": ph_credited,
            "needed_core": needed_core,
            "needed_core_names": ",".join(sorted(str(i) for i in needed_core)),
            "units_credited": units_credited,
            "units_left": units_left,
            "must_take_191": "Y" if must_take_191 else "",
            "denied_191": "Y" if denied_191 else "",
            "denied_198": "Y" if denied_198 else "",
            "passed_75percent_units": "Y" if passed_75percent_units else "",
            "senior_curriculum": "Y" if senior_curriculum else "", 
            "waive_senior": "Y" if waive_senior else "",
            "passed_half_units": "Y" if passed_half_units else "", 
            "junior_curriculum": "Y" if junior_curriculum else "", 
            #"waive_junior": "Y" if waive_junior else "",
            "waive_junior": "",
            "experiment": "Y" if experiment else "",
            "passed_junior_waive_units": 0,
            "total_junior_waive_units": 0,
            "total_failed": total_failed, 
            "failed_csmath_count": failed_csmath_count,
            "failed_csmath": ",".join(sorted(str(i.course) for i in failed_csmath)),
            "failed_others_count": failed_others_count,
            "failed_others": ",".join(sorted(str(i.course) for i in failed_others)),
            "cs_elective": cs_elective,
            "mse_elective": mse_elective,
            "free_elective": free_elective,
            "passed_comm3": "Y" if passed_comm3 else "",
            "passed_eng10": "Y" if passed_eng10 else "",
            "passed_fil40": "Y" if passed_fil40 else "",
            "passed_kas1": "Y" if passed_kas1 else "",
            "passed_philo1": "Y" if passed_philo1 else "",
            "passed_sts": "Y" if passed_sts else "",
            "passed_eng1": "Y" if passed_eng1 else "",
            "passed_pe_list": ",".join(sorted(str(i.class_attr.course) for i in passed_pe_list)),
            "passed_pe_count": passed_pe_count,
            "passed_nstp1": passed_nstp1,
            "passed_nstp2": passed_nstp2,
        }

    def grades(self, course):
        grades = Grade.objects.filter(student=self, class_attr__course=course)

        return [i.grade for i in grades]

    def __str__(self):
        if 'BS' not in str(self.degree_program):
            return '{sid}, {last_name}, {first_name} [{degree_program}]'.format(
                sid=self.sid,
                last_name=self.last_name,
                first_name=self.first_name,
                degree_program=self.degree_program.split(' ')[0].strip() + " CS",
            )

        return '{sid}, {last_name}, {first_name}'.format(
            sid=self.sid,
            last_name=self.last_name,
            first_name=self.first_name,
        )

    class Meta:
        unique_together = ('first_name', 'last_name', 'sid')


class Semester(models.Model):
    name = models.CharField(max_length=40, unique=True)
    number = models.IntegerField(unique=True)

    def before(self):
        number_list = sorted([i.number for i in Semester.objects.all()])

        index = number_list.index(self.number)

        if index != 0:
            return Semester.objects.get(number=number_list[index-1])

        return None

    def __str__(self):
        return self.name

    class Meta:
        unique_together = ('name', 'number')


class Enrollment(models.Model):
    student = models.ForeignKey('Student')
    semester = models.ForeignKey('Semester')
    status = models.CharField(max_length=30)

    def __str__(self):
        return "{student} - {semester} ({status})".format(
            student=self.student,
            semester=self.semester,
            status=self.status,
        )

    class Meta:
        unique_together = ('student', 'semester')


class Faculty(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'faculty'


class Course(models.Model):
    name = models.CharField(max_length=20)
    units = models.DecimalField(max_digits=5, decimal_places=2)
    prerequisites = models.ManyToManyField('self', symmetrical=False, related_name='prerequisites_to')
    substitutes = models.ManyToManyField('self', symmetrical=False, related_name='substitutes_to')
    affects_gwa = models.BooleanField(default=True)

    def must_take(self):
        students = [i for i in Student.objects.filter(degree_program='BS Computer Science') if i.active() and i.can_take(self) and not i.has_passed(self) and not any(i.has_passed(k) for k in self.substitutes.all())]

        return students

    def passed(self, semester_number):
        return sum(1 for i in Grade.objects.filter(class_attr__course=self, class_attr__semester__number=semester_number, student__degree_program='BS Computer Science') if i.passing())

    def failed(self, semester_number):
        return sum(1 for i in Grade.objects.filter(class_attr__course=self, class_attr__semester__number=semester_number, student__degree_program='BS Computer Science') if not i.passing())

    def __str__(self):
        return self.name

    class Meta:
        unique_together = ('name', 'units')


class Class(models.Model):
    section = models.CharField(max_length=20)
    code = models.IntegerField()
    semester = models.ForeignKey('Semester')
    course = models.ForeignKey('Course')
    faculty = models.ManyToManyField('Faculty')

    def __str__(self):
        return "{course} {section} - {semester} ({faculty})".format(
            course=self.course,
            section=self.section,
            semester=self.semester,
            faculty=', '.join(str(i) for i in self.faculty.all()),
        )

    class Meta:
        unique_together = ('section', 'code', 'semester', 'course')
        verbose_name_plural = 'classes'


class Grade(models.Model):
    grade = models.CharField(max_length=10)
    student = models.ForeignKey('Student')
    class_attr = models.ForeignKey('Class')

    def passing(self):
        grade = self.grade.lower().strip()

        if "5.00" in grade or "4.00" == grade or "drp" in grade or grade == "inc" or grade == "":
        #if "5.00" in grade or "4.00" == grade or "drp" in grade or grade == "inc":
            return False

        return True

    def __str__(self):
        return "{grade} - {student} - {class_}".format(
            grade=self.grade,
            student=self.student,
            class_=self.class_attr,
        )

    class Meta:
        unique_together = ('grade', 'student', 'class_attr')


class Enlistment(models.Model):
    student = models.ForeignKey('Student')
    semester = models.ForeignKey('Semester')
    priority = models.CharField(max_length=50)
    eligibility = models.CharField(max_length=50)
    accountability = models.CharField(max_length=50)
    classes = models.ManyToManyField('Class')

    def __str__(self):
        return "{student} - {semester}".format(
            student=self.student,
            semester=self.semester,
        )

    class Meta:
        unique_together = ('student', 'semester')
