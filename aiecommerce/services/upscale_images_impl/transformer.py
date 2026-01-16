import io

from PIL import Image


class HighResImageTransformer:
    """
    Transforms an image to a high-resolution format with a white background.
    """

    def transform(self, image_bytes: bytes, target_size: tuple[int, int] = (1200, 1200)) -> bytes:
        """
        Transforms image bytes into a high-resolution JPEG image.

        This method takes raw image bytes, opens them using PIL, and converts
        the image to RGBA to handle transparency (including WebP). It then
        resizes the image to fit within the specified target dimensions while
        maintaining aspect ratio, using high-quality resampling (LANCZOS).

        The resized image is then centered and pasted onto a white RGB canvas.
        Finally, the composite image is saved as a high-quality JPEG (95 quality)
        and returned as bytes.

        Args:
            image_bytes: The raw bytes of the source image.
            target_size: A tuple (width, height) for the output image dimensions.
                         Defaults to (1200, 1200).

        Returns:
            The bytes of the transformed JPEG image.
        """
        with Image.open(io.BytesIO(image_bytes)) as img:
            # Convert to RGBA to handle transparency and different color modes
            img = img.convert("RGBA")

            # Create a thumbnail (in-place) that fits within the target size
            img.thumbnail(target_size, Image.Resampling.LANCZOS)

            # Create a new white background canvas in RGB mode
            background = Image.new("RGB", target_size, (255, 255, 255))

            # Calculate position to center the thumbnail on the canvas
            paste_position = (
                (target_size[0] - img.width) // 2,
                (target_size[1] - img.height) // 2,
            )

            # Paste the thumbnail onto the background, using its alpha channel as a mask
            background.paste(img, paste_position, img)

            # Save the final image to a byte buffer as a high-quality JPEG
            output_buffer = io.BytesIO()
            background.save(output_buffer, format="JPEG", quality=95)
            return output_buffer.getvalue()
