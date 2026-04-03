from django.urls import path

from . import views

app_name = 'chat'

urlpatterns = [
    # Tournament management (tab director)
    path('', views.ChatManageView.as_view(), name='chat-manage'),
    # Room view / PIN entry
    path('<str:room_type>/', views.ChatRoomView.as_view(), name='chat-room'),
    # PIN verification POST
    path('<str:room_type>/pin/', views.ChatPinVerifyView.as_view(), name='chat-pin-verify'),
    # JSON history API
    path('<str:room_type>/history/', views.ChatHistoryView.as_view(), name='chat-history'),
]
