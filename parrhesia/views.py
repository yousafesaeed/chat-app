from django.shortcuts import render
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.db import IntegrityError
from django.views.decorators.csrf import csrf_exempt
import json

from .models import User, Channel, Channel_person, Channel_message, Invite


def index(request):
    return render(request, 'parrhesia/index.html')


def channel(request, id):
    if request.user.is_authenticated:
        return render(request, 'parrhesia/channel.html')
    else:
        return render(request, 'parrhesia/error.html', {
            'error_header': '401 Unauthorized',
            'error_discription': 'Click <a href=\'/login\'>here</a> to log in before you vist this page.'
        })


def channels(request):
    if request.user.is_authenticated:
        return render(request, 'parrhesia/channels.html')
    else:
        return render(request, 'parrhesia/error.html', {
            'error_header': '401 Unauthorized',
            'error_discription': 'Click <a href=\'/login\'>here</a> to log in before you vist this page.'
        })


def invite(request):
    if request.user.is_authenticated:
        channels_queryset = Channel_person.objects.filter(
            user=User(request.user.id)).values()

        channels = []
        for channel in channels_queryset:
            channel_object = Channel.objects.filter(
                id=channel['channel_id']).values()
            channels.append(channel_object[0])

        return render(request, 'parrhesia/invite.html', {
            'channels': channels
        })
    else:
        return render(request, 'parrhesia/error.html', {
            'error_header': '401 Unauthorized',
            'error_discription': 'Click <a href=\'/login\'>here</a> to log in before you vist this page.'
        })


def invites(request):
    if request.user.is_authenticated:
        return render(request, 'parrhesia/invites.html')
    else:
        return render(request, 'parrhesia/error.html', {
            'error_header': '401 Unauthorized',
            'error_discription': 'Click <a href=\'/login\'>here</a> to log in before you vist this page.'
        })


def page_not_found_view(request, exception):
    return render(request, 'parrhesia/404.html', status=404)


def login_view(request):
    logout(request)

    next = request.GET.get('next')
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            if not next:
                return HttpResponseRedirect(reverse("index"))
            else:
                return HttpResponseRedirect(next)
        else:
            return render(request, "parrhesia/login.html", {
                "message": "Invalid username and/or password."
            })
    else:
        return render(request, "parrhesia/login.html")


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


def register(request):
    logout(request)

    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]

        if password != confirmation:
            return render(request, "parrhesia/register.html", {
                "message": "Passwords must match."
            })

        try:
            user = User.objects.create_user(username, email, password)
            user.save()
        except IntegrityError:
            return render(request, "parrhesia/register.html", {
                "message": "Username already taken."
            })

        login(request, user)
        return HttpResponseRedirect(reverse("index"))
    else:
        return render(request, "parrhesia/register.html")


# ------API Views------


def channelsAPI(request):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    channels_in = Channel_person.objects.filter(
        user=User(request.user.id)).values()

    channels = []
    i = 0
    for channel_in in channels_in:
        channel = Channel.objects.filter(id=channel_in["channel_id"]).values()
        channels.append(channel[0])
        i += 1

    return JsonResponse(channels, safe=False)


@csrf_exempt
def newchannel(request):
    request_json = json.loads(request.body)

    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    channel = Channel(creator=User(request.user.id),
                      name=request_json.get("channel_name", ""))
    channel.save()

    channel_person = Channel_person(
        user=User(request.user.id), channel=Channel(channel.id))
    channel_person.save()
    return HttpResponse(status=200)


@csrf_exempt
def send_invite(request):
    request_json = json.loads(request.body)

    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    recipient_object = User.objects.filter(
        username=request_json.get("recipient", "")).values()

    if str(recipient_object) == '<QuerySet []>':
        return HttpResponse(status=404)

    recipient_id = recipient_object[0]["id"]

    channel = request_json.get("channel", "")
    channel_person = Channel_person.objects.filter(
        user=User(request.user.id), channel=Channel(channel))

    if channel_person == []:
        return HttpResponse(status=401)

    check_recipient = User.objects.filter(
        username=request_json.get("recipient", ""))
    if check_recipient == []:
        return HttpResponse(status=404)

    channel_person_recipient = Channel_person.objects.filter(
        channel=Channel(channel), user=User(recipient_id)).values()

    if str(channel_person_recipient) != '<QuerySet []>':
        return HttpResponse(status=409)

    check_invite = Invite.objects.filter(sender=User(request.user.id), reciever=User(
        recipient_id), channel=Channel(channel)).values()
    if str(check_invite) != '<QuerySet []>':
        return HttpResponse(status=409)

    invite = Invite(sender=User(request.user.id), reciever=User(
        recipient_id), channel=Channel(channel))
    invite.save()
    return HttpResponse(status=200)


def list_invites(request):
    invites_object = Invite.objects.filter(
        reciever=User(request.user.id), accepted=False)
    invites_queryset = Invite.objects.filter(
        reciever=User(request.user.id), accepted=False).values()

    invites = []
    i = 0
    for invite in invites_object:
        dict = invites_queryset[i]
        dict["channel_name"] = str(invite.channel.name)
        dict["channel_id"] = str(invite.channel.id)
        invites.append(dict)
        i += 1
    return JsonResponse(invites, safe=False)


@csrf_exempt
def accept_invite(request):
    request_json = json.loads(request.body)

    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    invite = Invite.objects.filter(reciever=User(request.user.id), id=int(
        request_json.get("invite_id", ""))).values()
    if invite == []:
        return HttpResponse(status=404)

    invite = Invite.objects.get(reciever=User(
        request.user.id), id=int(request_json.get("invite_id", "")))
    invite.accepted = True
    invite.save()

    channel_person = Channel_person(
        user=User(request.user.id), channel=Channel(invite.channel.id))
    channel_person.save()
    return HttpResponseRedirect('/channel/'+str(invite.channel.id))


@csrf_exempt
def decline_invite(request):
    request_json = json.loads(request.body)

    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    invite = Invite.objects.filter(reciever=User(
        request.user.id), id=request_json.get("invite_id", "")).values()
    if invite == []:
        return HttpResponse(status=404)

    invite = Invite.objects.get(reciever=User(
        request.user.id), id=request_json.get("invite_id", ""))
    invite.delete()
    return HttpResponse(status=200)


def user(request, id):
    userqueryset = User.objects.filter(id=id).values()
    user = userqueryset[0]
    return JsonResponse(user['username'], safe=False)


@csrf_exempt
def message(request):
    request_json = json.loads(request.body)

    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    channel = request_json.get("channel", "")
    text = request_json.get("text", "")

    if Channel_person.objects.filter(channel=Channel(int(channel)), user=User(request.user.id)).values()[0] == []:
        return HttpResponse(status=401)

    message = Channel_message(channel=Channel(
        int(channel)), user=User(request.user.id), text=text)
    message.save()

    return HttpResponse(status=200)


def messages(request, channel_id):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    if Channel_person.objects.filter(channel=Channel(int(channel_id)), user=User(request.user.id)).values() == '<QuerySet []>':
        return HttpResponse(status=401)

    messages_queryset = Channel_message.objects.filter(
        channel=Channel(channel_id)).order_by('-id').values()
    messages = []
    for message in messages_queryset:
        messages.append(message)
    return JsonResponse(messages, safe=False)


def channelAPI(request, id):
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    channel = Channel.objects.filter(id=int(id)).values()
    channel = channel[0]
    return JsonResponse(channel, safe=False)
