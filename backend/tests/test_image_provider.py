import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.services.image_provider import GeneratedImage, ImageProviderError, ImageReference, OpenAICompatibleImageProvider
from app.services.project_service import ProjectService


class FakeResponse:
    def __init__(self, body: bytes, content_type: str = "application/json") -> None:
        self._body = body
        self.headers = {"content-type": content_type}

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def read(self) -> bytes:
        return self._body


def test_shopaikey_keyframe_uploads_and_maps_reference_images(tmp_path) -> None:
    reference_path = tmp_path / "character_reference.png"
    reference_path.write_bytes(b"reference-image")
    requests = []

    def fake_urlopen(request, timeout):
        requests.append(request)
        if request.full_url.endswith("/upload/images"):
            assert b'name="file"; filename="character_reference.png"' in request.data
            return FakeResponse(json.dumps({"url": "https://cdn.example/character.png"}).encode())
        if request.full_url.endswith("/images/google/generations"):
            payload = json.loads(request.data.decode())
            assert payload["model"] == "nano-banana-2"
            assert payload["size"] == "9:16"
            assert payload["imageSize"] == "2K"
            assert payload["image_urls"] == ["https://cdn.example/character.png"]
            assert "portrait/vertical image at 9:16" in payload["prompt"]
            assert "Image 1: @character_reference" in payload["prompt"]
            return FakeResponse(json.dumps({"data": [{"url": "https://cdn.example/keyframe.png"}]}).encode())
        if request.full_url == "https://cdn.example/keyframe.png":
            return FakeResponse(b"generated-keyframe", "image/png")
        raise AssertionError(f"Unexpected URL: {request.full_url}")

    provider = OpenAICompatibleImageProvider(
        provider_name="shopaikey-google",
        api_key="test-key",
        base_url="https://api.shopaikey.com",
        image_output_size="2K",
    )
    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        generated = provider.generate_image(
            prompt="Create one coherent storyboard keyframe.",
            model_id="nano-banana-2",
            reference_images=[
                ImageReference(
                    id="file_1",
                    label="character_reference",
                    role="primary character identity",
                    file_path=str(reference_path),
                    content_type="image/png",
                )
            ],
        )

    assert generated.content == b"generated-keyframe"
    assert generated.content_type == "image/png"
    assert generated.source_url == "https://cdn.example/keyframe.png"
    assert len(requests) == 3


def test_shopaikey_reference_upload_is_cached_for_unchanged_file(tmp_path) -> None:
    reference_path = tmp_path / "location_reference.jpg"
    reference_path.write_bytes(b"location")
    upload_count = 0

    def fake_urlopen(request, timeout):
        nonlocal upload_count
        if request.full_url.endswith("/upload/images"):
            upload_count += 1
            return FakeResponse(json.dumps({"url": "https://cdn.example/location.jpg"}).encode())
        if request.full_url.endswith("/images/google/generations"):
            return FakeResponse(json.dumps({"data": [{"url": "https://cdn.example/output.png"}]}).encode())
        return FakeResponse(b"output", "image/png")

    provider = OpenAICompatibleImageProvider(
        provider_name="shopaikey-google",
        api_key="test-key",
        base_url="https://api.shopaikey.com/v1",
    )
    reference = ImageReference(
        id="file_2",
        label="location_reference",
        role="primary location layout",
        file_path=str(reference_path),
        content_type="image/jpeg",
    )
    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        provider.generate_image(prompt="First keyframe", model_id="nano-banana-2", reference_images=[reference])
        provider.generate_image(prompt="Second keyframe", model_id="nano-banana-2", reference_images=[reference])

    assert upload_count == 1


def test_shopaikey_uses_requested_image_model_per_generation() -> None:
    requested_model = None

    def fake_urlopen(request, timeout):
        nonlocal requested_model
        if request.full_url.endswith("/images/google/generations"):
            payload = json.loads(request.data.decode())
            requested_model = payload["model"]
            assert payload["imageSize"] == "2K"
            return FakeResponse(json.dumps({"data": [{"url": "https://cdn.example/output.png"}]}).encode())
        return FakeResponse(b"output", "image/png")

    provider = OpenAICompatibleImageProvider(
        provider_name="shopaikey-google",
        api_key="test-key",
        base_url="https://api.shopaikey.com",
    )
    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        provider.generate_image(prompt="Create a portrait storyboard image.", model_id="nano-banana-pro")

    assert requested_model == "nano-banana-pro"


def test_shopaikey_rejects_unsupported_image_model() -> None:
    provider = OpenAICompatibleImageProvider(
        provider_name="shopaikey-google",
        api_key="test-key",
        base_url="https://api.shopaikey.com",
    )

    with pytest.raises(ImageProviderError, match="Unsupported ShopAIKey image model"):
        provider.generate_image(prompt="Storyboard", model_id="seedream-5")


def test_shopaikey_gpt_image_uses_openai_endpoint_and_reference_urls(tmp_path) -> None:
    reference_path = tmp_path / "character_reference.png"
    reference_path.write_bytes(b"reference-image")

    def fake_urlopen(request, timeout):
        if request.full_url.endswith("/upload/images"):
            return FakeResponse(json.dumps({"url": "https://cdn.example/character.png"}).encode())
        if request.full_url.endswith("/images/openai/generations"):
            payload = json.loads(request.data.decode())
            assert payload["model"] == "gpt-image-1"
            assert payload["size"] == "1024x1536"
            assert payload["image_urls"] == ["https://cdn.example/character.png"]
            assert "centered 9:16 safe area" in payload["prompt"]
            assert "Image 1: @character_reference" in payload["prompt"]
            return FakeResponse(json.dumps({"data": [{"url": "https://cdn.example/gpt-output.png"}]}).encode())
        if request.full_url == "https://cdn.example/gpt-output.png":
            return FakeResponse(b"generated-gpt-image", "image/png")
        raise AssertionError(f"Unexpected URL: {request.full_url}")

    provider = OpenAICompatibleImageProvider(
        provider_name="shopaikey-google",
        api_key="test-key",
        base_url="https://api.shopaikey.com",
    )
    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        generated = provider.generate_image(
            prompt="Create a portrait keyframe.",
            model_id="gpt-image-1",
            reference_images=[
                ImageReference(
                    id="character_file",
                    label="character_reference",
                    role="primary character identity",
                    file_path=str(reference_path),
                    content_type="image/png",
                )
            ],
        )

    assert generated.content == b"generated-gpt-image"
    assert generated.warning == (
        "gpt-image-1 returned its supported 2:3 portrait canvas. "
        "The prompt reserved a centered 9:16 safe area for the video crop."
    )


def test_non_reference_provider_rejects_image_to_image() -> None:
    provider = OpenAICompatibleImageProvider(
        provider_name="openai-compatible",
        api_key="test-key",
        base_url="https://example.test/v1",
    )

    with pytest.raises(ImageProviderError, match="does not support reference images"):
        provider.generate_image(
            prompt="Keyframe",
            model_id="image-model",
            reference_images=[ImageReference(id="1", label="ref", role="character", url="https://example.test/ref.png")],
        )


def test_shopaikey_rejects_landscape_output_for_portrait_request() -> None:
    provider = OpenAICompatibleImageProvider(
        provider_name="shopaikey-google",
        api_key="test-key",
        base_url="https://api.shopaikey.com",
    )

    with pytest.raises(ImageProviderError, match="2816x1536"):
        provider._validate_aspect_ratio(
            GeneratedImage(content=b"image", width=2816, height=1536),
            "9:16",
        )


def test_image_generation_requires_a_selected_model() -> None:
    provider = OpenAICompatibleImageProvider(
        provider_name="shopaikey-google",
        api_key="test-key",
        base_url="https://api.shopaikey.com",
    )

    with pytest.raises(ImageProviderError, match="Select an image model"):
        provider.resolve_model_id("")


def test_keyframe_reference_mapping_excludes_unrelated_product_uploads() -> None:
    uploads = [
        SimpleNamespace(
            id="character_file",
            file_name="character_reference.png",
            url="/uploads/project/character.png",
            path="C:/tmp/character.png",
            content_type="image/png",
        ),
        SimpleNamespace(
            id="location_file",
            file_name="location_reference.png",
            url="/uploads/project/location.png",
            path="C:/tmp/location.png",
            content_type="image/png",
        ),
        SimpleNamespace(
            id="home_file",
            file_name="product_ref_01_home.png",
            url="/uploads/project/home.png",
            path="C:/tmp/home.png",
            content_type="image/png",
        ),
        SimpleNamespace(
            id="result_file",
            file_name="product_ref_02_result.png",
            url="/uploads/project/result.png",
            path="C:/tmp/result.png",
            content_type="image/png",
        ),
    ]
    project = SimpleNamespace(uploaded_files=uploads)
    plan = SimpleNamespace(
        primaryCharacter={"imageUrl": "/uploads/project/character.png"},
        primaryLocation={"imageUrl": "/uploads/project/location.png"},
        productReferences=[
            {"id": "home_file", "referenceLabel": "product_ref_01_home"},
            {"id": "result_file", "referenceLabel": "product_ref_02_result"},
        ],
    )
    service = object.__new__(ProjectService)

    references = service._build_keyframe_image_references(
        project,
        plan,
        scene={},
        slot={"productReferenceIds": ["result_file", "home_file"]},
    )

    assert [reference.id for reference in references] == ["result_file", "character_file", "location_file"]
    assert "pixel-locked product/app UI" in references[0].role
