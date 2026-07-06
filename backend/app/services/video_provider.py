from dataclasses import asdict, dataclass, field
from typing import Any, Protocol

from app.config import VIDEO_PROVIDER_API_KEY, VIDEO_PROVIDER_NAME
from app.models.schemas import PipelineAsset, PipelineStep


class VideoProviderError(Exception):
    pass


class ImageGenerationProvider(Protocol):
    def generate_image(self, step: PipelineStep, input_assets: list[PipelineAsset]) -> PipelineAsset:
        ...


class VideoGenerationProvider(Protocol):
    def generate_video(self, step: PipelineStep, input_assets: list[PipelineAsset]) -> PipelineAsset:
        ...


class OverlayProvider(Protocol):
    def apply_overlay(self, step: PipelineStep, input_assets: list[PipelineAsset]) -> PipelineAsset:
        ...


class AssemblyProvider(Protocol):
    def assemble(self, step: PipelineStep, input_assets: list[PipelineAsset]) -> PipelineAsset:
        ...


class ExportProvider(Protocol):
    def export(self, step: PipelineStep, input_assets: list[PipelineAsset]) -> PipelineAsset:
        ...


@dataclass
class ProviderContract:
    tool_type: str
    capability: str
    provider_name: str
    configured: bool
    adapter_status: str
    manual_supported: bool
    required_env: list[str] = field(default_factory=list)
    recommended_manual_tools: list[str] = field(default_factory=list)
    notes: str = ""

    @property
    def status(self) -> str:
        if not self.configured:
            return "missing_env"
        return self.adapter_status

    def model_dump(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status
        return data


class ConfiguredProviderAdapter:
    def __init__(self, tool_type: str, provider_name: str) -> None:
        self.tool_type = tool_type
        self.provider_name = provider_name

    def generate_image(self, step: PipelineStep, input_assets: list[PipelineAsset]) -> PipelineAsset:
        raise VideoProviderError(f"Provider '{self.provider_name}' is configured but image_generation adapter is not implemented yet.")

    def generate_video(self, step: PipelineStep, input_assets: list[PipelineAsset]) -> PipelineAsset:
        raise VideoProviderError(f"Provider '{self.provider_name}' is configured but video_generation adapter is not implemented yet.")

    def apply_overlay(self, step: PipelineStep, input_assets: list[PipelineAsset]) -> PipelineAsset:
        raise VideoProviderError(f"Provider '{self.provider_name}' is configured but overlay adapter is not implemented yet.")

    def assemble(self, step: PipelineStep, input_assets: list[PipelineAsset]) -> PipelineAsset:
        raise VideoProviderError(f"Provider '{self.provider_name}' is configured but assembly adapter is not implemented yet.")

    def export(self, step: PipelineStep, input_assets: list[PipelineAsset]) -> PipelineAsset:
        raise VideoProviderError(f"Provider '{self.provider_name}' is configured but export adapter is not implemented yet.")


class ProviderRegistry:
    def __init__(
        self,
        provider_name: str = VIDEO_PROVIDER_NAME,
        api_key: str = VIDEO_PROVIDER_API_KEY,
        requirements: list[dict[str, Any]] | None = None,
    ) -> None:
        self.provider_name = provider_name
        self.api_key = api_key
        self.requirements = requirements or []

    def get_provider(self, tool_type: str):
        if not self.provider_name or not self.api_key:
            return None
        return ConfiguredProviderAdapter(tool_type=tool_type, provider_name=self.provider_name)

    def contract_for(self, tool_type: str, requirement: dict[str, Any] | None = None) -> dict[str, Any]:
        requirement = requirement or self._requirement_for(tool_type)
        provider_name = self.provider_name or "manual_web_tool"
        contract = ProviderContract(
            tool_type=tool_type,
            capability=str(requirement.get("capability") or tool_type),
            provider_name=provider_name,
            configured=bool(self.provider_name and self.api_key),
            adapter_status="configured_no_adapter",
            manual_supported=bool(requirement.get("manual_supported", True)),
            required_env=list(requirement.get("required_env") or ["VIDEO_PROVIDER_NAME", "VIDEO_PROVIDER_API_KEY"]),
            recommended_manual_tools=list(requirement.get("recommended_manual_tools") or []),
            notes=str(requirement.get("notes") or ""),
        )
        return contract.model_dump()

    def contracts(self, requirements: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        items = requirements if requirements is not None else self.requirements
        if not items:
            return [self.contract_for(tool_type) for tool_type in ("image_generation", "video_generation", "video_editing", "final_assembly", "export")]
        return [self.contract_for(str(item.get("tool_type")), item) for item in items if item.get("tool_type")]

    def _requirement_for(self, tool_type: str) -> dict[str, Any]:
        for item in self.requirements:
            if item.get("tool_type") == tool_type:
                return item
        return {
            "tool_type": tool_type,
            "capability": tool_type,
            "required_env": ["VIDEO_PROVIDER_NAME", "VIDEO_PROVIDER_API_KEY"],
            "manual_supported": True,
            "recommended_manual_tools": [],
            "notes": "",
        }
