from typing import Protocol

from app.config import VIDEO_PROVIDER_API_KEY, VIDEO_PROVIDER_NAME
from app.models.schemas import Project, Variant


class VideoProviderError(Exception):
    pass


class VideoProvider(Protocol):
    def render(self, project: Project, variants: list[Variant]) -> list[Variant]:
        ...


class ExternalVideoProvider:
    def __init__(
        self,
        provider_name: str = VIDEO_PROVIDER_NAME,
        api_key: str = VIDEO_PROVIDER_API_KEY,
    ) -> None:
        self.provider_name = provider_name
        self.api_key = api_key

    def render(self, project: Project, variants: list[Variant]) -> list[Variant]:
        if not self.provider_name or not self.api_key:
            raise VideoProviderError(
                "Video provider is not configured. Set VIDEO_PROVIDER_NAME and VIDEO_PROVIDER_API_KEY."
            )

        raise VideoProviderError("Provider is configured but render adapter is not implemented yet.")
