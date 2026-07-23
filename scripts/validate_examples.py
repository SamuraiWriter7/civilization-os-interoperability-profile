from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]

SCHEMA_PATH = (
    ROOT
    / "schemas"
    / "civilization-os-interoperability-profile.schema.json"
)

PASS_DIR = ROOT / "examples" / "pass"
FAIL_DIR = ROOT / "examples" / "fail"


EXPECTED_STAGES = (
    "origin",
    "trace",
    "authorization",
    "execution",
    "audit",
    "royalty",
)


REQUIRED_OUTPUTS = {
    "origin": "origin_id",
    "trace": "trace_id",
    "authorization": "authorization_receipt_id",
    "execution": "execution_id",
    "audit": "audit_id",
    "royalty": "allocation_id",
}


REQUIRED_LINKS = {
    "trace": (
        "origin",
        "origin_id",
    ),
    "authorization": (
        "trace",
        "trace_id",
    ),
    "execution": (
        "authorization",
        "authorization_receipt_id",
    ),
    "audit": (
        "execution",
        "execution_id",
    ),
    "royalty": (
        "audit",
        "audit_id",
    ),
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    if not isinstance(data, dict):
        raise ValueError(
            "The YAML document root must be an object."
        )

    return data


def format_json_path(error: Any) -> str:
    if not error.absolute_path:
        return "<root>"

    parts: list[str] = []

    for part in error.absolute_path:
        if isinstance(part, int):
            parts.append(f"[{part}]")
        else:
            if parts:
                parts.append(".")
            parts.append(str(part))

    return "".join(parts)


def schema_errors(
    instance: dict[str, Any],
    schema: dict[str, Any],
) -> list[str]:
    validator = Draft202012Validator(schema)

    errors = sorted(
        validator.iter_errors(instance),
        key=lambda error: list(error.absolute_path),
    )

    return [
        f"{format_json_path(error)}: {error.message}"
        for error in errors
    ]


def semantic_errors(
    profile: dict[str, Any],
) -> list[str]:
    errors: list[str] = []

    sequence = profile.get(
        "profile_sequence",
        [],
    )

    if not isinstance(sequence, list):
        return [
            "profile_sequence must be an array."
        ]

    stage_positions: dict[str, int] = {}
    produced: dict[str, set[str]] = {}

    for index, binding in enumerate(sequence):
        if not isinstance(binding, dict):
            errors.append(
                f"profile_sequence[{index}] must be an object."
            )
            continue

        stage = binding.get("stage")
        position = binding.get("position")

        if stage not in EXPECTED_STAGES:
            continue

        if stage in stage_positions:
            errors.append(
                f"Stage '{stage}' appears more than once."
            )
        else:
            stage_positions[stage] = index

        expected_position = index + 1

        if position != expected_position:
            errors.append(
                f"Stage '{stage}' has position {position}; "
                f"expected {expected_position}."
            )

        output_ids: set[str] = set()

        for output in binding.get(
            "produces",
            [],
        ):
            if not isinstance(output, dict):
                continue

            canonical_id = output.get(
                "canonical_id"
            )

            if not isinstance(
                canonical_id,
                str,
            ):
                continue

            if canonical_id in output_ids:
                errors.append(
                    f"Stage '{stage}' produces duplicate "
                    f"canonical ID '{canonical_id}'."
                )

            output_ids.add(canonical_id)

        produced[stage] = output_ids

    actual_stages = tuple(
        binding.get("stage")
        for binding in sequence
        if isinstance(binding, dict)
    )

    if actual_stages != EXPECTED_STAGES:
        errors.append(
            "profile_sequence must follow this exact order: "
            + " -> ".join(EXPECTED_STAGES)
            + "."
        )

    all_producers: dict[str, str] = {}

    for stage in EXPECTED_STAGES:
        for canonical_id in produced.get(
            stage,
            set(),
        ):
            previous_stage = all_producers.get(
                canonical_id
            )

            if previous_stage is not None:
                errors.append(
                    f"Canonical ID '{canonical_id}' is "
                    f"produced by both '{previous_stage}' "
                    f"and '{stage}'."
                )
            else:
                all_producers[canonical_id] = stage

    for index, binding in enumerate(sequence):
        if not isinstance(binding, dict):
            continue

        stage = binding.get("stage")

        if stage not in EXPECTED_STAGES:
            continue

        seen_inputs: set[tuple[str, str]] = set()

        for item in binding.get(
            "consumes",
            [],
        ):
            if not isinstance(item, dict):
                continue

            source_stage = item.get(
                "from_stage"
            )

            canonical_id = item.get(
                "canonical_id"
            )

            link = (
                str(source_stage),
                str(canonical_id),
            )

            if link in seen_inputs:
                errors.append(
                    f"Stage '{stage}' consumes duplicate "
                    f"link '{source_stage}:{canonical_id}'."
                )

            seen_inputs.add(link)

            source_position = stage_positions.get(
                str(source_stage)
            )

            if source_position is None:
                errors.append(
                    f"Stage '{stage}' references unknown "
                    f"source stage '{source_stage}'."
                )
                continue

            if source_position >= index:
                errors.append(
                    f"Stage '{stage}' consumes "
                    f"'{canonical_id}' from non-earlier "
                    f"stage '{source_stage}'."
                )

            source_outputs = produced.get(
                str(source_stage),
                set(),
            )

            if canonical_id not in source_outputs:
                errors.append(
                    f"Stage '{stage}' consumes "
                    f"'{canonical_id}' from "
                    f"'{source_stage}', but that stage "
                    f"does not produce it."
                )

    for stage, required_id in (
        REQUIRED_OUTPUTS.items()
    ):
        if required_id not in produced.get(
            stage,
            set(),
        ):
            errors.append(
                f"Stage '{stage}' must produce "
                f"canonical ID '{required_id}'."
            )

    bindings_by_stage = {
        binding.get("stage"): binding
        for binding in sequence
        if isinstance(binding, dict)
    }

    for stage, required_link in (
        REQUIRED_LINKS.items()
    ):
        source_stage, canonical_id = (
            required_link
        )

        binding = bindings_by_stage.get(
            stage,
            {},
        )

        consumes = (
            binding.get("consumes", [])
            if isinstance(binding, dict)
            else []
        )

        has_required_link = any(
            isinstance(item, dict)
            and item.get("from_stage")
            == source_stage
            and item.get("canonical_id")
            == canonical_id
            and item.get("required") is True
            for item in consumes
        )

        if not has_required_link:
            errors.append(
                f"Stage '{stage}' must require "
                f"'{canonical_id}' from stage "
                f"'{source_stage}'."
            )

    return errors


def validate_expected_pass(
    path: Path,
    schema: dict[str, Any],
) -> bool:
    print(
        f"[validate-pass] "
        f"{path.relative_to(ROOT)}"
    )

    try:
        instance = load_yaml(path)
    except Exception as exc:
        print(f"[yaml-error] {exc}")
        return False

    errors = schema_errors(
        instance,
        schema,
    )

    if errors:
        for error in errors:
            print(
                f"[schema-error] {error}"
            )
        return False

    print("[schema-ok]")

    errors = semantic_errors(instance)

    if errors:
        for error in errors:
            print(
                f"[semantic-error] {error}"
            )
        return False

    print("[semantic-ok]")

    return True


def validate_expected_fail(
    path: Path,
    schema: dict[str, Any],
) -> bool:
    print(
        f"[validate-fail] "
        f"{path.relative_to(ROOT)}"
    )

    try:
        instance = load_yaml(path)
    except Exception as exc:
        print(
            f"[expected-yaml-failure] "
            f"{exc}"
        )
        return True

    errors = schema_errors(
        instance,
        schema,
    )

    if errors:
        for error in errors:
            print(
                "[expected-schema-failure] "
                f"{error}"
            )
        return True

    errors = semantic_errors(instance)

    if errors:
        for error in errors:
            print(
                "[expected-semantic-failure] "
                f"{error}"
            )
        return True

    print(
        "[unexpected-pass] "
        "Failure example was accepted."
    )

    return False


def collect_yaml_files(
    directory: Path,
) -> list[Path]:
    return sorted(
        [
            *directory.glob("*.yaml"),
            *directory.glob("*.yml"),
        ]
    )


def main() -> int:
    print(
        "=== Civilization OS "
        "Interoperability Profile Validation ==="
    )

    print(
        "schema: "
        f"{SCHEMA_PATH.relative_to(ROOT)}"
    )

    print()

    schema = load_json(SCHEMA_PATH)

    Draft202012Validator.check_schema(
        schema
    )

    pass_files = collect_yaml_files(
        PASS_DIR
    )

    fail_files = collect_yaml_files(
        FAIL_DIR
    )

    if not pass_files:
        print(
            "[fatal] No pass examples found."
        )
        return 1

    success = True

    for path in pass_files:
        success = (
            validate_expected_pass(
                path,
                schema,
            )
            and success
        )

        print()

    for path in fail_files:
        success = (
            validate_expected_fail(
                path,
                schema,
            )
            and success
        )

        print()

    if success:
        print(
            "All interoperability profile "
            "examples behaved as expected."
        )
        return 0

    print("Validation failed.")

    return 1


if __name__ == "__main__":
    sys.exit(main())
