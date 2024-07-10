from django.shortcuts import render

# Create your views here.
def index(request):
    # Add any necessary logic here
    context = {
        'message': 'Hello, World!'  # Example context data
    }
    return render(request, 'base.html', context)