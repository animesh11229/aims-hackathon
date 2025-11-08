from flask import session
from functools import wraps

def check_logged_in(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'login' in session:
            return func(*args, **kwargs)
        return "u are not logged in"
    return wrapper