import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Booking, Message
from accounts.models import Profile, Notification

class MeetingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            self.booking_id = self.scope['url_route']['kwargs']['booking_id']
            self.room_group_name = f"meeting_{self.booking_id}"
            self.user = self.scope["user"]

            if not self.user.is_authenticated:
                await self.close()
                return

            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            await self.accept()
            
            # Send previous messages
            messages = await self.get_messages()
            await self.send(text_data=json.dumps({
                'type': 'history',
                'messages': messages
            }))
        except Exception as e:
            print(f"Error in MeetingConsumer connect: {e}")
            await self.close()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        data = json.loads(text_data)
        message_content = data.get('message')
        
        if message_content:
            # Save message (this triggers the broadcast_message signal in signals.py)
            await self.save_message(message_content)

    # Receive message from room group
    async def chat_message(self, event):
        message = event['message']
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': message
        }))
        
    async def signal_message(self, event):
         # Keep for backward compatibility or signaling if needed
        message = event['message']
        await self.send(text_data=json.dumps(message))

    @database_sync_to_async
    def get_messages(self):
        booking = Booking.objects.get(id=self.booking_id)
        messages = Message.objects.filter(booking=booking).order_by('timestamp')
        return [
            {
                'sender': msg.sender.user.username,
                'content': msg.content,
                'timestamp': msg.timestamp.isoformat()
            }
            for msg in messages
        ]

    @database_sync_to_async
    def save_message(self, content):
        booking = Booking.objects.get(id=self.booking_id)
        profile = Profile.objects.get(user=self.user)
        message = Message.objects.create(booking=booking, sender=profile, content=content)
        return {
            'sender': profile.user.username,
            'content': message.content,
            'timestamp': message.timestamp.isoformat()
        }

class UserConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if not self.user.is_authenticated:
            await self.close()
            return

        self.room_group_name = f"user_{self.user.id}"

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        
        # Send history
        history = await self.get_notification_history()
        await self.send(text_data=json.dumps({
            'type': 'notification_history',
            'notifications': history['notifications'],
            'unread_count': history['unread_count']
        }))

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        data = json.loads(text_data)
        if data.get('type') == 'mark_read':
            await self.mark_notifications_read()
            await self.send(text_data=json.dumps({
                'type': 'unread_count_update',
                'count': 0
            }))
        elif data.get('type') == 'mark_single_read':
            notification_id = data.get('notification_id')
            if notification_id:
                await self.mark_single_notification_read(notification_id)
                new_count = await self.get_unread_count()
                await self.send(text_data=json.dumps({
                    'type': 'unread_count_update',
                    'count': new_count
                }))

    @database_sync_to_async
    def get_notification_history(self):
        notifications = Notification.objects.filter(user=self.user).order_by('-timestamp')[:15]
        unread_count = Notification.objects.filter(user=self.user, is_read=False).count()
        return {
            'notifications': [
                {
                    'id': n.id,
                    'title': n.title,
                    'body': n.body,
                    'link': n.link,
                    'is_read': n.is_read,
                    'timestamp': n.timestamp.isoformat()
                } for n in notifications
            ],
            'unread_count': unread_count
        }

    @database_sync_to_async
    def mark_notifications_read(self):
        Notification.objects.filter(user=self.user, is_read=False).update(is_read=True)

    @database_sync_to_async
    def mark_single_notification_read(self, notification_id):
        Notification.objects.filter(user=self.user, id=notification_id, is_read=False).update(is_read=True)

    async def notification(self, event):
        unread_count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': event['notification'],
            'unread_count': unread_count
        }))

    @database_sync_to_async
    def get_unread_count(self):
        return Notification.objects.filter(user=self.user, is_read=False).count()

    async def status_update(self, event):
        unread_count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'status_update',
            'booking_id': event['booking_id'],
            'new_status': event['new_status'], # Note: JS expects new_status based on booking_list.html:179
            'message': event['message'],
            'action_urls': event.get('action_urls', {}),
            'is_provider': event.get('is_provider', False),
            'unread_count': unread_count
        }))

    async def token_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'token_update',
            'balance': event['balance']
        }))

    async def new_booking_request(self, event):
        await self.send(text_data=json.dumps({
            'type': 'new_booking_request',
            'booking_id': event['booking_id'],
            'role': event.get('role', 'provider')
        }))

    async def new_swap_request(self, event):
        await self.send(text_data=json.dumps({
            'type': 'new_swap_request',
            'swap_id': event['swap_id']
        }))
        
    async def force_logout(self, event):
        """
        Handle force logout event triggered by backend (e.g., getting blocked).
        """
        await self.send(text_data=json.dumps({
            'type': 'force_logout',
            'message': event['message']
        }))
