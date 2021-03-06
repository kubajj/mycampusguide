from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from guide.models import Lecturer, Course, UserProfile, LecturerRating, Category, CourseRating
from guide.forms import LecturerForm, CourseForm, UserForm, UserProfileForm, LecturerRatingForm, CourseRatingForm, LecturerCommentForm, CourseCommentForm, UserDeleteForm, ChangeProfileForm, EditLecturer, EditCourse
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.shortcuts import redirect
from django.urls import reverse
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
import random
from django.contrib import messages

def visitor_cookie_handler(request, response): 
  visits = int(request.COOKIES.get('visits', '1'))
  last_visit_cookie = request.COOKIES.get('last_visit', str(datetime.now())) 
  last_visit_time = datetime.strptime(last_visit_cookie[:-7],'%Y-%m-%d %H:%M:%S')
  if (datetime.now() - last_visit_time).days > 0:
    visits = visits + 1
  else:
    response.set_cookie('visits', visits)


def index(request):
  response =  render(request, 'guide/index.html')
  try:
    #Get's the lecture and course with the most views to appear on 'trending'
    trending_lecturer = Lecturer.objects.order_by('-views')[0]
    trending_course = Course.objects.order_by('-views')[0]
  except:
    trending_lecturer = None
    trending_course = None
  context_dict = {}
  context_dict['lecturer'] = trending_lecturer
  context_dict['course'] = trending_course
  #Chooses a random picture to select on the trending page for the courses page
  context_dict['course_image'] = "course_"+str(random.randint(1,3))+".jpg"
  visitor_cookie_handler(request, response)
  return render(request, 'guide/index.html', context=context_dict)


@login_required
def myprofile(request):
    user = User.objects.get(username=request.user.username)
    profile = UserProfile.objects.get(user=request.user)
    #If its a HTTP POST, we are interested in processing form data
    if request.method == 'POST':
      form = ChangeProfileForm(request.POST)

      if form.is_valid():
        #Updates any changed information on the users profile page
        cform = form.save(commit=False)
        user.email = cform.email
        profile.major = cform.major
        profile.degreeprogram = cform.degreeprogram
        profile.startedstudying = cform.startedstudying
        profile.expectedgraduation = cform.expectedgraduation
        if 'picture' in request.FILES:
          profile.picture = request.FILES['picture']
        user.save()
        profile.save()
        
        #Refreshes the page
        return HttpResponseRedirect(request.path_info)

    return render(request, 'guide/myprofile.html', context={'user': user, 'profile': profile})

def courses(request):
  #Initially orders the courses by name to calculate the number of comments and average ratings for each
  courses = Course.objects.order_by('name')
  for course in courses:
    course.storeNumberOfComments()
    course.calculateAverageRating()
    course.save()
  #Whatever button the user presses to sort by, it orders it accordingly 
  order_by = request.GET.get('order_by', 'name')
  courses = Course.objects.order_by(order_by)  
  context_dict = {}
  context_dict['courses'] = courses
  return render(request, 'guide/courses.html', context=context_dict)

def lecturers(request):
  #Initially orders the lecturers by name to calculate the number of comments and average ratings for each
  lecturers = Lecturer.objects.order_by('name')
  for lecturer in lecturers:
    lecturer.storeNumberOfComments()
    lecturer.calculateAverageRating()
    lecturer.save()
  #Whatever button the user presses to sort by, it orders it accordingly 
  order_by = request.GET.get('order_by', 'name')
  lecturers = Lecturer.objects.order_by(order_by)  
  context_dict = {}
  context_dict['lecturers'] = lecturers
  return render(request, 'guide/lecturers.html', context=context_dict)

@login_required
def add_course(request):
  category = Category.objects.get(name="Course Pages")
  user = User.objects.get(username=request.user.username)

  form = CourseForm()
  if request.method == 'POST':
      form = CourseForm(request.POST)

      if form.is_valid():
        #Sets the attributes entered by the user for the course page
        page = form.save(commit=False)
        page.category = category
        page.views = 0
        page.page_owner = user
        page.save()
        #Redirects to courses page if successful
        return redirect(reverse('guide:courses'))
      else:
        print(form.errors)
  return render(request, 'guide/add_course.html', {'form':form})

@login_required
def add_lecturer(request):
  category = Category.objects.get(name="Lecturer Pages")
  user = User.objects.get(username=request.user.username)

  form = LecturerForm()
  if request.method == 'POST':
      form = LecturerForm(request.POST, request.FILES)

      if form.is_valid():
        #Sets the attributes entered by the user for the course page
        page = form.save(commit=False)
        page.category = category
        page.views = 0
        page.page_owner = user
        page.save()
        #Redirects to lecturers page if successful
        return redirect(reverse('guide:lecturers'))
      else:
        print(form.errors)
  return render(request, 'guide/add_lecturer.html', {'form':form})


def show_lecturer(request, lecturer_name_slug):
  context_dict = {}
  try:
    lecturer = Lecturer.objects.get(slug=lecturer_name_slug)
    lecturer.calculateAverageRating()
    lecturer.viewed()
    context_dict['lecturer'] = lecturer
    context_dict['comments'] = lecturer.lecturercomment_set.all()
    
    try:
      #Checks if the user already has a rating for this page to display if so
      user = User.objects.get(username=request.user.username) 
      context_dict['rating'] = LecturerRating.objects.get(user=user, page=lecturer)
    except:
      context_dict['rating'] = None

  except Lecturer.DoesNotExist:
    context_dict['lecturer'] = None
    context_dict['rating'] = None

  #Form for each the ratings and the comments
  form = LecturerRatingForm()
  cform = LecturerCommentForm()
  if request.method == 'POST':
    #The rating form is only processed if the data is in the request
    if 'submitrating' in request.POST:
      form = LecturerRatingForm(request.POST)

      if form.is_valid():
        rating = form.save(commit=False)
        rating.user = user
        rating.page = lecturer
        rating.save()
        context_dict['form'] = form
        context_dict['rating'] = LecturerRating.objects.get(user=user, page=lecturer)
        #Refreshes the page, removing information stored
        return HttpResponseRedirect(request.path_info)
    
    #The comment form is only processed if the data is in the request
    if 'submitcomment' in request.POST:
      cform = LecturerCommentForm(request.POST)
      if cform.is_valid():
        comment = cform.save(commit=False)
        comment.user = request.user
        comment.page = lecturer
        comment.save()
        context_dict['cform'] = cform 
        #Refreshes the page, removing information stored and empties the form  
        return HttpResponseRedirect(request.path_info)
  
  context_dict['cform'] = cform
  context_dict['form'] = form

  return render(request, 'guide/chosen_lecturer.html', context = context_dict)


def show_course(request, course_name_slug):
  context_dict = {}
  try:
    course = Course.objects.get(slug=course_name_slug)
    course.calculateAverageRating()
    course.viewed()
    context_dict['course'] = course
    context_dict['comments'] = course.coursecomment_set.all()

    try:
      #Checks if the user already has a rating for this page to display if so
      user = User.objects.get(username=request.user.username)  
      context_dict['rating'] = CourseRating.objects.get(user=user, page=course)
    except:
      context_dict['rating'] = None

  except Course.DoesNotExist:
    context_dict['course'] = None
    context_dict['rating'] = None

  #Form for each the ratings and the comments
  form = CourseRatingForm()
  cform = CourseCommentForm()
  if request.method == 'POST':
    #The rating form is only processed if the data is in the request
    if 'submitrating' in request.POST:
      form = CourseRatingForm(request.POST)

      if form.is_valid():
        rating = form.save(commit=False)
        rating.user = user
        rating.page = course
        rating.save()
        context_dict['form'] = form
        context_dict['rating'] = CourseRating.objects.get(user=user, page=course)
        #Refreshes the page, removing information stored
        return HttpResponseRedirect(request.path_info)
  
    #The comment form is only processed if the data is in the request
    if 'submitcomment' in request.POST:
      cform = CourseCommentForm(request.POST)
      if cform.is_valid():
        comment = cform.save(commit=False)
        comment.user = request.user
        comment.page = course
        comment.save()
        context_dict['cform'] = cform 
        #Refreshes the page, removing information stored and empties the form  
        return HttpResponseRedirect(request.path_info)
  
  context_dict['cform'] = cform
  context_dict['form'] = form

  return render(request, 'guide/chosen_course.html', context = context_dict)


def searchResults(request):
  context_dict = {}
  #Recieves search query by the user
  userSearch = request.GET.get('searchResults')
  users = UserProfile.objects.all()
  context_dict["user_profiles"] = users
  try:
      #Filters lecturer objects to only show those of which the characters in the user's search is within the lecturer's name
      lecturers = Lecturer.objects.filter(name__contains = userSearch)
      context_dict["searchlecturers"] = lecturers
      context_dict["SearchValue"] = userSearch
      
  except Lecturer.DoesNotExist:
      context_dict["searchlecturers"] = None
      context_dict["SearchValue"] = None
  try:
      #Filters course objects to only show those of which the characters in the user's search is within the course's name
      courses = Course.objects.filter(name__contains = userSearch)
      context_dict["searchcourses"] = courses
      context_dict["SearchValue"] = userSearch
      
  except Course.DoesNotExist:
      context_dict["searchcourses"] = None
      context_dict["SearchValue"] = None

  return render(request, 'guide/search_results.html', context=context_dict)


def register(request):
  #Boolean value to indiacate to the template if registration was successful
  registered = False

  if request.method == 'POST': 
    user_form = UserForm(request.POST)
    profile_form = UserProfileForm(request.POST)

    if user_form.is_valid() and profile_form.is_valid():
      user = user_form.save()
      user.set_password(user.password)
      user.save()

      profile = profile_form.save(commit=False)
      profile.user = user

      #If the user provides a picture it has to be out in the UserProfile model
      if 'picture' in request.FILES:
        profile.picture = request.FILES['picture']

      profile.save()

      registered = True

      auth_login(request, user)
      return redirect(reverse('guide:registered'))
      
    else:
      return redirect(reverse('guide:register'))
  else:
    user_form = UserForm()
    profile_form = UserProfileForm()

  return render(request, 'guide/register.html',context = {'user_form': user_form, 'profile_form': profile_form, 'registered': registered})  

def registered(request):
  return render(request, 'guide/registered.html')

def login(request):
    
    if request.method == 'POST':       
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(username=username, password=password)
        
        if user:          

            if user.is_active:   
                #Signs the user in with the details supllied once they create an account             
                auth_login(request, user)
                return redirect(reverse('guide:index'))
            else:             
                return HttpResponse("Your Guide account is disabled.")

        else:          
            return render(request, 'guide/login.html', context={'message':"Invalid login details"})
            
    else:
        return render(request, 'guide/login.html')

@login_required
def logout(request):
  auth_logout(request)
  return render(request, 'guide/logout.html')



@login_required
def deleteuser(request):
    if request.method == 'POST':
        delete_form = UserDeleteForm(request.POST, instance=request.user)
        user = request.user
        user.delete()
        messages.info(request, 'Your account has been deleted.')
        return redirect(reverse('guide:index'))
    else:
        delete_form = UserDeleteForm(instance=request.user)

    context = {
        'delete_form': delete_form
    }

    return render(request, 'guide/delete_account.html', context)

@login_required
def edit_course(request, course_name_slug):
  context_dict = {}
  try:
    course = Course.objects.get(slug=course_name_slug)
    context_dict['course'] = course
  except Course.DoesNotExist:
    context_dict['course'] = None

  if request.method == 'POST':
    form = EditCourse(request.POST)
    print(form.errors)
    if form.is_valid():
      #Sets the course's data to any information changed in the form
      cform = form.save(commit=False)
      course.school = cform.school
      course.credits = cform.credits
      course.requirements = cform.requirements
      course.description = cform.description
      course.currentlecturer = cform.currentlecturer
      course.save()
          
        #Refreshes the page
      return HttpResponseRedirect(request.path_info)

  return render(request, 'guide/edit_course.html', context=context_dict)

@login_required
def edit_lecturer(request, lecturer_name_slug):
  context_dict = {}
  try:
    lecturer = Lecturer.objects.get(slug=lecturer_name_slug)
    context_dict['lecturer'] = lecturer
  except Lecturer.DoesNotExist:
    context_dict['lecturer'] = None

  if request.method == 'POST':
    form = EditLecturer(request.POST)
    print(form.errors)
    if form.is_valid():
      #Sets the lecturer's data to any information changed in the form
      cform = form.save(commit=False)
      lecturer.name = lecturer.name
      lecturer.teaching = cform.teaching
      lecturer.description = cform.description
      lecturer.save()
        
      #Refreshes the page
      return HttpResponseRedirect(request.path_info)
  return render(request, 'guide/edit_lecturer.html', context=context_dict)

