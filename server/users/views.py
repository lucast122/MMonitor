from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm


def register(request):
    """Register a new user"""
    if request.method != "POST":
        # Display black registration form
        form = UserCreationForm()

    else:
        # Process completed form
        form = UserCreationForm(data=request.POST)

        if form.is_valid():
            new_user = form.save()
            # default to non-active so admin needs to authorize user
            new_user.is_active = False
            new_user.save()

            # send mail to notify admin, change email backend in settings.py!
            send_mail(
                '<Subject>User {} has been created' .format(new_user.username),
                '<Body>A new user has been created, please activate',
                'django@site.com',
                ['admin@mail.com'],
                fail_silently=False,
            )

            # Login and redirect to homepage
            login(request, new_user)
            return redirect("main:index")

    # Display a blank or invalid form
    context = {"form": form}

    return render(request, "registration/register.html", context)
