from typing import Annotated

from fastapi import APIRouter, File, Query, UploadFile, status

from app.models.schemas import (
    CreativePlan,
    GenerateImageRequest,
    GenerateSceneVideoRequest,
    ImageGenerationJob,
    Project,
    ReviewSceneTakeRequest,
    RewriteSceneRequest,
    SelectKeyframeCandidateRequest,
    UpdateKeyframePromptSlotRequest,
    UpdateProductReferenceRequest,
    UpdateReferenceAssetRequest,
    UpdateSceneRequest,
    UpdateSceneVideoPromptRequest,
)
from app.routes.projects import project_service
from app.services.image_generation_queue import ImageGenerationQueue


router = APIRouter(prefix="/api/projects", tags=["generation"])
image_generation_queue = ImageGenerationQueue(project_service)


@router.post("/{project_id}/plan-creation", response_model=CreativePlan)
def generate_plan_creation(project_id: str) -> CreativePlan:
    return project_service.generate_plan_creation(project_id)


@router.patch("/{project_id}/product-references/{reference_id}", response_model=Project)
def update_product_reference(
    project_id: str,
    reference_id: str,
    payload: UpdateProductReferenceRequest,
) -> Project:
    return project_service.update_product_reference(project_id, reference_id, payload)


@router.patch("/{project_id}/scenes/{scene_index}", response_model=Project)
def update_scene(
    project_id: str,
    scene_index: int,
    payload: UpdateSceneRequest,
) -> Project:
    return project_service.update_scene(project_id, scene_index, payload)


@router.post("/{project_id}/scenes/{scene_index}/rewrite", response_model=Project)
def rewrite_scene(
    project_id: str,
    scene_index: int,
    payload: RewriteSceneRequest,
) -> Project:
    return project_service.rewrite_scene(project_id, scene_index, payload)


@router.patch("/{project_id}/scenes/{scene_index}/video-prompt", response_model=Project)
def update_scene_video_prompt(
    project_id: str,
    scene_index: int,
    payload: UpdateSceneVideoPromptRequest,
) -> Project:
    return project_service.update_scene_video_prompt(project_id, scene_index, payload)


@router.post("/{project_id}/scenes/{scene_index}/video-prompt/regenerate", response_model=Project)
def regenerate_scene_video_prompt(project_id: str, scene_index: int) -> Project:
    return project_service.regenerate_scene_video_prompt(project_id, scene_index)


@router.patch("/{project_id}/scenes/{scene_index}/keyframe-slots/{slot_id}", response_model=Project)
def update_keyframe_prompt_slot(
    project_id: str,
    scene_index: int,
    slot_id: str,
    payload: UpdateKeyframePromptSlotRequest,
) -> Project:
    return project_service.update_keyframe_prompt_slot(project_id, scene_index, slot_id, payload)


@router.post("/{project_id}/scenes/{scene_index}/keyframe-slots/{slot_id}/select", response_model=Project)
def select_keyframe_candidate(
    project_id: str,
    scene_index: int,
    slot_id: str,
    payload: SelectKeyframeCandidateRequest,
) -> Project:
    return project_service.select_keyframe_candidate(project_id, scene_index, slot_id, payload)


@router.post("/{project_id}/reference-assets/{asset_type}/generate", response_model=Project)
def generate_reference_asset_image(
    project_id: str,
    asset_type: str,
    payload: GenerateImageRequest,
) -> Project:
    return project_service.generate_reference_asset_image(project_id, asset_type, model_id=payload.model)


@router.post(
    "/{project_id}/reference-assets/{asset_type}/generate-async",
    response_model=ImageGenerationJob,
    status_code=status.HTTP_202_ACCEPTED,
)
def enqueue_reference_asset_image(
    project_id: str,
    asset_type: str,
    payload: GenerateImageRequest,
) -> ImageGenerationJob:
    return image_generation_queue.submit_reference_asset(project_id, asset_type, payload.model)


@router.patch("/{project_id}/reference-assets/{asset_type}", response_model=Project)
def update_reference_asset(
    project_id: str,
    asset_type: str,
    payload: UpdateReferenceAssetRequest,
) -> Project:
    return project_service.update_reference_asset(project_id, asset_type, payload)


@router.post("/{project_id}/reference-assets/{asset_type}/upload", response_model=Project)
async def upload_reference_asset_image(
    project_id: str,
    asset_type: str,
    file: Annotated[UploadFile, File()],
) -> Project:
    return await project_service.upload_reference_asset_image(project_id, asset_type, file)


@router.post("/{project_id}/scenes/{scene_index}/keyframe-slots/{slot_id}/generate", response_model=Project)
def generate_keyframe_slot_image(
    project_id: str,
    scene_index: int,
    slot_id: str,
    payload: GenerateImageRequest,
) -> Project:
    return project_service.generate_keyframe_slot_image(
        project_id,
        scene_index,
        slot_id,
        model_id=payload.model,
    )


@router.post(
    "/{project_id}/scenes/{scene_index}/keyframe-slots/{slot_id}/generate-async",
    response_model=ImageGenerationJob,
    status_code=status.HTTP_202_ACCEPTED,
)
def enqueue_keyframe_slot_image(
    project_id: str,
    scene_index: int,
    slot_id: str,
    payload: GenerateImageRequest,
) -> ImageGenerationJob:
    return image_generation_queue.submit_keyframe(
        project_id,
        scene_index,
        slot_id,
        payload.model,
    )


@router.get("/{project_id}/image-generation-jobs", response_model=list[ImageGenerationJob])
def list_image_generation_jobs(
    project_id: str,
    active_only: bool = Query(default=False),
) -> list[ImageGenerationJob]:
    return image_generation_queue.list_for_project(project_id, active_only=active_only)


@router.get("/{project_id}/image-generation-jobs/{job_id}", response_model=ImageGenerationJob)
def get_image_generation_job(project_id: str, job_id: str) -> ImageGenerationJob:
    return image_generation_queue.get(project_id, job_id)


@router.post("/{project_id}/scenes/{scene_index}/keyframe-slots/{slot_id}/upload", response_model=Project)
async def upload_keyframe_slot_image(
    project_id: str,
    scene_index: int,
    slot_id: str,
    file: Annotated[UploadFile, File()],
) -> Project:
    return await project_service.upload_keyframe_slot_image(project_id, scene_index, slot_id, file)


@router.post("/{project_id}/scenes/{scene_index}/video", response_model=Project)
def generate_scene_video(
    project_id: str,
    scene_index: int,
    payload: GenerateSceneVideoRequest | None = None,
) -> Project:
    return project_service.generate_scene_video(project_id, scene_index, payload.model if payload else None)


@router.get("/{project_id}/scenes/{scene_index}/video-status", response_model=Project)
def poll_scene_video(project_id: str, scene_index: int) -> Project:
    return project_service.poll_scene_video(project_id, scene_index)


@router.post("/{project_id}/scenes/{scene_index}/video/upload", response_model=Project)
async def upload_scene_video(
    project_id: str,
    scene_index: int,
    file: Annotated[UploadFile, File()],
) -> Project:
    return await project_service.upload_scene_video(project_id, scene_index, file)


@router.post("/{project_id}/scenes/{scene_index}/take-review", response_model=Project)
def review_scene_take(
    project_id: str,
    scene_index: int,
    payload: ReviewSceneTakeRequest,
) -> Project:
    return project_service.review_scene_take(project_id, scene_index, payload)
