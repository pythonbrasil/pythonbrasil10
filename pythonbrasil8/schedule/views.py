# -*- coding: utf-8 -*-

from django import http, shortcuts
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.template import response, RequestContext
from django.utils.translation import ugettext as _
from django.views.generic import CreateView, View

from pythonbrasil8.core.views import LoginRequiredMixin
from pythonbrasil8.schedule.forms import SessionForm
from pythonbrasil8.schedule.models import Session, Track


VOTE = {'up': 1, 'down': -1, 'neutral': 0}


class SubscribeView(LoginRequiredMixin, CreateView):
    form_class = SessionForm
    template_name = "schedule/subscribe.html"

    def get_success_url(self):
        return reverse("dashboard-index")

    def get_extra_speakers(self):
        es = self.request.POST.getlist("extra_speakers")
        return User.objects.filter(Q(username__in=es) | Q(email__in=es))

    def form_valid(self, form):
        r = super(SubscribeView, self).form_valid(form)
        spkrs = [self.request.user]
        spkrs.extend(self.get_extra_speakers())
        self.object.speakers.add(*spkrs)
        return r

    def get(self, request, *args, **kwargs):
        r = super(SubscribeView, self).get(request, *args, **kwargs)
        r.context_data["tracks"] = Track.objects.all()
        return r

    def post(self, request, *args, **kwargs):
        r = super(SubscribeView, self).post(request, *args, **kwargs)
        if isinstance(r, http.HttpResponseRedirect):
            messages.success(request, _("Session successfully submitted!"), fail_silently=True)
        else:
            r.context_data["extra_speakers"] = self.request.POST.getlist("extra_speakers")
        return r


class EditSessionView(LoginRequiredMixin, View):
    form_class = SessionForm
    template_name = "schedule/edit-session.html"

    def get(self, request, id):
        session = shortcuts.get_object_or_404(Session, pk=id, speakers=request.user)
        form = self.form_class(instance=session)
        extra_speakers = session.speakers.exclude(username=request.user.username)
        tracks = Track.objects.all()
        return response.TemplateResponse(request, self.template_name, {"session": session, "form": form, "tracks": tracks,
            "extra_speakers": extra_speakers})

    def post(self, request, id):
        session = shortcuts.get_object_or_404(Session, pk=id, speakers=request.user)
        form = self.form_class(request.POST, instance=session)
        if form.is_valid():
            form.save()
            messages.success(request, _("Session successfully updated!"), fail_silently=True)
            return http.HttpResponseRedirect(reverse("dashboard-sessions"))
        tracks = Track.objects.all()
        return response.TemplateResponse(request, self.template_name, {"session": session, "form": form, "tracks": tracks})


class DeleteSessionView(LoginRequiredMixin, View):

    def get(self, request, id):
        session = shortcuts.get_object_or_404(Session, pk=id, speakers=request.user)
        session.delete()
        messages.success(request, _("Session successfully deleted!"), fail_silently=True)
        return http.HttpResponseRedirect(reverse("dashboard-sessions"))


class FinishedProposalsView(LoginRequiredMixin, View):
    template_name = u"schedule/finished_proposals.html"

    def get(self, request):
        return response.TemplateResponse(request, self.template_name)


def schedule(request):
    '''Show accepted talk proposals'''
    tracks = Track.objects.all().order_by('name_en')
    tracks_and_sessions = {}
    for track in tracks:
        sessions = Session.objects.filter(track=track, type='talk',
                                          status__in=['accepted', 'confirmed'])
        tracks_and_sessions[track] = sessions
    data = {'tracks_and_sessions': tracks_and_sessions.items()}
    return shortcuts.render_to_response('schedule.html', data,
            context_instance=RequestContext(request))


def track_page(request, track_slug):
    return http.HttpResponseRedirect(reverse("schedule"))


def proposal_page(request, track_slug, proposal_slug):
    shortcuts.get_object_or_404(Track, slug=track_slug)
    proposal = shortcuts.get_object_or_404(Session, slug=proposal_slug)

    speakers = []
    for speaker in proposal.speakers.all():
        try:
            profile = speaker.get_profile()
            name = profile.name
            bio = profile.description
            twitter = profile.twitter
            institution = profile.institution
            profession = profile.profession
        except ObjectDoesNotExist:
            name = speaker.username
            twitter = ''
            bio = ''
            institution = ''
            profession = ''
        speakers.append({'name': name, 'twitter': twitter, 'bio': bio,
                         'institution': institution, 'profession': profession})
    data = {'proposal': proposal, 'speakers': speakers}
    return shortcuts.render_to_response('proposal.html', data,
            context_instance=RequestContext(request))


def vote_page(request):
    return http.HttpResponseRedirect(reverse("schedule"))
