from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect
from functools import wraps

LOGIN_REQUIRED_MESSAGE = "Please log in first to do that."

def supabase_auth_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not getattr(request, 'supabase_user', None):
            # JavaScript (fetch) calls get JSON they can read, not an HTML redirect
            if request.path.startswith('/api/'):
                return JsonResponse({"error": LOGIN_REQUIRED_MESSAGE}, status=401)
            messages.info(request, LOGIN_REQUIRED_MESSAGE)
            return redirect('login')  # Ensure you have a URL named 'login'
        return view_func(request, *args, **kwargs)
    return _wrapped_view
