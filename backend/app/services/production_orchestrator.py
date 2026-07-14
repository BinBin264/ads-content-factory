from __future__ import annotations

import re
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.models.schemas import CreativePlan, Project


PROMPT_BUDGET_CHARS = 2200
MAX_PRODUCT_REFERENCES_PER_KEYFRAME = 1


class ProductionOrchestrator:
    """Builds provider-neutral sequence contracts and compact Veo prompts."""

    def prepare_plan(self, project: Project, plan: CreativePlan, *, compile_prompts: bool = True) -> CreativePlan:
        scenes = [scene for scene in plan.scenes if isinstance(scene, dict)]
        plan.storySpine = self._story_spine(project, plan, scenes)
        plan.worldBible = self._world_bible(project, plan)
        plan.surfaceProfile = self._surface_profile()
        plan.safetyPlan = self._safety_plan(project, plan)
        plan.qualityStrategy = self._quality_strategy()

        existing_state = dict(plan.sequenceState or {})
        take_history = existing_state.get("takeHistory") if isinstance(existing_state.get("takeHistory"), list) else []
        plan.sequenceState = {
            "schemaVersion": "1.0",
            "stateRevision": int(existing_state.get("stateRevision") or 1),
            "canonRevision": int(existing_state.get("canonRevision") or 1),
            "providerProfile": "google_veo",
            "currentSceneIndex": int(existing_state.get("currentSceneIndex") or 1),
            "takeHistory": take_history,
            "updatedAt": existing_state.get("updatedAt") or self._now(),
        }

        accepted_handoff: dict[str, Any] | None = None
        for index, scene in enumerate(scenes):
            self._prepare_scene(plan, scene, index, scenes, accepted_handoff, compile_prompts=compile_prompts)
            review = scene.get("takeReview") if isinstance(scene.get("takeReview"), dict) else None
            if review and review.get("canonAccepted"):
                accepted_handoff = self._dict(review.get("observedEndState")) or self._dict(scene.get("shotContract", {}).get("plannedEndState"))
            else:
                accepted_handoff = None

        plan.scenes = scenes
        self._refresh_current_scene(plan)
        return plan

    def refresh_scene(self, plan: CreativePlan, scene: dict[str, Any], *, compile_prompt: bool = False) -> None:
        scenes = [item for item in plan.scenes if isinstance(item, dict)]
        try:
            index = scenes.index(scene)
        except ValueError:
            index = max(int(scene.get("sceneIndex") or 1) - 1, 0)
        prior_end_state = None
        if index > 0:
            previous = scenes[index - 1]
            review = previous.get("takeReview") if isinstance(previous.get("takeReview"), dict) else {}
            prior_end_state = self._dict(review.get("observedEndState")) or self._dict(previous.get("shotContract", {}).get("plannedEndState"))
        self._prepare_scene(plan, scene, index, scenes, prior_end_state, compile_prompts=compile_prompt)

    def compile_scene_prompt(self, plan: CreativePlan, scene: dict[str, Any]) -> str:
        contract = self._dict(scene.get("shotContract"))
        camera = self._dict(scene.get("camera"))
        direction = self._dict(scene.get("direction"))
        voice_lines = [item for item in scene.get("voiceLines") or [] if isinstance(item, dict)]
        negative_rules = self._strings(scene.get("negativeRules"))
        continuity_locks = self._strings(contract.get("continuityLocks"))
        reserved = self._strings(contract.get("reservedForLater"))
        endpoint = self._state_text(contract.get("plannedEndState"))
        opening = self._state_text(contract.get("observedHandoff"))

        clauses = [
            "Use the selected keyframe as the visual source of truth; continue from it naturally without a collage, slideshow, or visual reset.",
        ]
        felt_intent = self._text(direction.get("feltIntent"))
        value_shift = self._text(direction.get("valueShift"))
        primary_spend = self._text(contract.get("primarySpend")).replace("_", " ")
        if felt_intent:
            clauses.append(f"Directing intent: {felt_intent}.")
        if value_shift:
            clauses.append(f"Emotional progression: {value_shift}.")
        if primary_spend:
            clauses.append(f"Visual fidelity priority: {primary_spend}.")
        if opening:
            clauses.append(f"Open after the accepted previous state: {opening}.")
        current_action = self._first_text(contract.get("thisClipOnly")) or self._text(scene.get("visualAction"))
        if current_action:
            clauses.append(f"This clip only: {current_action}")
        performance = self._text(scene.get("characterAction"))
        if performance:
            clauses.append(f"Performance: {performance}")

        camera_text = "; ".join(
            item
            for item in [
                self._text(camera.get("shot")) or self._text(camera.get("selected")),
                self._text(camera.get("movement")),
                self._text(camera.get("composition")),
            ]
            if item
        )
        if camera_text:
            clauses.append(f"Camera: {camera_text}.")

        light = self._text(direction.get("lighting"))
        atmosphere = self._text(direction.get("atmosphere"))
        if light or atmosphere:
            clauses.append(f"Light and atmosphere: {'; '.join(item for item in [light, atmosphere] if item)}.")

        dialogue_cues: list[str] = []
        for item in voice_lines:
            line = self._text(item.get("line"))
            if not line:
                continue
            cue = " / ".join(
                value
                for value in [
                    self._text(item.get("timing")),
                    self._text(item.get("speaker")),
                    self._text(item.get("emotion")),
                    self._text(item.get("delivery")),
                ]
                if value
            )
            dialogue_cues.append(f"{cue}: <{line}>" if cue else f"<{line}>")
        if dialogue_cues:
            clauses.append(f"Spoken dialogue, preserve wording and cues exactly: {'; '.join(dialogue_cues)}.")
        ambient_audio = self._text(scene.get("ambientAudio"))
        if ambient_audio:
            clauses.append(f"Native audio: {ambient_audio}.")
        if endpoint:
            clauses.append(f"Stop when: {endpoint}.")
        if continuity_locks:
            clauses.append(f"Preserve: {'; '.join(continuity_locks[:5])}.")
        if reserved:
            clauses.append(f"Do not yet show: {'; '.join(reserved[:3])}.")

        overlay = self._text(scene.get("onScreenText"))
        if overlay:
            clauses.append(f"Reserve overlay text for post-production only: <{overlay}>; do not render it inside the generated footage.")
        else:
            clauses.append("Do not invent new overlay text, captions, logos, or watermarks; preserve any approved product branding already visible in the keyframe.")
        if negative_rules:
            clauses.append(f"Avoid: {'; '.join(negative_rules[:6])}.")

        return self._compress_prompt(" ".join(clauses))

    def lint_scene_prompt(self, scene: dict[str, Any], prompt: str | None = None) -> dict[str, Any]:
        value = self._text(prompt if prompt is not None else scene.get("finalVideoPrompt"))
        hard_failures: list[str] = []
        warnings: list[str] = []

        if not value:
            hard_failures.append("Video prompt is empty.")
        if re.search(r"\bfile_[a-z0-9]+\b", value, flags=re.IGNORECASE):
            hard_failures.append("Prompt contains an internal file id instead of a stable reference name.")
        slots = [item for item in scene.get("keyframePrompts") or [] if isinstance(item, dict)]
        if not slots:
            hard_failures.append("Scene has no main keyframe contract.")
        for slot in slots:
            reference_ids = self._strings(slot.get("productReferenceIds"))
            if len(reference_ids) > MAX_PRODUCT_REFERENCES_PER_KEYFRAME:
                hard_failures.append("A keyframe may use at most one uploaded product reference.")

        if len(value) > PROMPT_BUDGET_CHARS:
            warnings.append(f"Prompt exceeds the {PROMPT_BUDGET_CHARS}-character Veo budget and should be compressed.")
        provider_parameter_text = re.sub(
            r"\b\d+(?:\.\d+)?\s*(?:-|to)\s*\d+(?:\.\d+)?\s*s\b",
            "",
            value,
            flags=re.IGNORECASE,
        )
        if re.search(
            r"\b(?:4|6|8|10)\s*(?:s|sec|second)|\b9:16\b|\bvertical\b",
            provider_parameter_text,
            flags=re.IGNORECASE,
        ):
            warnings.append("Duration or aspect ratio appears in prompt text; keep it in provider parameters.")
        move_terms = re.findall(r"\b(?:push[- ]?in|pull[- ]?back|pan|tilt|dolly|orbit|zoom|tracking|crane)\b", value, flags=re.IGNORECASE)
        if len(set(item.lower() for item in move_terms)) > 1:
            warnings.append("Prompt asks for multiple camera moves; prefer one motivated move per clip.")
        if not self._state_text(self._dict(scene.get("shotContract")).get("plannedEndState")):
            warnings.append("Scene has no explicit endpoint for continuity handoff.")
        if len(self._strings(self._dict(scene.get("shotContract")).get("thisClipOnly"))) != 1:
            warnings.append("Scene should own exactly one visible beat.")

        score = max(0, 100 - len(hard_failures) * 35 - len(warnings) * 8)
        return {
            "status": "blocked" if hard_failures else "ready" if not warnings else "warning",
            "score": score,
            "hardFailures": hard_failures,
            "warnings": warnings,
            "promptLength": len(value),
            "promptBudget": PROMPT_BUDGET_CHARS,
        }

    def review_take(self, plan: CreativePlan, scene: dict[str, Any], payload: dict[str, Any]) -> None:
        self.prepare_plan_for_review(plan)
        verdict = self._text(payload.get("verdict")).lower()
        accepted = verdict in {"keep", "fix_in_post"}
        take_id = f"take_{uuid4().hex[:10]}"
        review = {
            "takeId": take_id,
            "verdict": verdict,
            "canonAccepted": accepted,
            "observedStartState": self._dict(payload.get("observed_start_state")),
            "observedEndState": self._dict(payload.get("observed_end_state")),
            "completedBeats": self._strings(payload.get("completed_beats")),
            "continuityBreaks": self._strings(payload.get("continuity_breaks")),
            "acceptedDeviations": self._strings(payload.get("accepted_deviations")) if accepted else [],
            "changedVariable": self._text(payload.get("changed_variable")),
            "evidence": self._text(payload.get("evidence")),
            "observationConfidence": self._text(payload.get("observation_confidence")) or "medium",
            "notes": self._text(payload.get("notes")),
            "reviewedAt": self._now(),
            "nextAction": self._next_action(verdict),
        }
        scene["takeReview"] = review
        scene["status"] = "ACCEPTED" if accepted else "RETAKE_REQUIRED"

        state = dict(plan.sequenceState or {})
        history = state.get("takeHistory") if isinstance(state.get("takeHistory"), list) else []
        history.append({"sceneIndex": scene.get("sceneIndex"), **deepcopy(review)})
        state["takeHistory"] = history[-50:]
        state["stateRevision"] = int(state.get("stateRevision") or 1) + 1
        if accepted:
            state["canonRevision"] = int(state.get("canonRevision") or 1) + 1
        state["updatedAt"] = self._now()
        plan.sequenceState = state

        if accepted:
            self._handoff_to_next_scene(plan, scene, review)
        self._refresh_current_scene(plan)

    def prepare_plan_for_review(self, plan: CreativePlan) -> None:
        if not isinstance(plan.sequenceState, dict):
            plan.sequenceState = {}

    def _prepare_scene(
        self,
        plan: CreativePlan,
        scene: dict[str, Any],
        index: int,
        scenes: list[dict[str, Any]],
        prior_end_state: dict[str, Any] | None,
        *,
        compile_prompts: bool,
    ) -> None:
        scene_index = int(scene.get("sceneIndex") or index + 1)
        scene["sceneIndex"] = scene_index
        scene.setdefault("sceneId", f"scene_{scene_index:02d}")
        scene.setdefault("clipId", f"clip_{scene_index:02d}")
        scene.setdefault("arcPosition", self._arc_position(index, len(scenes)))
        scene.setdefault("dramaticFunction", self._text(scene.get("narrativePurpose")) or self._text(scene.get("sceneGoal")))

        direction = self._dict(scene.get("direction"))
        direction.setdefault("valueShift", self._value_shift(scene, index))
        direction.setdefault("feltIntent", self._text(scene.get("feltIntent")) or self._text(scene.get("sceneGoal")))
        direction.setdefault("lighting", self._default_lighting(plan, scene, index))
        direction.setdefault("atmosphere", self._default_atmosphere(scene))
        direction.setdefault("performanceSubtext", self._text(scene.get("characterAction")))
        scene["direction"] = direction

        previous_contract = self._dict(scene.get("shotContract"))
        planned_predecessor = prior_end_state
        if planned_predecessor is None and index > 0:
            planned_predecessor = self._dict(scenes[index - 1].get("shotContract", {}).get("plannedEndState"))
        planned_start = self._dict(previous_contract.get("plannedStartState")) or self._planned_start_state(plan, scene, planned_predecessor)
        planned_end = self._dict(previous_contract.get("plannedEndState")) or self._planned_end_state(scene)
        bindings = self._reference_bindings(plan, scene)
        scene["shotContract"] = {
            "generationMode": "intentional_next_shot",
            "shotStructure": "compact_single_take",
            "primarySpend": self._primary_spend(scene),
            "secondarySpend": "identity_fidelity",
            "economize": self._economize(scene),
            "alreadyHappened": [self._text(item.get("title")) for item in scenes[:index] if self._text(item.get("title"))],
            "thisClipOnly": [self._text(scene.get("visualAction")) or self._text(scene.get("sceneGoal"))],
            "reservedForLater": [self._text(item.get("title")) for item in scenes[index + 1 :] if self._text(item.get("title"))],
            "plannedStartState": planned_start,
            "plannedEndState": planned_end,
            "observedHandoff": self._dict(previous_contract.get("observedHandoff")) or prior_end_state,
            "continuityLocks": self._continuity_locks(plan, scene),
            "allowedChanges": ["actor pose", "facial expression", "camera framing", "action phase"],
            "referenceBindings": bindings,
            "transitionIn": "canonical re-anchor" if index == 0 else "intentional editorial cut from accepted prior state",
            "transitionOut": "clean endpoint for the next planned scene",
            "extensionDepth": 0,
        }

        slot = next((item for item in scene.get("keyframePrompts") or [] if isinstance(item, dict)), None)
        if slot is not None:
            slot["referenceBindings"] = [item for item in bindings if item.get("stage") == "keyframe"]
            slot["qualityGate"] = {
                "status": "ready_for_manual_review" if slot.get("selectedImageUrl") else "awaiting_image",
                "checks": [
                    "identity and wardrobe match canonical character reference",
                    "location geometry and light direction match canonical location reference",
                    "hands, face, and product geometry are not deformed",
                    "only the routed product reference is visible",
                    "no invented UI, logo, label, or readable text",
                ],
                "repairRule": "Change one variable or one prompt clause per retry; do not replace every reference at once.",
            }

        if compile_prompts:
            source_prompt = self._text(scene.get("sourceVideoPrompt")) or self._text(scene.get("finalVideoPrompt"))
            if source_prompt:
                scene["sourceVideoPrompt"] = source_prompt
            scene["finalVideoPrompt"] = self.compile_scene_prompt(plan, scene)
            scene["finalVideoPromptStale"] = False
        scene["promptQuality"] = self.lint_scene_prompt(scene)

    def _story_spine(self, project: Project, plan: CreativePlan, scenes: list[dict[str, Any]]) -> dict[str, Any]:
        existing = dict(plan.storySpine or {})
        first = scenes[0] if scenes else {}
        last = scenes[-1] if scenes else {}
        return {
            "logline": existing.get("logline") or project.brief or project.product_description or project.product_name,
            "storyPromise": existing.get("storyPromise") or self._text(first.get("sceneGoal")) or plan.product_truth,
            "objective": existing.get("objective") or ("deliver a clear product proof and response" if project.workflow_type == "video_ads" else "complete the requested story beat"),
            "initialCondition": existing.get("initialCondition") or self._text(first.get("visualAction")),
            "finalOutcome": existing.get("finalOutcome") or self._text(last.get("visualAction")) or self._text(last.get("sceneGoal")),
            "tone": existing.get("tone") or project.tone,
        }

    def _world_bible(self, project: Project, plan: CreativePlan) -> dict[str, Any]:
        existing = dict(plan.worldBible or {})
        return {
            "characterLock": existing.get("characterLock") or self._text(plan.primaryCharacter.get("consistencyPrompt")),
            "locationLock": existing.get("locationLock") or self._text(plan.primaryLocation.get("consistencyPrompt")),
            "productLock": existing.get("productLock") or self._text(plan.productAnalysis.get("productLockPrompt")),
            "visualGrammar": existing.get("visualGrammar") or f"{project.tone}; one motivated camera move per clip; readable hero subject",
            "lightingContinuity": existing.get("lightingContinuity") or "Keep motivated light direction and color relationship stable inside the same location.",
            "atmosphereContinuity": existing.get("atmosphereContinuity") or "Keep ambience and recurring environmental cues consistent; unify music in post.",
            "antiDriftRules": existing.get("antiDriftRules") or [
                "Re-anchor every scene from canonical character, location, and product references.",
                "Use generated output only as an observed handoff, never as the sole identity source.",
                "Do not silently change face, wardrobe, product geometry, location layout, or exact reference names.",
            ],
        }

    def _surface_profile(self) -> dict[str, Any]:
        return {
            "providerFamily": "google_veo",
            "generationUnit": "one_scene_one_clip",
            "imageInputPolicy": "one selected keyframe as the visual anchor",
            "maxProductReferencesPerKeyframe": MAX_PRODUCT_REFERENCES_PER_KEYFRAME,
            "durationOptionsSec": [4, 6, 8, 10],
            "aspectRatio": "9:16",
            "overlayPolicy": "render subtitles, CTA, and precise text in post-production",
            "continuityPolicy": "canonical re-anchor per scene; accepted take state informs the next shot",
            "limitations": [
                "Face and object consistency can be improved but cannot be guaranteed permanently by orchestration alone.",
                "Exact UI and small readable text should come from a locked keyframe or post-production, not free generation.",
                "Separate generated clips need final music, subtitle, and transition assembly in an editor.",
            ],
        }

    def _safety_plan(self, project: Project, plan: CreativePlan) -> dict[str, Any]:
        existing = dict(plan.safetyPlan or {})
        claims = list(dict.fromkeys([*project.claims_to_avoid, *self._strings(plan.productAnalysis.get("doNotAssume"))]))
        return {
            "claimsToAvoid": existing.get("claimsToAvoid") or claims,
            "referencePolicy": existing.get("referencePolicy") or "Use only user-provided or authorized identity, voice, brand, and product references.",
            "rewriteRules": existing.get("rewriteRules") or [
                "Replace unlicensed celebrity or protected character imitation with an original generic character.",
                "Do not clone a private person's face or voice without authorization.",
                "Move precise legal copy, prices, disclaimers, and logos to approved keyframes or post-production.",
            ],
            "reviewRequired": bool(claims),
        }

    def _quality_strategy(self) -> dict[str, Any]:
        return {
            "takeVerdicts": ["keep", "fix_in_post", "edit", "reroll", "rewrite", "reject"],
            "oneVariableRule": "Change one prompt clause, seed, mode, or reference per retake.",
            "defaultAttemptBudget": 5,
            "rewriteThreshold": "Rewrite after the same flaw appears in two takes.",
            "acceptanceRule": "Only accepted observed footage updates canon; rejected footage never becomes a continuation source.",
        }

    def _reference_bindings(self, plan: CreativePlan, scene: dict[str, Any]) -> list[dict[str, Any]]:
        bindings = [
            {
                "stage": "keyframe",
                "tag": "@character_reference.png",
                "role": "identity_and_wardrobe",
                "transfer": "actor identity, face, body type, hair, and outfit only",
                "ignore": "pose, camera, location, product, logo, and background from this reference",
            },
            {
                "stage": "keyframe",
                "tag": "@location_reference.png",
                "role": "environment",
                "transfer": "location geometry, recurring props, and motivated light direction only",
                "ignore": "people, identity, product, logos, and camera motion from this reference",
            },
        ]
        slot = next((item for item in scene.get("keyframePrompts") or [] if isinstance(item, dict)), {})
        reference_ids = self._strings(slot.get("productReferenceIds"))[:MAX_PRODUCT_REFERENCES_PER_KEYFRAME]
        reference_by_id = {self._text(item.get("id")): item for item in plan.productReferences if isinstance(item, dict)}
        for reference_id in reference_ids:
            reference = reference_by_id.get(reference_id)
            if not reference:
                continue
            tag = self._reference_tag(reference)
            bindings.append(
                {
                    "stage": "keyframe",
                    "tag": tag,
                    "role": "product_or_ui_identity",
                    "transfer": self._text(reference.get("lockPrompt")) or "exact visible product or UI appearance only",
                    "ignore": "actor identity, location, camera, motion, and unrelated screen states from this reference",
                }
            )
        bindings.append(
            {
                "stage": "video",
                "tag": f"@scene_{int(scene.get('sceneIndex') or 1):02d}_keyframe_01.png",
                "role": "first_frame_and_visual_anchor",
                "transfer": "accepted actor, location, product state, framing, light, and composition",
                "ignore": "none; this is the current scene source of truth",
            }
        )
        return bindings

    def _continuity_locks(self, plan: CreativePlan, scene: dict[str, Any]) -> list[str]:
        locks = [
            self._text(plan.primaryCharacter.get("consistencyPrompt")),
            self._text(plan.primaryLocation.get("consistencyPrompt")),
            self._text(plan.productAnalysis.get("productLockPrompt")),
            "preserve the keyframe's actor pose, hand ownership, product state, framing, and light direction at the opening",
        ]
        return [item for item in locks if item]

    def _planned_start_state(self, plan: CreativePlan, scene: dict[str, Any], prior_end_state: dict[str, Any] | None) -> dict[str, Any]:
        if prior_end_state:
            return deepcopy(prior_end_state)
        return {
            "actor": self._text(plan.primaryCharacter.get("description")),
            "location": self._text(plan.primaryLocation.get("description")),
            "productState": self._text(scene.get("productMoment")),
            "actionPhase": "opening pose shown by the selected keyframe",
            "camera": self._text(self._dict(scene.get("camera")).get("shot")),
        }

    def _planned_end_state(self, scene: dict[str, Any]) -> dict[str, Any]:
        return {
            "visibleOutcome": self._text(scene.get("visualAction")) or self._text(scene.get("sceneGoal")),
            "actorState": self._text(scene.get("characterAction")),
            "productState": self._text(scene.get("productMoment")),
            "cameraState": self._text(self._dict(scene.get("camera")).get("composition")),
        }

    def _handoff_to_next_scene(self, plan: CreativePlan, scene: dict[str, Any], review: dict[str, Any]) -> None:
        scenes = [item for item in plan.scenes if isinstance(item, dict)]
        try:
            index = scenes.index(scene)
        except ValueError:
            return
        if index + 1 >= len(scenes):
            return
        next_scene = scenes[index + 1]
        contract = self._dict(next_scene.get("shotContract"))
        observed_end = self._dict(review.get("observedEndState"))
        if observed_end:
            contract["observedHandoff"] = observed_end
            contract["plannedStartState"] = deepcopy(observed_end)
        completed = self._strings(review.get("completedBeats"))
        if completed:
            contract["alreadyHappened"] = list(dict.fromkeys([*self._strings(contract.get("alreadyHappened")), *completed]))
        next_scene["shotContract"] = contract
        next_scene["finalVideoPrompt"] = self.compile_scene_prompt(plan, next_scene)
        next_scene["promptQuality"] = self.lint_scene_prompt(next_scene)

    def _refresh_current_scene(self, plan: CreativePlan) -> None:
        scenes = [item for item in plan.scenes if isinstance(item, dict)]
        current = next(
            (int(item.get("sceneIndex") or 1) for item in scenes if not self._dict(item.get("takeReview")).get("canonAccepted")),
            len(scenes) if scenes else 1,
        )
        state = dict(plan.sequenceState or {})
        state["currentSceneIndex"] = current
        plan.sequenceState = state

    def _primary_spend(self, scene: dict[str, Any]) -> str:
        text = " ".join(
            self._text(scene.get(key)).lower()
            for key in ("visualAction", "productMoment", "characterAction", "sceneGoal")
        )
        if any(word in text for word in ("screen", "ui", "product", "packaging", "logo", "detail", "result")):
            return "product_identity"
        if any(word in text for word in ("run", "jump", "turn", "walk", "pick", "open", "scan", "move")):
            return "motion_clarity"
        return "character_identity"

    def _economize(self, scene: dict[str, Any]) -> list[str]:
        primary = self._primary_spend(scene)
        if primary == "product_identity":
            return ["crowd density", "bold camera motion", "tiny background detail"]
        if primary == "motion_clarity":
            return ["facial micro-expression", "dense props", "readable background text"]
        return ["bold motion", "crowd density", "tiny product detail"]

    def _default_lighting(self, plan: CreativePlan, scene: dict[str, Any], index: int) -> str:
        location = self._text(plan.primaryLocation.get("description"))
        if index == 0:
            return f"Motivated soft key from the location's established practical source; preserve its direction. {location}".strip()
        return "Preserve the established key-light direction and color relationship; change intensity only when the story turn motivates it."

    def _default_atmosphere(self, scene: dict[str, Any]) -> str:
        audio = self._text(scene.get("ambientAudio"))
        return f"Environment remains physically coherent; atmosphere is carried by {audio or 'subtle native room tone and one motivated sound cue'}"

    def _value_shift(self, scene: dict[str, Any], index: int) -> str:
        purpose = self._text(scene.get("narrativePurpose")).lower()
        if "result" in purpose or "proof" in purpose:
            return "uncertainty to evidence"
        if "cta" in purpose or "ending" in purpose:
            return "consideration to decision"
        if index == 0:
            return "ordinary to curious"
        return "setup to forward movement"

    def _arc_position(self, index: int, count: int) -> str:
        if index == 0:
            return "open"
        if index == count - 1:
            return "release"
        ratio = index / max(count - 1, 1)
        if ratio < 0.5:
            return "rising"
        if ratio < 0.8:
            return "turn"
        return "climax"

    def _next_action(self, verdict: str) -> str:
        return {
            "keep": "Lock this take as canon and continue to the next scene.",
            "fix_in_post": "Lock the footage as canon and record the post-production fix.",
            "edit": "Keep this take as the edit source and change only the failing layer.",
            "reroll": "Generate again with the same prompt and a new sample; do not change other variables.",
            "rewrite": "Change one diagnosed prompt clause, then regenerate.",
            "reject": "Do not update canon or use this take as a continuation source.",
        }.get(verdict, "Review the take before continuing.")

    def _reference_tag(self, reference: dict[str, Any]) -> str:
        file_name = self._text(reference.get("sourceFileName")) or self._text(reference.get("name")) or self._text(reference.get("referenceLabel"))
        return f"@{file_name.lstrip('@')}" if file_name else "@product_reference"

    def _compress_prompt(self, value: str) -> str:
        compact = re.sub(r"\s+", " ", value).strip()
        if len(compact) <= PROMPT_BUDGET_CHARS:
            return compact
        sentences = re.split(r"(?<=[.!?])\s+", compact)
        required_prefixes = ("Use the selected", "This clip only", "Stop when", "Preserve", "Do not yet", "Avoid")
        required = [item for item in sentences if item.startswith(required_prefixes)]
        optional = [item for item in sentences if item not in required]
        output: list[str] = []
        for sentence in [*required, *optional]:
            if len(" ".join([*output, sentence])) > PROMPT_BUDGET_CHARS:
                continue
            output.append(sentence)
        return " ".join(output)

    def _state_text(self, value: Any) -> str:
        if isinstance(value, dict):
            return "; ".join(f"{key}: {item}" for key, item in value.items() if self._text(item))
        return self._text(value)

    def _first_text(self, value: Any) -> str:
        values = self._strings(value)
        return values[0] if values else ""

    def _dict(self, value: Any) -> dict[str, Any]:
        return dict(value) if isinstance(value, dict) else {}

    def _strings(self, value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [self._text(item) for item in value if self._text(item)]
        text = self._text(value)
        return [text] if text else []

    def _text(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (dict, list)):
            return ""
        return str(value).strip()

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
