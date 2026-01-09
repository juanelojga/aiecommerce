import instructor
from django.conf import settings
from django.core.management.base import BaseCommand
from openai import OpenAI

from aiecommerce.services.ai_content_generator_impl.description_generator import DescriptionGeneratorService
from aiecommerce.services.ai_content_generator_impl.orchestrator import AIContentOrchestrator
from aiecommerce.services.ai_content_generator_impl.selector import AIContentGeneratorCandidateSelector
from aiecommerce.services.ai_content_generator_impl.title_generator import TitleGeneratorService


class Command(BaseCommand):
    help = "Enriches ProductMaster records with structured content using AI"

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Reprocess products that already have specs")
        parser.add_argument("--dry-run", action="store_true", help="Perform API calls without saving to DB")
        parser.add_argument("--delay", type=float, default=0.5, help="Delay between products")

    def handle(self, *args, **options):
        force = options["force"]
        dry_run = options["dry_run"]
        delay = options["delay"]

        if dry_run:
            self.stdout.write(self.style.WARNING("--- DRY RUN MODE ACTIVATED ---"))

        api_key = settings.OPENROUTER_API_KEY
        base_url = settings.OPENROUTER_BASE_URL

        client = instructor.from_openai(OpenAI(api_key=api_key, base_url=base_url))

        # Initialize the specific specification service and its orchestrator
        title_generator = TitleGeneratorService(client)
        description_generator = DescriptionGeneratorService(client)

        selector = AIContentGeneratorCandidateSelector()

        orchestrator = AIContentOrchestrator(title_generator=title_generator, description_generator=description_generator, client=client, selector=selector)

        # Run the enrichment batch
        stats = orchestrator.run(force=force, dry_run=dry_run, delay=delay)

        self.stdout.write(self.style.SUCCESS(f"\nCompleted. Processed {stats['processed']}/{stats['total']} products"))
