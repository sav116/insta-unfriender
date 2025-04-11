#!/usr/bin/env python3
"""
Script to check available exceptions in instagrapi module
"""
import inspect
import sys

try:
    import instagrapi
    import instagrapi.exceptions as exceptions
    
    print(f"Instagrapi version: {instagrapi.__version__}")
    print("Available exceptions in instagrapi.exceptions:")
    print("-" * 50)
    
    # Get all members from the exceptions module
    exception_classes = []
    for name, obj in inspect.getmembers(exceptions):
        if inspect.isclass(obj) and issubclass(obj, Exception):
            exception_classes.append(name)
    
    # Print sorted list of exceptions
    for name in sorted(exception_classes):
        print(f"- {name}")
    
except ImportError:
    print("Error: instagrapi module not found.")
    sys.exit(1) 