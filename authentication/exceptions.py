# exceptions.py
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError
from django.db import IntegrityError
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):
    """
    Custom exception handler for the POS system
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)
    
    # Add custom handling for specific exceptions
    if response is not None:
        custom_response_data = {
            'error': True,
            'message': 'An error occurred',
            'details': response.data,
            'status_code': response.status_code
        }
        
        # Handle specific error types
        if response.status_code == 400:
            custom_response_data['message'] = 'Validation error'
        elif response.status_code == 401:
            custom_response_data['message'] = 'Authentication required'
        elif response.status_code == 403:
            custom_response_data['message'] = 'Permission denied'
        elif response.status_code == 404:
            custom_response_data['message'] = 'Resource not found'
        elif response.status_code == 500:
            custom_response_data['message'] = 'Internal server error'
        
        response.data = custom_response_data
    
    # Handle Django ValidationError
    elif isinstance(exc, ValidationError):
        logger.error(f"Validation Error: {exc}")
        response = Response({
            'error': True,
            'message': 'Validation error',
            'details': {'non_field_errors': exc.messages},
            'status_code': 400
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Handle Django IntegrityError
    elif isinstance(exc, IntegrityError):
        logger.error(f"Integrity Error: {exc}")
        response = Response({
            'error': True,
            'message': 'Database integrity error',
            'details': {'error': 'This operation violates database constraints'},
            'status_code': 400
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Handle unexpected errors
    else:
        logger.error(f"Unexpected Error: {exc}")
        response = Response({
            'error': True,
            'message': 'An unexpected error occurred',
            'details': {'error': str(exc)} if settings.DEBUG else {},
            'status_code': 500
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return response