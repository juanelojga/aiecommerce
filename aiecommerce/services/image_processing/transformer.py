import logging
from io import BytesIO

from PIL import Image, ImageFilter
from rembg import new_session, remove

logger = logging.getLogger(__name__)


class ImageTransformer:
    """Handles image transformations like background removal and resizing."""

    def __init__(self, canvas_size: tuple[int, int] = (800, 800), padding: int = 20, jpeg_quality: int = 95, dilation_filter_size: int = 3):
        self.canvas_size = canvas_size
        self.padding = padding
        self.jpeg_quality = jpeg_quality
        self.dilation_filter_size = dilation_filter_size
        self._rembg_session = None

    @property
    def rembg_session(self):
        if self._rembg_session is None:
            self._rembg_session = new_session()
        return self._rembg_session

    def transform(self, image_bytes: bytes, with_background_removal: bool = False, background_analyzer=None) -> bytes | None:
        """
        Transforms the image: removes background if requested, crops, and centers on a white canvas.
        """
        try:
            with Image.open(BytesIO(image_bytes)) as img:
                # 1. Background Check
                if background_analyzer and background_analyzer.is_dark_background(img):
                    logger.info("Image detected with dark/black background. Ignoring.")
                    return None

                img = img.convert("RGBA")
                icc_profile = img.info.get("icc_profile")

                if with_background_removal:
                    logger.info("Performing color-safe background removal.")
                    processed_bytes = remove(image_bytes, session=self.rembg_session)

                    with Image.open(BytesIO(processed_bytes)) as rembg_img:
                        rembg_img = rembg_img.convert("RGBA")
                        # Perform edge dilation on the alpha mask
                        split_result = rembg_img.split()
                        if len(split_result) == 4:
                            r, g, b, alpha = split_result
                            dilated_alpha = alpha.filter(ImageFilter.MaxFilter(self.dilation_filter_size))
                            img = Image.merge("RGBA", (r, g, b, dilated_alpha))
                        else:
                            img = rembg_img

                    # AUTO-CROP
                    bbox = img.getbbox()
                    if bbox:
                        img = img.crop(bbox)

                # 2. Create standardized White Canvas
                canvas = Image.new("RGB", self.canvas_size, (255, 255, 255))

                # Resize to fit within canvas with padding
                thumbnail_size = (self.canvas_size[0] - 2 * self.padding, self.canvas_size[1] - 2 * self.padding)
                img.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)

                # Center the product
                paste_x = (self.canvas_size[0] - img.width) // 2
                paste_y = (self.canvas_size[1] - img.height) // 2

                # Final Paste
                canvas.paste(img, (paste_x, paste_y), mask=img)

                output_buffer = BytesIO()
                save_kwargs: dict[str, str | int | bytes] = {"format": "JPEG", "quality": self.jpeg_quality, "subsampling": 0}
                if icc_profile:
                    save_kwargs["icc_profile"] = icc_profile

                canvas.save(output_buffer, **save_kwargs)  # type: ignore[arg-type]
                return output_buffer.getvalue()

        except Exception as e:
            logger.error(f"Error transforming image: {e}")
            return None


class HighResImageTransformer(ImageTransformer):
    """Image transformer for high-resolution images (1200x1200)."""

    def __init__(self, **kwargs):
        super().__init__(canvas_size=(1200, 1200), **kwargs)
