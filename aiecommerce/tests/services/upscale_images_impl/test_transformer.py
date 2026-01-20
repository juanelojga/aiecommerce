import io

import pytest
from PIL import Image

from aiecommerce.services.upscale_images_impl.transformer import HighResImageTransformer


@pytest.fixture
def transformer():
    return HighResImageTransformer()


def create_test_image(
    size: tuple[int, int] = (100, 100),
    color: tuple[int, int, int, int] = (255, 0, 0, 255),
    mode: str = "RGBA",
    format: str = "PNG",
) -> bytes:
    img = Image.new(mode, size, color)
    buf = io.BytesIO()
    img.save(buf, format=format)
    return buf.getvalue()


def test_transform_success(transformer):
    # Test with a simple PNG image (100x100)
    image_bytes = create_test_image(size=(100, 100), color=(255, 0, 0, 255))
    # Target size is much larger (1200x1200)
    target_size = (1200, 1200)

    output_bytes = transformer.transform(image_bytes, target_size)

    # Verify the output is a valid JPEG and has the correct size
    with Image.open(io.BytesIO(output_bytes)) as out_img:
        assert out_img.format == "JPEG"
        assert out_img.size == target_size

        # In a 1200x1200 canvas, the 100x100 image should be upscaled
        # to fill the canvas (since 1200/100 = 12, it will be 1200x1200).
        # Wait, if it's 100x100 and target is 1200x1200, it scales to 1200x1200.
        # That's why (0,0) is red!

        # Let's use an image that won't fill the canvas perfectly to test background
        # Or just test that the center is red.
        pixel_center = out_img.getpixel((600, 600))
        assert pixel_center[0] > 250  # Should be red
        assert pixel_center[1] < 10
        assert pixel_center[2] < 10


def test_transform_with_background(transformer):
    # 100x50 image in 100x100 target size -> should have background
    image_bytes = create_test_image(size=(100, 50), color=(255, 0, 0, 255))
    target_size = (100, 100)

    output_bytes = transformer.transform(image_bytes, target_size)

    with Image.open(io.BytesIO(output_bytes)) as out_img:
        assert out_img.size == target_size
        # (0,0) should be background (white)
        pixel_corner = out_img.getpixel((0, 0))
        assert all(c >= 250 for c in pixel_corner)
        # (50, 50) should be red (the image is 100x50 scaled to 100x50 and centered)
        # paste_position = (0, (100-50)//2) = (0, 25)
        # So (50, 50) is inside the red area (y from 25 to 75)
        pixel_center = out_img.getpixel((50, 50))
        assert pixel_center[0] > 250
        assert pixel_center[1] < 10
        assert pixel_center[2] < 10


def test_transform_different_target_size(transformer):
    image_bytes = create_test_image(size=(100, 100))
    target_size = (800, 600)

    output_bytes = transformer.transform(image_bytes, target_size)

    with Image.open(io.BytesIO(output_bytes)) as out_img:
        assert out_img.size == target_size


def test_transform_upscale(transformer):
    # Small image should be upscaled
    image_bytes = create_test_image(size=(50, 50))
    target_size = (500, 500)

    output_bytes = transformer.transform(image_bytes, target_size)

    with Image.open(io.BytesIO(output_bytes)) as out_img:
        assert out_img.size == target_size


def test_transform_downscale(transformer):
    # Large image should be downscaled
    image_bytes = create_test_image(size=(2000, 2000))
    target_size = (1000, 1000)

    output_bytes = transformer.transform(image_bytes, target_size)

    with Image.open(io.BytesIO(output_bytes)) as out_img:
        assert out_img.size == target_size


def test_transform_aspect_ratio_landscape(transformer):
    # Landscape image
    image_bytes = create_test_image(size=(200, 100))
    target_size = (1000, 1000)

    output_bytes = transformer.transform(image_bytes, target_size)

    with Image.open(io.BytesIO(output_bytes)) as out_img:
        assert out_img.size == target_size
        # The original image was 2:1 ratio.
        # In 1000x1000, it should be scaled to 1000x500 and centered.
        # So at (500, 250) we should see the original color (red)
        # Note: JPEG compression might slightly change the color, but it should be close to red
        # Let's check a pixel that definitely should be red.
        pixel = out_img.getpixel((500, 500))
        assert pixel[0] > 200  # Red component should be high
        assert pixel[1] < 50  # Green should be low
        assert pixel[2] < 50  # Blue should be low


def test_transform_aspect_ratio_portrait(transformer):
    # Portrait image
    image_bytes = create_test_image(size=(100, 200))
    target_size = (1000, 1000)

    output_bytes = transformer.transform(image_bytes, target_size)

    with Image.open(io.BytesIO(output_bytes)) as out_img:
        assert out_img.size == target_size


def test_transform_webp_with_alpha(transformer):
    # Test with WebP image which often has transparency
    image_bytes = create_test_image(size=(100, 100), format="WEBP")

    output_bytes = transformer.transform(image_bytes)

    with Image.open(io.BytesIO(output_bytes)) as out_img:
        assert out_img.format == "JPEG"
        assert out_img.size == (1200, 1200)


def test_transform_invalid_bytes(transformer):
    with pytest.raises(Exception):
        transformer.transform(b"not an image")
