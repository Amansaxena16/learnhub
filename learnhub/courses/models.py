from django.db import models
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
import uuid

class Category(models.Model):
    '''
    "Programming & Software Development",
    "Data Science & Artificial Intelligence",
    "Web Development",
    "Mobile App Development",
    "Cybersecurity"
    '''
    id = models.UUIDField(primary_key=True, editable=False, unique=True, null=False, blank=False, default=uuid.uuid4)
    category_name = models.CharField(max_length=150, null=False, blank=False)
    category_slug = models.CharField(max_length=150, unique=True, null=False, blank=False)
        
    def save(self, *args, **kwargs):
        if not self.category_slug:
            self.slug = slugify(self.category_slug)
        super().save(*args, **kwargs)
        
    def __str__(self):
        return self.category_slug
        
class Tag(models.Model):
    '''
    Python
    Django
    React
    JavaScript
    '''
    id = models.UUIDField(primary_key=True, editable=False, unique=True, null=False, blank=False, default=uuid.uuid4)
    tag_name = models.CharField(max_length=100, null=False, blank=False)
    tag_slug = models.CharField(max_length=100, unique=True, blank=False, null=False)
    
    def save(self, *args, **kwargs):
        if not self.tag_slug:
            self.slug = slugify(self.tag_slug)
        super().save(*args, **kwargs)
        
    def __str__(self):
        return self.tag_slug
        
    
class Instructor(models.Model):
    id = models.UUIDField(primary_key=True, editable=False, unique=True, blank=False, null=False, default=uuid.uuid4)
    user = models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.user.email
    
class Course(models.Model):
    '''
    Course 1:
    title = "Python for Beginners"
    price = 999

    Course 2:
    title = "Django Web Development"
    price = 1499
    '''
    
    id = models.UUIDField(primary_key=True, editable=False, unique=True, null=False, blank=False, default=uuid.uuid4)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, blank=True, null=True)
    tag = models.ManyToManyField(Tag)
    instructor = models.ForeignKey(Instructor, on_delete=models.SET_NULL, related_name='courses', blank=True, null=True)
    title = models.CharField(max_length=200, null=False, blank=False)
    title_slug = models.CharField(max_length=200, unique=True, null=False, blank=False)
    description = models.TextField(max_length=500, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title
    
class Lesson(models.Model):
    id = models.UUIDField(primary_key=True, editable=False, unique=True, null=False, blank=False, default=uuid.uuid4)
    title = models.CharField(max_length=200, null=True, blank=True)
    content =  models.TextField()
    order = models.PositiveIntegerField()
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='lessons')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.title} and its {self.order}"
    
class Student(models.Model):
    id = models.UUIDField(primary_key=True, editable=False, unique=True, null=False, blank=False, default=uuid.uuid4)
    user = models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.user.email
    
class Enrollment(models.Model):
    STATUS = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('dropped', 'Dropped'),
    ]
    id = models.UUIDField(primary_key=True, editable=False, unique=True, null=False, blank=False, default=uuid.uuid4)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    progress = models.IntegerField(validators=[MinValueValidator(0), MaxValueValidator(100)], null=True, blank=True)
    status = models.CharField(choices=STATUS, default='active', max_length=20, null=True, blank=False)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'course'],
                name = 'unique_student_course'
            )
        ]
    def __str__(self):
        return f"Student {self.student} its course {self.course} and its status {self.status}"