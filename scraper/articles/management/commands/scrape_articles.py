from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Run scraper, websites are stored in websites.json.'

    def handle(self, *args, **options):
        # Import locally so this module can be imported without hitting DB at import time
        from articles.utils import scraper_run

        result = scraper_run()
