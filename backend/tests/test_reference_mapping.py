from app.models.schemas import CreativePlan


def test_explicit_product_reference_filename_is_mapped_to_keyframe() -> None:
    plan = CreativePlan(
        productReferences=[
            {
                "id": "file_home",
                "name": "product_ref_01_home.png",
                "sourceFileName": "product_ref_01_home.png",
                "referenceLabel": "product_ref_01_home",
            },
            {
                "id": "file_scan",
                "name": "product_ref_02_scan.png",
                "sourceFileName": "product_ref_02_scan.png",
                "referenceLabel": "product_ref_02_scan",
            },
        ],
        scenes=[
            {
                "sceneIndex": 1,
                "title": "Open the app",
                "productMoment": "Show @product_ref_01_home.png clearly.",
                "keyframePrompts": [
                    {
                        "id": "kf_main",
                        "prompt": "The phone displays @product_ref_01_home.png.",
                        "productReferenceIds": [],
                    }
                ],
            }
        ],
    )

    assert plan.scenes[0]["keyframePrompts"][0]["productReferenceIds"] == ["file_home"]


def test_explicit_home_reference_wins_over_stale_result_id_and_scene_wording() -> None:
    plan = CreativePlan(
        productReferences=[
            {"id": "file_home", "name": "product_ref_01_home.png", "referenceLabel": "product_ref_01_home"},
            {"id": "file_result", "name": "product_ref_02_result.jpg", "referenceLabel": "product_ref_02_result"},
        ],
        scenes=[
            {
                "sceneIndex": 2,
                "title": "Open app before checking the result",
                "productMoment": "The result will be shown in a later scene.",
                "keyframePrompts": [
                    {
                        "id": "kf_main",
                        "prompt": "Show the exact home screen from @product_ref_01_home.png.",
                        "productReferenceIds": ["file_result"],
                    }
                ],
            }
        ],
    )

    assert plan.scenes[0]["keyframePrompts"][0]["productReferenceIds"] == ["file_home"]


def test_scene_semantics_replace_wrong_product_reference_with_scan_reference() -> None:
    plan = CreativePlan(
        productReferences=[
            {"id": "file_home", "name": "app_home.png", "referenceLabel": "app_home"},
            {"id": "file_scan", "name": "app_scan.png", "referenceLabel": "app_scan"},
        ],
        scenes=[
            {
                "sceneIndex": 1,
                "title": "Scanning in progress",
                "productMoment": "The scanning interface is clearly visible.",
                "keyframePrompts": [
                    {
                        "id": "kf_main",
                        "prompt": "Show the app scanning interface on the phone.",
                        "productReferenceIds": ["file_home"],
                    }
                ],
            }
        ],
    )

    assert plan.scenes[0]["keyframePrompts"][0]["productReferenceIds"] == ["file_scan"]


def test_compiled_frontend_keyframe_prompt_is_reduced_to_source_once() -> None:
    compiled_prompt = """Reference images to attach / mention in Flow:
- @character_reference.png: use for the same actor identity and outfit.
- @location_reference.png: use for the same location.
- @product_ref_result.png: use for the result screen.

Reference images to attach / mention in Flow:
- @character_reference.png: use for the same actor identity and outfit.
- @location_reference.png: use for the same location.
- @product_ref_home.png: use for the home screen.

A close-up of the phone showing a scanning animation.

Action: The phone scans the coin.

Product moment: The scanning interface is visible.

Camera: stable close-up

Preservation rule: preserve the uploaded UI."""
    plan = CreativePlan(
        productReferences=[
            {"id": "file_home", "name": "product_ref_home.png", "referenceLabel": "product_ref_home"},
            {"id": "file_scan", "name": "product_ref_scan.png", "referenceLabel": "product_ref_scan"},
            {"id": "file_result", "name": "product_ref_result.png", "referenceLabel": "product_ref_result"},
        ],
        scenes=[
            {
                "sceneIndex": 4,
                "title": "Scanning in progress",
                "productMoment": "The scanning interface is visible.",
                "keyframePrompts": [
                    {
                        "id": "kf_main",
                        "prompt": compiled_prompt,
                        "productReferenceIds": ["file_result"],
                    }
                ],
            }
        ],
    )

    slot = plan.scenes[0]["keyframePrompts"][0]
    assert slot["prompt"] == "A close-up of the phone showing a scanning animation."
    assert slot["productReferenceIds"] == ["file_scan"]
