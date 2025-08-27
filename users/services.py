from users.models import Student

class StudentFileService:
    
    
    @staticmethod
    def get_student_file_data(student_id):
        
        try:
            student = Student.objects.select_related('user', 'career__faculty').get(student_id=student_id)
            return {
                "nro_legajo": student.student_id,
                "apellido_nombre": student.user.get_full_name(),
                "dni": student.user.dni,
                "facultad_nombre": student.career.faculty.name,
                "carrera_nombre": student.career.name,
                "fecha_inscripcion": student.enrollment_date.strftime("%d/%m/%Y"),
            }
        except Student.DoesNotExist:
            return None