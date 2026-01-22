# app/api/v1/sanitization_middleware.py
"""
Middleware and utilities for sanitizing user-generated content
"""
from app.core.security import sanitize_html, sanitize_input


def sanitize_resume_sections(sections: list) -> list:
    """
    Sanitize resume sections to prevent XSS.
    
    Args:
        sections: List of resume sections with title and content
        
    Returns:
        List of sanitized resume sections
    """
    sanitized = []
    for section in sections:
        sanitized_section = section.copy() if isinstance(section, dict) else section.model_dump()
        
        # Sanitize title and content
        if 'title' in sanitized_section:
            sanitized_section['title'] = sanitize_input(str(sanitized_section['title']))
        
        if 'content' in sanitized_section:
            # Content may contain HTML formatting, sanitize it
            sanitized_section['content'] = sanitize_html(str(sanitized_section['content']))
        
        sanitized.append(sanitized_section)
    
    return sanitized


def sanitize_user_profile(profile_data: dict) -> dict:
    """
    Sanitize user profile data to prevent XSS.
    
    Args:
        profile_data: User profile dictionary
        
    Returns:
        Sanitized profile data
    """
    sanitized = profile_data.copy()
    
    # Text fields that should be plain text (no HTML)
    text_fields = ['full_name', 'phone', 'location', 'summary']
    for field in text_fields:
        if field in sanitized and sanitized[field]:
            sanitized[field] = sanitize_input(str(sanitized[field]))
    
    # Lists of text
    if 'skills' in sanitized and sanitized['skills']:
        sanitized['skills'] = [sanitize_input(str(skill)) for skill in sanitized['skills']]
    
    # Nested structures (experience, education, etc.)
    for list_field in ['experience', 'education', 'certifications']:
        if list_field in sanitized and sanitized[list_field]:
            sanitized_list = []
            for item in sanitized[list_field]:
                sanitized_item = {}
                for key, value in item.items():
                    if isinstance(value, str):
                        sanitized_item[key] = sanitize_input(value)
                    else:
                        sanitized_item[key] = value
                sanitized_list.append(sanitized_item)
            sanitized[list_field] = sanitized_list
    
    return sanitized
