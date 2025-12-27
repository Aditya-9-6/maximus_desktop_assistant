from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from maximus_logic import MaximusAssistant
import json

# Initialize once (or per request if statelessness is preferred)
assistant = MaximusAssistant()

def index(request):
    return render(request, 'index.html')

@csrf_exempt
def chat_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '')
            response_text = assistant.process_command(user_message)
            return JsonResponse({'response': response_text, 'status': 'success'})
        except Exception as e:
            return JsonResponse({'response': f"Error: {str(e)}", 'status': 'error'})
    return JsonResponse({'response': 'Invalid request', 'status': 'error'}, status=400)