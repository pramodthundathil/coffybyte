# =============== MIDDLEWARE FOR STORE CONTEXT ===============
from .models import Store

class StoreMiddleware:
    """Middleware to set current store context"""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Get store from header or subdomain
        store_code = request.META.get('HTTP_X_STORE_CODE')
        if not store_code:
            # Try to get from subdomain
            host = request.get_host()
            if '.' in host:
                store_code = host.split('.')[0]
        
        if store_code:
            try:
                store = Store.objects.get(store_code=store_code, is_active=True)
                request.current_store = store
            except Store.DoesNotExist:
                request.current_store = None
        else:
            request.current_store = None
            
        response = self.get_response(request)
        return response
    

    
# Middleware for store context
class StoreContextMiddleware:
    """
    Middleware to add store context to requests
    """
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Extract store_code from various sources
        store_code = None
        
        if request.method in ['POST', 'PUT', 'PATCH']:
            if hasattr(request, 'data') and request.data:
                store_code = request.data.get('store_code')
        
        if not store_code:
            store_code = request.GET.get('store_code')
        
        if not store_code and hasattr(request, 'resolver_match') and request.resolver_match:
            store_code = request.resolver_match.kwargs.get('store_code')
        
        if not store_code:
            # Try to extract from path
            path_parts = request.path.strip('/').split('/')
            if 'stores' in path_parts:
                try:
                    store_index = path_parts.index('stores')
                    if len(path_parts) > store_index + 1:
                        store_code = path_parts[store_index + 1]
                except (ValueError, IndexError):
                    pass
        
        request.store_code = store_code
        
        response = self.get_response(request)
        return response