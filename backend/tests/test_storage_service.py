from app.services.storage_service import LocalFileStorage


def test_generated_file_uses_highest_existing_prefix_instead_of_file_count(tmp_path) -> None:
    project_dir = tmp_path / "project_test"
    project_dir.mkdir()
    (project_dir / "01_product.png").write_bytes(b"one")
    (project_dir / "03_location.png").write_bytes(b"three")

    storage = LocalFileStorage(tmp_path)
    saved = storage.save_generated_file(
        "project_test",
        bucket="keyframe",
        filename="scene_01.png",
        content=b"four",
    )

    assert saved.url.endswith("/04_keyframe_scene_01.png")
    assert (project_dir / "03_location.png").read_bytes() == b"three"
    assert (project_dir / "04_keyframe_scene_01.png").read_bytes() == b"four"
