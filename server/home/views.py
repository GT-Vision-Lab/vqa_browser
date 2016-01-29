from django.http import HttpResponse, HttpResponseRedirect

from .models import Counter

#@xframe_options_exempt


def index(request):

    if len(Counter.objects.all()) == 0:
        c = Counter(counter=0)
        c.save()

    first_counter = Counter.objects.all()[0]
    first_counter.counter += 1
    first_counter.save()
    resp = ('Welcome to our server.</br>It has been accessed %s times')

    return HttpResponse(resp % first_counter)
