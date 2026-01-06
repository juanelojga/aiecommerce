from django.core.management.base import BaseCommand

from aiecommerce.services.enrichment_impl.orchestrator import EnrichmentOrchestrator
from aiecommerce.services.enrichment_impl.selector import EnrichmentCandidateSelector
from aiecommerce.services.scrape_tecnomega_impl.detail_orchestrator import TecnomegaDetailOrchestrator
from aiecommerce.services.specifications_impl.orchestrator import ProductSpecificationsOrchestrator
from aiecommerce.services.specifications_impl.service import ProductSpecificationsService


class Command(BaseCommand):
    help = "Enriches ProductMaster records with structured specs using AI"

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

        # Initialize the specific specification service and its orchestrator
        specs_service = ProductSpecificationsService()
        specs_orchestrator = ProductSpecificationsOrchestrator(specs_service)
        detail_orchestrator = TecnomegaDetailOrchestrator()

        # Initialize the selector and the main batch orchestrator
        selector = EnrichmentCandidateSelector()
        orchestrator = EnrichmentOrchestrator(selector, specs_orchestrator, detail_orchestrator)

        # Run the enrichment batch
        stats = orchestrator.run(force=force, dry_run=dry_run, delay=delay)

        self.stdout.write(self.style.SUCCESS(f"\nCompleted. Processed {stats['processed']}/{stats['total']} products"))
