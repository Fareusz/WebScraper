from django.urls import path
from . import views

app_name = 'articles'

urlpatterns = [
    path('articles/', views.ArticleListView.as_view(), name='list'),
    path('articles/<int:pk>/', views.ArticleRetrieveView.as_view(), name='detail'),

]
