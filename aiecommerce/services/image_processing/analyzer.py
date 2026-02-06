import logging

from PIL import Image

logger = logging.getLogger(__name__)


class BackgroundAnalyzer:
    """Analyzes image background characteristics."""

    def __init__(self, dark_threshold: int = 45):
        """Initialize the analyzer with a luminance threshold.

        Args:
            dark_threshold: Luminance value below which background is considered dark.
        """
        self.dark_threshold = dark_threshold

    def is_dark_background(self, img: Image.Image) -> bool:
        """Detect if the image background is dark by sampling edge luminance.

        Args:
            img: The PIL Image to analyze.

        Returns:
            True if the background is dark, False otherwise.
        """
        # If image has an alpha channel, it might be transparent, which we don't consider "dark"
        if img.mode == "RGBA":
            # Just check the corners, if they are transparent, it's not a dark background
            width, height = img.size
            corners = [(0, 0), (width - 1, 0), (0, height - 1), (width - 1, height - 1)]
            for pos in corners:
                pixel = img.getpixel(pos)
                if isinstance(pixel, tuple) and len(pixel) == 4 and pixel[3] == 0:
                    logger.debug("Transparent corner detected, not a dark background.")
                    return False

        # Convert to grayscale to analyze luminance
        gray_img = img.convert("L")
        width, height = gray_img.size

        # Sample points at the edges and corners where background is expected
        samples = [
            (0, 0),
            (width - 1, 0),
            (0, height - 1),
            (width - 1, height - 1),
            (width // 2, 0),
            (width // 2, height - 1),
            (0, height // 2),
            (width - 1, height // 2),
        ]

        pixel_values = []
        for pos in samples:
            pixel = gray_img.getpixel(pos)
            if isinstance(pixel, int):
                pixel_values.append(float(pixel))
            elif isinstance(pixel, tuple):
                pixel_values.append(float(pixel[0]))

        if not pixel_values:
            return False

        avg_luminance = sum(pixel_values) / len(pixel_values)
        logger.debug(f"Average edge luminance: {avg_luminance} (threshold: {self.dark_threshold})")

        return avg_luminance < self.dark_threshold
