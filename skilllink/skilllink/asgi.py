import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'skilllink.settings')

# Initialize Django ASGI application early to ensure the AppRegistry is populated
# before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import mettings.routing

# Debug Middleware to print headers/scope
class DebugMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'websocket':
            print(f"🕵️‍♂️ WS CONNECT: {scope['path']}")
            print(f"   Headers: {scope.get('headers')}")
            if 'user' in scope:
                print(f"   User: {scope['user']}")
        return await self.inner(scope, receive, send)

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": DebugMiddleware(
        AuthMiddlewareStack(
            URLRouter(
                mettings.routing.websocket_urlpatterns
            )
        )
    ),
})
