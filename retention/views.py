import os

from django.contrib.admin.views.decorators import staff_member_required
from django.http import FileResponse, Http404, HttpResponseBadRequest

from .models import TournamentDeletionLog


@staff_member_required
def download_archive(request, log_id):
    """Serve an archive zip/json file for download.

    Only staff users can access this.  The archive_path on the
    ``TournamentDeletionLog`` entry must point to a file on disk.
    """
    try:
        log = TournamentDeletionLog.objects.get(pk=log_id)
    except TournamentDeletionLog.DoesNotExist:
        raise Http404("Deletion log entry not found.")

    if not log.archive_path:
        return HttpResponseBadRequest("No archive file associated with this log entry.")

    if not os.path.isfile(log.archive_path):
        return HttpResponseBadRequest(
            f"Archive file no longer exists on disk: {log.archive_path}\n\n"
            "On ephemeral-disk platforms (like Heroku) archives are lost on "
            "dyno restart.  Use --export-dir with a persistent volume or "
            "download promptly after export."
        )

    filename = os.path.basename(log.archive_path)
    return FileResponse(
        open(log.archive_path, 'rb'),
        as_attachment=True,
        filename=filename,
    )
