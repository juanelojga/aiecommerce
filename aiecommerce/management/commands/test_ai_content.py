"""
A management command to test the AIContentOrchestrator for generating SEO-optimized content.
"""

from django.core.management.base import BaseCommand, CommandError

from aiecommerce.models import ProductMaster
from aiecommerce.services.mercadolibre_impl.ai_content.description_generator import DescriptionGeneratorService
from aiecommerce.services.mercadolibre_impl.ai_content.orchestrator import AIContentOrchestrator
from aiecommerce.services.mercadolibre_impl.ai_content.title_generator import TitleGeneratorService


class Command(BaseCommand):
    """
    A management command that triggers the AI content generation for a specific product.

    This command is a testing utility for Task ML-08 (Content Builder). It allows manually
    triggering the content generation process for a single product to verify the output of
    the `AIContentOrchestrator`. It supports a dry-run mode to prevent database writes.
    """

    help = "Triggers AI content generation for a specific product."

    def add_arguments(self, parser):
        """
        Adds command-line arguments for the command.
        """
        parser.add_argument(
            "product_code",
            type=str,
            help="The unique code of the product to process.",
        )
        parser.add_argument(
            "--no-dry-run",
            action="store_false",
            dest="dry_run",
            help="If set, the command will save the generated content to the database.",
        )
        parser.set_defaults(dry_run=True)
        parser.add_argument(
            "--force",
            action="store_true",
            default=False,
            help="If set, forces content regeneration even if it already exists.",
        )

    def handle(self, *args, **options):
        """
        The main logic for the command.
        """
        product_code = options["product_code"]
        dry_run = options["dry_run"]
        force = options["force"]

        try:
            product = ProductMaster.objects.get(code=product_code)
        except ProductMaster.DoesNotExist:
            raise CommandError(f'Product with code "{product_code}" does not exist.')

        self.stdout.write(self.style.SUCCESS(f"Processing product: {product.code}"))
        self.stdout.write(f"  Category: {product.category}")
        self.stdout.write(f"  Original Description: {product.description}")

        title_generator = TitleGeneratorService()
        description_generator = DescriptionGeneratorService()
        orchestrator = AIContentOrchestrator(title_generator=title_generator, description_generator=description_generator)
        result = orchestrator.process_product_content(product, dry_run=dry_run, force_refresh=force)

        if result and not result.get("error"):
            self.stdout.write(self.style.NOTICE("\n--- Generated Content ---"))
            self.stdout.write(f"GENERATED SEO TITLE ({len(product.seo_title or '')} chars): {product.seo_title}")
            self.stdout.write(f"GENERATED SEO DESCRIPTION: {product.seo_description}")

            if dry_run:
                self.stdout.write(self.style.WARNING("\n[DRY RUN] Content was not saved."))
            else:
                self.stdout.write(self.style.SUCCESS("\nContent has been saved to the database."))
        else:
            self.stdout.write(self.style.WARNING("Content generation was skipped. Use --force to override."))
