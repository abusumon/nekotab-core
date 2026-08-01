import os
from xml.etree import ElementTree

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from importer.archive import Importer


class Command(BaseCommand):
    help = 'Import a non-existant tournament from an XML archive file.'

    def add_arguments(self, parser):
        parser.add_argument('file', help="File to import tournament data from")
        parser.add_argument('--organization', required=True,
            help="Slug of the organization to import the tournament into. "
                 "Required because Tournament.organization is NOT NULL.")
        parser.add_argument('--owner',
            help="Username to record as the tournament's owner (optional).")

    def handle(self, *args, **options):
        self.options = options
        self.filepath = self.get_data_path(options['file'])

        self.create_tournament()

    def get_data_path(self, arg):
        """Returns the file for the given command-line argument. If the
        argument is an absolute path and is an XML file, then looks there.
        Failing that, looks in the debate/data directory. Raises an exception
        if the file doesn't appear to exist, or is not an XML file."""

        def _check_return(path):
            # os.path.splitext[1] was subscripting the function itself, so this
            # raised TypeError for every input and the command could never run.
            if not os.path.isfile(path) or os.path.splitext(path)[1] != '.xml':
                raise CommandError("The path '%s' is not a valid XML file" % path)
            self.stdout.write('Importing from file: ' + path)
            return path

        if os.path.isabs(arg):  # Absolute path
            return _check_return(arg)

        # relative path, look in debate/data
        base_path = os.path.join(settings.BASE_DIR, '..', 'data')
        data_path = os.path.join(base_path, arg)
        return _check_return(data_path)

    def create_tournament(self):
        """Given the path, does everything necessary to create the tournament."""
        from organizations.models import Organization

        try:
            organization = Organization.objects.get(slug=self.options['organization'])
        except Organization.DoesNotExist:
            raise CommandError("No organization with slug '%s'" % self.options['organization'])

        owner = None
        if self.options.get('owner'):
            from django.contrib.auth import get_user_model
            try:
                owner = get_user_model().objects.get(username=self.options['owner'])
            except get_user_model().DoesNotExist:
                raise CommandError("No user named '%s'" % self.options['owner'])

        # fromstring() needs the file's text, not the file object — passing the
        # handle raised TypeError, so this path had never worked either.
        with open(self.filepath, 'r', encoding='utf-8') as handle:
            contents = handle.read()

        importer = Importer(ElementTree.fromstring(contents),
                            organization=organization, owner=owner)
        importer.import_tournament()
        self.stdout.write("Imported '%s' into organization '%s'"
                          % (importer.tournament.name, organization.slug))
