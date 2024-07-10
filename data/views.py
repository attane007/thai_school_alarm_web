from django.shortcuts import render
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
import os

def check_initial(view_func):
    def wrapper(request, *args, **kwargs):
        # Check if db.sqlite3 file exists
        db_file = 'db.sqlite3'  # Replace with your actual path
        if not os.path.exists(db_file):
            # Run makemigrations and migrate
            try:
                call_command('makemigrations', 'data')
                call_command('migrate')
            except CommandError as e:
                # Handle any errors that may occur during migrations
                return render(request, 'error.html', {'error_message': str(e)})
        cursor = connection.cursor()
        table_name = 'data_bell'  # Replace with your actual table name
        table_exists = False
        try:
            cursor.execute(f"SELECT 1 FROM {table_name} LIMIT 1;")
            table_exists = True
        except Exception as ex:
            # Handle exception if needed
            pass
        finally:
            cursor.close()

        if not table_exists:
            # Run makemigrations and migrate again if the table doesn't exist
            try:
                call_command('makemigrations', 'data')
                call_command('migrate')
            except CommandError as e:
                # Handle any errors that may occur during migrations
                return render(request, 'error.html', {'error_message': str(e)})
        
        # Call the original view function
        return view_func(request, *args, **kwargs)
    
    return wrapper


# Create your views here.
@check_initial
def index(request):
    # Add any necessary logic here
    context = {
        'message': 'Hello, World!'  # Example context data
    }
    return render(request, 'base.html', context)

def setup(request):
    print("set up")