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
from user_management.views import *

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', guestHomePage, name='guest_home'),
    path('user/home', homePage, name='home'),
    path('register/', registerPage, name="register"),
    path('login/', loginPage, name="login"),
    path('logout/', logoutPage, name='logout'),
    path('user/modify_ups_account/', modify_ups_account, name='modify_ups_account'),
    path('user/profile/', profilePage, name='user_profile'),
    path('user/view_all_packages/', view_all_packages, name='view_all_packages'),
    path('user/<int:nid>/edit_package_destination/', edit_package_desination, name='edit_package_desination'),
    path('guest/<int:nid>/edit_package_destination/', guest_edit_package_desination, name='guest_edit_package_desination'),
    path('user/<int:nid>/check_package_position/', check_package_position, name='check_package_position'),
    path('guest/<int:nid>/check_package_position/', guest_check_package_position, name='guest_check_package_position'),
    path('user/<int:nid>/view_package_detail/', view_package_detail, name='view_package_detail'),
    path('guest/view_all_packages/', guest_view_all_packages, name='guest_view_all_packages'),
    path('guest/<int:nid>/view_package_detail/', guest_view_package_detail, name='guest_view_package_detail'),
]
