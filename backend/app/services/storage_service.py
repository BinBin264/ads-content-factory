import json
import shutil
from pathlib import Path
from typing import Any

from fastapi import UploadFile

from app.config import PROJECTS_JSON, UPLOADS_DIR, ensure_app_dirs
from app.models.schemas import Project, UploadedFileInfo, utc_now


class ProjectNotFoundError(Exception):
    pass


def _sanitize_filename(filename: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {".", "-", "_"} else "_" for ch in filename)
    return safe.strip("._") or "upload"


def _slug_stem(filename: str) -> str:
    stem = Path(filename).stem or "product"
    slug = "".join(ch.lower() if ch.isalnum() else "_" for ch in stem)
    slug = "_".join(part for part in slug.split("_") if part)
    return slug or "product"


def _safe_extension(upload: UploadFile) -> str:
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        return suffix
    if upload.content_type == "image/png":
        return ".png"
    if upload.content_type == "image/webp":
        return ".webp"
    return ".jpeg"


class JsonProjectStorage:
    def __init__(self, json_path: Path = PROJECTS_JSON) -> None:
        self.json_path = json_path
        ensure_app_dirs()

    def list_projects(self) -> list[Project]:
        raw = self._read_raw()
        return [Project.model_validate(item) for item in raw]

    def get_project(self, project_id: str) -> Project:
        for project in self.list_projects():
            if project.id == project_id:
                return project
        raise ProjectNotFoundError(f"Project '{project_id}' was not found")

    def save_project(self, project: Project) -> Project:
        projects = self.list_projects()
        project.updated_at = utc_now()
        replaced = False
        for index, existing in enumerate(projects):
            if existing.id == project.id:
                projects[index] = project
                replaced = True
                break
        if not replaced:
            projects.append(project)
        self._write_raw([item.model_dump(mode="json") for item in projects])
        return project

    def delete_project(self, project_id: str) -> None:
        projects = self.list_projects()
        remaining = [project for project in projects if project.id != project_id]
        if len(remaining) == len(projects):
            raise ProjectNotFoundError(f"Project '{project_id}' was not found")
        self._write_raw([item.model_dump(mode="json") for item in remaining])

        target = (UPLOADS_DIR / project_id).resolve()
        if target.exists() and UPLOADS_DIR.resolve() in target.parents:
            shutil.rmtree(target)

    def _read_raw(self) -> list[dict[str, Any]]:
        if not self.json_path.exists():
            return []
        content = self.json_path.read_text(encoding="utf-8-sig").strip()
        if not content:
            return []
        data = json.loads(content)
        if not isinstance(data, list):
            raise ValueError("projects.json must contain a JSON array")
        return data

    def _write_raw(self, data: list[dict[str, Any]]) -> None:
        self.json_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.json_path.with_suffix(".json.tmp")
        temp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_path.replace(self.json_path)


class LocalFileStorage:
    def __init__(self, uploads_dir: Path = UPLOADS_DIR) -> None:
        self.uploads_dir = uploads_dir
        ensure_app_dirs()

    async def save_uploads(self, project_id: str, files: list[UploadFile] | None) -> list[UploadedFileInfo]:
        if not files:
            return []

        project_dir = self.uploads_dir / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        saved: list[UploadedFileInfo] = []

        existing_count = len([item for item in project_dir.iterdir() if item.is_file()]) if project_dir.exists() else 0
        for index, upload in enumerate(files, start=existing_count + 1):
            original_name = upload.filename or f"upload_{index}"
            filename = f"{index:02d}_{_sanitize_filename(original_name)}"
            destination = project_dir / filename
            content = await upload.read()
            destination.write_bytes(content)
            saved.append(
                UploadedFileInfo(
                    file_name=original_name,
                    content_type=upload.content_type,
                    size_bytes=len(content),
                    path=str(destination),
                    url=f"/uploads/{project_id}/{filename}",
                )
            )
            await upload.close()

        return saved

    async def save_product_uploads(
        self,
        project_id: str,
        files: list[UploadFile] | None,
        *,
        start_index: int = 1,
    ) -> list[UploadedFileInfo]:
        if not files:
            return []

        project_dir = self.uploads_dir / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        saved: list[UploadedFileInfo] = []

        existing_count = len([item for item in project_dir.iterdir() if item.is_file()]) if project_dir.exists() else 0
        for offset, upload in enumerate(files):
            reference_index = start_index + offset
            original_name = upload.filename or f"product_{reference_index}"
            display_name = f"product_ref_{reference_index:02d}_{_slug_stem(original_name)}{_safe_extension(upload)}"
            stored_name = f"{existing_count + offset + 1:02d}_{display_name}"
            destination = project_dir / stored_name
            content = await upload.read()
            destination.write_bytes(content)
            saved.append(
                UploadedFileInfo(
                    file_name=display_name,
                    content_type=upload.content_type,
                    size_bytes=len(content),
                    path=str(destination),
                    url=f"/uploads/{project_id}/{stored_name}",
                )
            )
            await upload.close()

        return saved

    async def save_named_upload(self, project_id: str, upload: UploadFile, filename: str) -> UploadedFileInfo:
        project_dir = self.uploads_dir / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        existing_count = len([item for item in project_dir.iterdir() if item.is_file()]) if project_dir.exists() else 0
        safe_name = _sanitize_filename(filename)
        stored_name = f"{existing_count + 1:02d}_{safe_name}"
        destination = project_dir / stored_name
        content = await upload.read()
        destination.write_bytes(content)
        await upload.close()
        return UploadedFileInfo(
            file_name=safe_name,
            content_type=upload.content_type,
            size_bytes=len(content),
            path=str(destination),
            url=f"/uploads/{project_id}/{stored_name}",
        )

    def save_generated_file(
        self,
        project_id: str,
        *,
        bucket: str,
        filename: str,
        content: bytes,
        content_type: str = "image/png",
    ) -> UploadedFileInfo:
        project_dir = self.uploads_dir / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        existing_count = len([item for item in project_dir.iterdir() if item.is_file()]) if project_dir.exists() else 0
        safe_name = _sanitize_filename(filename)
        stored_name = f"{existing_count + 1:02d}_{_sanitize_filename(bucket)}_{safe_name}"
        destination = project_dir / stored_name
        destination.write_bytes(content)
        return UploadedFileInfo(
            file_name=filename,
            content_type=content_type,
            size_bytes=len(content),
            path=str(destination),
            url=f"/uploads/{project_id}/{stored_name}",
        )

    def delete_uploaded_files(self, files: list[UploadedFileInfo]) -> None:
        uploads_root = self.uploads_dir.resolve()
        for uploaded_file in files:
            target = Path(uploaded_file.path).resolve()
            if target.exists() and uploads_root in target.parents:
                target.unlink()
