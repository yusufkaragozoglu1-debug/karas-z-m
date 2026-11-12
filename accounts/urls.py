from django.urls import path

from . import views

urlpatterns = [
    path("kayit/", views.SignupView.as_view(), name="signup"),
    path("giris/", views.SiteLoginView.as_view(), name="login"),
    path("cikis/", views.SiteLogoutView.as_view(), name="logout"),
]
