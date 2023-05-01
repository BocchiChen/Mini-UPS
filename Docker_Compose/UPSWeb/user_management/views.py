from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from .forms import *
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .models import UPSAccount, Package_Info, Truck
from django.contrib import messages
from .comm_backend import *

"""
    user function
"""

@login_required(login_url='/login/')
def homePage(request):
    return render(request, 'home.html')

def registerPage(request):
    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid(): 
            username=form.cleaned_data['username']
            # print(username)
            password1 = form.cleaned_data['password1']
            password2 = form.cleaned_data['password2']
            ups_account_number = form.cleaned_data['ups_account_number']
            email = form.cleaned_data['email']

            user = User.objects.create_user(username=username, email=email, password=password2)
            new_user = UPSAccount.objects.create(user=user, ups_account_number=ups_account_number) # set default value for world_id
            new_user.save()
            return redirect('login')
        else:
            return render(request, 'register.html', {'form':form})
    form = UserRegistrationForm()
    return render(request, 'register.html', {'form':form})

def loginPage(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.info(request, 'Username or Password is incorrect')
            return redirect('login')

    return render(request, 'login.html')

def logoutPage(request):
    logout(request)
    return redirect('login')

@login_required(login_url='/login/')
def modify_ups_account(request):
    cur_user = request.user
    if request.method == "POST":
        form = UPSAccountForm(request.POST)
        if form.is_valid():
            old_user = User.objects.get(id=cur_user.id)
            old_user.first_name = form.cleaned_data["first_name"]
            old_user.last_name = form.cleaned_data["last_name"]
            old_user.email = form.cleaned_data["email"]
            old_user.save()
            return redirect('user_profile')

    old_user = User.objects.get(id=cur_user.id)
    form = UPSAccountForm(instance=old_user)
    return render(request, 'modify_ups_account.html', {'form' : form})

@login_required(login_url='/login/')
def profilePage(request):
    cur_user = request.user
    ups_acc = UPSAccount.objects.filter(user_id=cur_user.id).first()
    if ups_acc:
        return render(request, 'user_profile.html', {'user':cur_user, 'ups_acc':ups_acc})
    else:
        messages.info(request, f"You are a superuser, so you are not in the database, please check in as a normal user")
        return redirect('home')
    
@login_required(login_url='/login/')
def view_all_packages(request):
    try:
        cur_user = request.user
        ups_acc = UPSAccount.objects.filter(user_id=cur_user.id).first()
        if ups_acc:
            # get the packages that are owned by this user and in the same world
            related_packages = Package_Info.objects.filter(user_id=ups_acc.ups_account_number)
            pac_dict = {}
            search_data = request.GET.get('q', "")
            if search_data:
                pac_dict["package_id__exact"] = search_data
                related_packages = Package_Info.objects.filter(**pac_dict)

            context = {'packages' : related_packages, 'ups_acc' : ups_acc, 'search_data' : search_data}
            return render(request, 'view_all_packages.html', context)
        else:
            messages.info(request, f"You are a superuser, so you are not in the database, please check in as a normal user")
            return redirect('home')
    except Exception as e:
        if not search_data.isdigit():
            messages.error(request, "numbers are only allowed")
        # print(e)
        return redirect('view_all_packages')

@login_required(login_url='/login/')
def edit_package_desination(request, nid):
    try: 
        if request.method == "POST":
            form = PackageEditForm(request.POST)
            if form.is_valid():
                old_package = Package_Info.objects.get(package_id=nid)
                old_package.destination_x = form.cleaned_data["destination_x"]
                old_package.destination_y = form.cleaned_data["destination_y"]
                old_package.save()
                backend_soc = connectToBackEndServer()
                msg = f'{old_package.package_id},{old_package.destination_x},{old_package.destination_y}'
                sendAddrMSgToBackEnd(backend_soc, msg)
                backend_soc.close()
                return redirect('view_all_packages')

        package = Package_Info.objects.get(package_id=nid)
        form = PackageEditForm(instance=package)
        return render(request, 'edit_package_destination.html', {'form' : form})
    except Exception as e:
        messages.error(request, e)
        # print(e)
        return redirect('view_all_packages')

@login_required(login_url='/login/')
def view_package_detail(request, nid):
    cur_user = request.user
    ups_acc = UPSAccount.objects.get(user_id=cur_user.id)
    package = Package_Info.objects.get(package_id=nid)
    context = {'package' : package, 'ups_acc' : ups_acc}
    return render(request, "view_package_detail.html", context)


@login_required(login_url='/login/')
def check_package_position(request, nid):
    try:
        package = Package_Info.objects.get(package_id=nid)
        truck = Truck.objects.get(truck_id=package.truck.truck_id)
        backend_soc = connectToBackEndServer()
        msg = str(truck.truck_id)
        sendTruckIdMsgToBackEnd(backend_soc, msg)
        backend_soc.close()
        truck = Truck.objects.get(truck_id=package.truck.truck_id)
        context = {'package' : package, 'truck' : truck}
        return render(request, "check_package_position.html", context)
    except Exception as e:
        messages.error(request, e)
        # print(e)
        return redirect('view_all_packages')
    
@login_required(login_url='/login/')
def user_evaluation(request, nid):
    cur_user = request.user
    package = Package_Info.objects.get(package_id=nid)
    ups_acc = UPSAccount.objects.get(user_id=cur_user.id)
    if request.method == "POST":
        form = EvaluationForm(request.POST)
        if form.is_valid():
            ups_number = form.cleaned_data['ups_number']
            product = package
            prod_quality = form.cleaned_data['prod_quality']
            delivery_quality = form.cleaned_data['delivery_quality']
            description = form.cleaned_data['description']
            existed_eva = userEvaluation.objects.filter(ups_number=ups_acc.ups_account_number).first()
            if existed_eva is None:
                eva = userEvaluation(ups_number=ups_number, product=product, prod_quality=prod_quality, delivery_quality=delivery_quality, description=description)
                eva.save()
            else:
                existed_eva.prod_quality = prod_quality
                existed_eva.delivery_quality = delivery_quality
                existed_eva.description = description
                existed_eva.save()
        return redirect('user_view_evaluations')
    
    form = EvaluationForm()
    context = {'form' : form, 'package' : package, 'user' : cur_user, 'ups_acc' : ups_acc}
    return render(request, "user_evaluation.html", context)

@login_required(login_url='/login/')
def user_view_evaluations(request):
    try:
        cur_user = request.user
        ups_acc = UPSAccount.objects.filter(user_id=cur_user.id).first()
        if ups_acc:
            # get the packages that are owned by this user and in the same world
            related_evaluations = userEvaluation.objects.filter(ups_number=ups_acc.ups_account_number)
            eva_dict = {}
            search_data = request.GET.get('q', "")
            if search_data:
                eva_dict["product__package_id__exact"] = search_data
                related_evaluations = userEvaluation.objects.filter(**eva_dict)

            context = {'evaluations' : related_evaluations, 'ups_acc' : ups_acc, 'search_data' : search_data}
            return render(request, 'user_view_eva.html', context)
        else:
            messages.info(request, f"You are a superuser, so you are not in the database, please check in as a normal user")
            return redirect('home')
    except Exception as e:
        if not search_data.isdigit():
            messages.error(request, "numbers are only allowed")
        # print(e)
        return redirect('user_view_evaluations')

""" 
    guest functions 
"""


def guestHomePage(request):
    return render(request, 'guest_home.html')

def guest_edit_package_desination(request, nid):
    try:
        if request.method == "POST":
            form = PackageEditForm(request.POST)
            if form.is_valid():
                old_package = Package_Info.objects.get(package_id=nid)
                old_package.destination_x = form.cleaned_data["destination_x"]
                old_package.destination_y = form.cleaned_data["destination_y"]
                old_package.save()
                backend_soc = connectToBackEndServer()
                msg = f'{old_package.package_id},{old_package.destination_x},{old_package.destination_y}'
                sendAddrMSgToBackEnd(backend_soc, msg)
                backend_soc.close()
                return redirect('guest_view_all_packages')

        package = Package_Info.objects.get(package_id=nid)
        form = PackageEditForm(instance=package)
        return render(request, 'guest_edit_package_destination.html', {'form' : form})
    except Exception as e:
        messages.error(request, e)
        # print(e)
        return redirect('guest_view_all_packages')
        
def guest_view_all_packages(request):
    try:
        pac_dict = {}
        search_data = request.GET.get('q', "")
        related_packages = Package_Info.objects.none()
        if search_data:
            pac_dict["package_id__exact"] = search_data
            related_packages = Package_Info.objects.filter(**pac_dict)

        context = {'packages' : related_packages, 'search_data' : search_data}
        return render(request, 'guest_view_all_packages.html', context)
    except Exception as e:
        if not search_data.isdigit():
            messages.error(request, "numbers are only allowed")
        # print(e)
        return redirect('guest_view_all_packages')
    
def guest_view_package_detail(request, nid):
    package = Package_Info.objects.get(package_id=nid)
    context = {'package' : package}
    return render(request, "guest_view_package_detail.html", context)

def guest_check_package_position(request, nid):
    try:
        package = Package_Info.objects.get(package_id=nid)
        truck = Truck.objects.get(truck_id=package.truck.truck_id)
        backend_soc = connectToBackEndServer()
        msg = str(truck.truck_id)
        sendTruckIdMsgToBackEnd(backend_soc, msg)
        backend_soc.close()
        truck = Truck.objects.get(truck_id=package.truck.truck_id)
        context = {'package' : package, 'truck' : truck}
        return render(request, "guest_check_package_position.html", context)
    except Exception as e:
        messages.error(request, e)
        # print(e)
        return redirect('guest_view_all_packages')