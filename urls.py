from django.urls import path
import views

urlpatterns = [
    path('', views.index, name='index'),
    path('chat/', views.chat_api, name='chat_api'),
]