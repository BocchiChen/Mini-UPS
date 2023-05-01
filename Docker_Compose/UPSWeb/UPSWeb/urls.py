"""UPSWeb URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from user_management import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.guestHomePage, name='guest_home'),
    path('user/home', views.homePage, name='home'),
    path('register/', views.registerPage, name="register"),
    path('login/', views.loginPage, name="login"),
    path('logout/', views.logoutPage, name='logout'),
    path('user/modify_ups_account/', views.modify_ups_account, name='modify_ups_account'),
    path('user/profile/', views.profilePage, name='user_profile'),
    path('user/view_all_packages/', views.view_all_packages, name='view_all_packages'),
    path('user/<int:nid>/edit_package_destination/', views.edit_package_desination, name='edit_package_desination'),
    path('guest/<int:nid>/edit_package_destination/', views.guest_edit_package_desination, name='guest_edit_package_desination'),
    path('user/<int:nid>/check_package_position/', views.check_package_position, name='check_package_position'),
    path('guest/<int:nid>/check_package_position/', views.guest_check_package_position, name='guest_check_package_position'),
    path('user/<int:nid>/view_package_detail/', views.view_package_detail, name='view_package_detail'),
    path('guest/view_all_packages/', views.guest_view_all_packages, name='guest_view_all_packages'),
    path('guest/<int:nid>/view_package_detail/', views.guest_view_package_detail, name='guest_view_package_detail'),
    path('user/<int:nid>/evaluation/', views.user_evaluation, name='user_evaluation'),
    path('user/view_evaluation/', views.user_view_evaluations, name='user_view_evaluations'),
]
