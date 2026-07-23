from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]

PROFILE_SCHEMA_PATH = (
    ROOT
    / "schemas"
    / "civilization-os-interoperability-profile.schema.json"
)

IDENTIFIER_SCHEMA_PATH = (
    ROOT
    / "schemas"
    / "canonical-identifier-registry.schema.json"
)

COMPATIBILITY_SCHEMA_PATH = (
    ROOT
    / "schemas"
    / "protocol-compatibility-registry.schema.json"
)

ADAPTER_SCHEMA_PATH = (
    ROOT
    / "schemas"
    / "protocol-adapter-registry.schema.json"
)

IDENTIFIER_REGISTRY_PATH = (
    ROOT
    / "registry"
    / "canonical-identifiers.yaml"
)

COMPATIBILITY_REGISTRY_PATH = (
    ROOT
    / "registry"
    / "protocol-compatibility.yaml"
)

ADAPTER_REGISTRY_PATH = (
    ROOT
    / "registry"
    / "protocol-adapters.yaml"
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

STAGE_POSITIONS = {
    stage: index
    for index, stage in enumerate(
        EXPECTED_STAGES,
        start=1,
    )
}

REQUIRED_CONTRACTS = {
    "origin_id": (
        "origin",
        "origin_reference",
    ),
    "trace_id": (
        "trace",
        "trace_reference",
    ),
    "authorization_receipt_id": (
        "authorization",
        "authorization_receipt_reference",
    ),
    "execution_id": (
        "execution",
        "execution_reference",
    ),
    "audit_id": (
        "audit",
        "audit_reference",
    ),
    "allocation_id": (
        "royalty",
        "allocation_reference",
    ),
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

REQUIRED_RESOLUTION_POLICY = {
    "require_resolution_receipt": True,
    "require_digest_lock": True,
    "require_exact_stage_snapshot": True,
    "require_conformance_handoff": True,
    "handoff_target": "kazene-protocol-conformance-suite",
}

REQUIRED_CONFORMANCE_FLAGS = {
    "require_ordered_execution": True,
    "require_reference_resolution": True,
    "require_registry_resolution": True,
    "require_registered_identifiers": True,
    "require_unique_contract_producers": True,
    "require_compatibility_resolution": True,
    "require_exact_protocol_versions": True,
    "reject_blocked_compatibility": True,
    "require_adapter_resolution": True,
    "reject_unbound_adapters": True,
    "require_resolution_receipt": True,
    "require_digest_lock": True,
    "require_conformance_handoff": True,
    "reject_unknown_stages": True,
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(
            f"{path.relative_to(ROOT)} must contain a JSON object."
        )

    return data


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)

    if not isinstance(data, dict):
        raise ValueError(
            f"{path.relative_to(ROOT)} must contain a YAML object."
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
        key=lambda error: tuple(
            str(part)
            for part in error.absolute_path
        ),
    )

    return [
        f"{format_json_path(error)}: {error.message}"
        for error in errors
    ]


def collect_yaml_files(
    directory: Path,
) -> list[Path]:
    return sorted(
        [
            *directory.glob("*.yaml"),
            *directory.glob("*.yml"),
        ]
    )


def resolve_repository_reference(
    reference: str,
) -> Path:
    resolved = (ROOT / reference).resolve()

    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValueError(
            f"Reference escapes repository root: {reference}"
        ) from exc

    return resolved


def build_identifier_contract_map(
    registry: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    identifiers = registry.get(
        "identifiers",
        [],
    )

    if not isinstance(identifiers, list):
        return {}

    return {
        contract["canonical_id"]: contract
        for contract in identifiers
        if isinstance(contract, dict)
        and isinstance(
            contract.get("canonical_id"),
            str,
        )
    }


def build_adapter_contract_map(
    registry: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    adapters = registry.get(
        "adapters",
        [],
    )

    if not isinstance(adapters, list):
        return {}

    return {
        adapter["adapter_id"]: adapter
        for adapter in adapters
        if isinstance(adapter, dict)
        and isinstance(
            adapter.get("adapter_id"),
            str,
        )
    }


def adapter_endpoint_key(
    endpoint: dict[str, Any],
) -> tuple[str, str, str, str]:
    return (
        str(endpoint.get("stage")),
        str(endpoint.get("protocol_id")),
        str(endpoint.get("version")),
        str(endpoint.get("record_type")),
    )


def compatibility_endpoint_key(
    endpoint: dict[str, Any],
) -> tuple[str, str, tuple[str, ...], str]:
    versions = endpoint.get(
        "versions",
        [],
    )

    if isinstance(versions, list):
        normalized_versions = tuple(
            sorted(
                str(version)
                for version in versions
            )
        )
    else:
        normalized_versions = ()

    return (
        str(endpoint.get("stage")),
        str(endpoint.get("protocol_id")),
        normalized_versions,
        str(endpoint.get("record_type")),
    )


def identifier_registry_semantic_errors(
    registry: dict[str, Any],
) -> list[str]:
    errors: list[str] = []

    identifiers = registry.get(
        "identifiers",
        [],
    )

    if not isinstance(identifiers, list):
        return [
            "identifiers must be an array."
        ]

    seen_ids: set[str] = set()

    for index, contract in enumerate(
        identifiers
    ):
        if not isinstance(contract, dict):
            errors.append(
                f"identifiers[{index}] must be an object."
            )
            continue

        canonical_id = contract.get(
            "canonical_id"
        )

        if not isinstance(canonical_id, str):
            continue

        if canonical_id in seen_ids:
            errors.append(
                f"Identifier contract '{canonical_id}' "
                "appears more than once."
            )

        seen_ids.add(canonical_id)

    contract_map = build_identifier_contract_map(
        registry
    )

    for canonical_id, (
        expected_stage,
        expected_semantic_type,
    ) in REQUIRED_CONTRACTS.items():
        contract = contract_map.get(
            canonical_id
        )

        if contract is None:
            errors.append(
                f"Required identifier contract "
                f"'{canonical_id}' is missing."
            )
            continue

        if (
            contract.get("producer_stage")
            != expected_stage
        ):
            errors.append(
                f"Identifier contract '{canonical_id}' "
                f"must use producer stage "
                f"'{expected_stage}'."
            )

        if (
            contract.get("semantic_type")
            != expected_semantic_type
        ):
            errors.append(
                f"Identifier contract '{canonical_id}' "
                f"must use semantic type "
                f"'{expected_semantic_type}'."
            )

        if contract.get("value_type") != "string":
            errors.append(
                f"Identifier contract '{canonical_id}' "
                "must use value_type 'string'."
            )

        if contract.get("cardinality") != "one":
            errors.append(
                f"Identifier contract '{canonical_id}' "
                "must use cardinality 'one'."
            )

    return errors


def adapter_registry_semantic_errors(
    registry: dict[str, Any],
    identifier_registry: dict[str, Any],
) -> list[str]:
    errors: list[str] = []

    adapters = registry.get(
        "adapters",
        [],
    )

    if not isinstance(adapters, list):
        return [
            "adapters must be an array."
        ]

    identifier_contracts = (
        build_identifier_contract_map(
            identifier_registry
        )
    )

    seen_adapter_ids: set[str] = set()

    seen_contracts: set[
        tuple[
            tuple[str, str, str, str],
            tuple[str, str, str, str],
            str,
        ]
    ] = set()

    for index, adapter in enumerate(
        adapters
    ):
        if not isinstance(adapter, dict):
            errors.append(
                f"adapters[{index}] must be an object."
            )
            continue

        adapter_id = adapter.get(
            "adapter_id"
        )

        if isinstance(adapter_id, str):
            if adapter_id in seen_adapter_ids:
                errors.append(
                    f"Adapter '{adapter_id}' "
                    "appears more than once."
                )

            seen_adapter_ids.add(adapter_id)

        source = adapter.get(
            "source",
            {},
        )

        target = adapter.get(
            "target",
            {},
        )

        if not isinstance(source, dict):
            errors.append(
                f"Adapter '{adapter_id}' "
                "source must be an object."
            )
            continue

        if not isinstance(target, dict):
            errors.append(
                f"Adapter '{adapter_id}' "
                "target must be an object."
            )
            continue

        source_stage = str(
            source.get("stage")
        )

        target_stage = str(
            target.get("stage")
        )

        source_position = STAGE_POSITIONS.get(
            source_stage
        )

        target_position = STAGE_POSITIONS.get(
            target_stage
        )

        if (
            source_position is not None
            and target_position is not None
            and source_position >= target_position
        ):
            errors.append(
                f"Adapter '{adapter_id}' must point "
                f"from an earlier stage; received "
                f"'{source_stage}' to '{target_stage}'."
            )

        canonical_id = str(
            adapter.get("canonical_id")
        )

        identifier_contract = (
            identifier_contracts.get(
                canonical_id
            )
        )

        if identifier_contract is None:
            errors.append(
                f"Adapter '{adapter_id}' uses "
                f"unregistered canonical ID "
                f"'{canonical_id}'."
            )
        elif (
            identifier_contract.get(
                "producer_stage"
            )
            != source_stage
        ):
            errors.append(
                f"Adapter '{adapter_id}' uses "
                f"'{canonical_id}' from "
                f"'{source_stage}', but the "
                f"identifier registry assigns its "
                f"producer to "
                f"'{identifier_contract.get('producer_stage')}'."
            )

        contract_key = (
            adapter_endpoint_key(source),
            adapter_endpoint_key(target),
            canonical_id,
        )

        if contract_key in seen_contracts:
            errors.append(
                f"Adapter contract for "
                f"'{canonical_id}' from "
                f"'{source_stage}' to "
                f"'{target_stage}' is duplicated."
            )

        seen_contracts.add(contract_key)

        transforms = adapter.get(
            "transforms",
            [],
        )

        if not isinstance(transforms, list):
            continue

        seen_target_fields: set[str] = set()

        for transform in transforms:
            if not isinstance(transform, dict):
                continue

            target_field = transform.get(
                "to_field"
            )

            if not isinstance(
                target_field,
                str,
            ):
                continue

            if target_field in seen_target_fields:
                errors.append(
                    f"Adapter '{adapter_id}' writes "
                    f"target field '{target_field}' "
                    "more than once."
                )

            seen_target_fields.add(
                target_field
            )

    return errors


def adapter_matches_compatibility_link(
    adapter: dict[str, Any],
    link: dict[str, Any],
) -> bool:
    source = adapter.get(
        "source",
        {},
    )

    target = adapter.get(
        "target",
        {},
    )

    link_source = link.get(
        "source",
        {},
    )

    link_target = link.get(
        "target",
        {},
    )

    if not all(
        isinstance(item, dict)
        for item in (
            source,
            target,
            link_source,
            link_target,
        )
    ):
        return False

    source_versions = link_source.get(
        "versions",
        [],
    )

    target_versions = link_target.get(
        "versions",
        [],
    )

    return (
        source.get("stage")
        == link_source.get("stage")
        and source.get("protocol_id")
        == link_source.get("protocol_id")
        and source.get("record_type")
        == link_source.get("record_type")
        and isinstance(source_versions, list)
        and source.get("version")
        in source_versions
        and target.get("stage")
        == link_target.get("stage")
        and target.get("protocol_id")
        == link_target.get("protocol_id")
        and target.get("record_type")
        == link_target.get("record_type")
        and isinstance(target_versions, list)
        and target.get("version")
        in target_versions
        and adapter.get("canonical_id")
        == link.get("canonical_id")
    )


def compatibility_registry_semantic_errors(
    registry: dict[str, Any],
    identifier_registry: dict[str, Any],
    adapter_registry: dict[str, Any],
) -> list[str]:
    errors: list[str] = []

    links = registry.get(
        "links",
        [],
    )

    if not isinstance(links, list):
        return [
            "links must be an array."
        ]

    identifier_contracts = (
        build_identifier_contract_map(
            identifier_registry
        )
    )

    adapter_contracts = (
        build_adapter_contract_map(
            adapter_registry
        )
    )

    seen_link_ids: set[str] = set()

    seen_contracts: set[
        tuple[
            tuple[
                str,
                str,
                tuple[str, ...],
                str,
            ],
            tuple[
                str,
                str,
                tuple[str, ...],
                str,
            ],
            str,
        ]
    ] = set()

    for index, link in enumerate(links):
        if not isinstance(link, dict):
            errors.append(
                f"links[{index}] must be an object."
            )
            continue

        link_id = link.get(
            "link_id"
        )

        if isinstance(link_id, str):
            if link_id in seen_link_ids:
                errors.append(
                    f"Compatibility link "
                    f"'{link_id}' appears more "
                    "than once."
                )

            seen_link_ids.add(link_id)

        source = link.get(
            "source",
            {},
        )

        target = link.get(
            "target",
            {},
        )

        if not isinstance(source, dict):
            errors.append(
                f"Compatibility link "
                f"'{link_id}' source must "
                "be an object."
            )
            continue

        if not isinstance(target, dict):
            errors.append(
                f"Compatibility link "
                f"'{link_id}' target must "
                "be an object."
            )
            continue

        source_stage = str(
            source.get("stage")
        )

        target_stage = str(
            target.get("stage")
        )

        source_position = STAGE_POSITIONS.get(
            source_stage
        )

        target_position = STAGE_POSITIONS.get(
            target_stage
        )

        if (
            source_position is not None
            and target_position is not None
            and source_position >= target_position
        ):
            errors.append(
                f"Compatibility link "
                f"'{link_id}' must point from "
                f"an earlier stage; received "
                f"'{source_stage}' to "
                f"'{target_stage}'."
            )

        canonical_id = str(
            link.get("canonical_id")
        )

        identifier_contract = (
            identifier_contracts.get(
                canonical_id
            )
        )

        if identifier_contract is None:
            errors.append(
                f"Compatibility link "
                f"'{link_id}' uses unregistered "
                f"canonical ID '{canonical_id}'."
            )
        elif (
            identifier_contract.get(
                "producer_stage"
            )
            != source_stage
        ):
            errors.append(
                f"Compatibility link "
                f"'{link_id}' uses "
                f"'{canonical_id}' from "
                f"'{source_stage}', but the "
                f"identifier registry assigns "
                f"its producer to "
                f"'{identifier_contract.get('producer_stage')}'."
            )

        contract_key = (
            compatibility_endpoint_key(
                source
            ),
            compatibility_endpoint_key(
                target
            ),
            canonical_id,
        )

        if contract_key in seen_contracts:
            errors.append(
                f"Compatibility contract for "
                f"'{canonical_id}' from "
                f"'{source_stage}' to "
                f"'{target_stage}' is duplicated."
            )

        seen_contracts.add(contract_key)

        disposition = link.get(
            "disposition"
        )

        adapter_id = link.get(
            "adapter_id"
        )

        if disposition == "adapter-required":
            if not isinstance(adapter_id, str):
                errors.append(
                    f"Compatibility link "
                    f"'{link_id}' requires "
                    "adapter_id."
                )
                continue

            adapter = adapter_contracts.get(
                adapter_id
            )

            if adapter is None:
                errors.append(
                    f"Compatibility link "
                    f"'{link_id}' references "
                    f"unknown adapter "
                    f"'{adapter_id}'."
                )
                continue

            if adapter.get("status") == "deprecated":
                errors.append(
                    f"Compatibility link "
                    f"'{link_id}' references "
                    f"deprecated adapter "
                    f"'{adapter_id}'."
                )

            if not adapter_matches_compatibility_link(
                adapter,
                link,
            ):
                errors.append(
                    f"Compatibility link "
                    f"'{link_id}' does not match "
                    f"adapter '{adapter_id}' "
                    "endpoints, versions, record "
                    "types, or canonical identifier."
                )

        elif adapter_id is not None:
            errors.append(
                f"Compatibility link "
                f"'{link_id}' must not declare "
                f"adapter_id when disposition "
                f"is '{disposition}'."
            )

    return errors


def registry_binding_errors(
    profile: dict[str, Any],
    profile_field: str,
    registry: dict[str, Any],
    registry_path: Path,
) -> list[str]:
    errors: list[str] = []

    binding = profile.get(
        profile_field,
        {},
    )

    if not isinstance(binding, dict):
        return [
            f"{profile_field} must be an object."
        ]

    if (
        binding.get("registry_id")
        != registry.get("registry_id")
    ):
        errors.append(
            f"{profile_field}.registry_id "
            "does not match the loaded registry."
        )

    if (
        binding.get("version")
        != registry.get("version")
    ):
        errors.append(
            f"{profile_field}.version "
            "does not match the loaded registry."
        )

    registry_ref = binding.get(
        "registry_ref"
    )

    if not isinstance(registry_ref, str):
        return errors

    try:
        declared_path = (
            resolve_repository_reference(
                registry_ref
            )
        )
    except ValueError as exc:
        errors.append(
            f"{profile_field}.registry_ref: {exc}"
        )
        return errors

    if declared_path != registry_path.resolve():
        errors.append(
            f"{profile_field}.registry_ref "
            "does not resolve to the expected registry."
        )

    if not declared_path.is_file():
        errors.append(
            f"{profile_field}.registry_ref "
            f"does not exist: {registry_ref}."
        )

    return errors


def profile_endpoint_matches_adapter(
    binding: dict[str, Any],
    endpoint: dict[str, Any],
) -> bool:
    protocol = binding.get(
        "protocol",
        {},
    )

    if not isinstance(protocol, dict):
        return False

    return (
        binding.get("stage")
        == endpoint.get("stage")
        and protocol.get("protocol_id")
        == endpoint.get("protocol_id")
        and protocol.get("version")
        == endpoint.get("version")
        and protocol.get("record_type")
        == endpoint.get("record_type")
    )


def profile_endpoint_matches_compatibility(
    binding: dict[str, Any],
    endpoint: dict[str, Any],
) -> bool:
    protocol = binding.get(
        "protocol",
        {},
    )

    versions = endpoint.get(
        "versions",
        [],
    )

    if not isinstance(protocol, dict):
        return False

    if not isinstance(versions, list):
        return False

    return (
        binding.get("stage")
        == endpoint.get("stage")
        and protocol.get("protocol_id")
        == endpoint.get("protocol_id")
        and protocol.get("version")
        in versions
        and protocol.get("record_type")
        == endpoint.get("record_type")
    )


def matching_compatibility_links(
    compatibility_registry: dict[str, Any],
    source_binding: dict[str, Any],
    target_binding: dict[str, Any],
    canonical_id: str,
) -> list[dict[str, Any]]:
    links = compatibility_registry.get(
        "links",
        [],
    )

    if not isinstance(links, list):
        return []

    matches: list[dict[str, Any]] = []

    for link in links:
        if not isinstance(link, dict):
            continue

        source = link.get(
            "source",
            {},
        )

        target = link.get(
            "target",
            {},
        )

        if not isinstance(source, dict):
            continue

        if not isinstance(target, dict):
            continue

        if (
            profile_endpoint_matches_compatibility(
                source_binding,
                source,
            )
            and profile_endpoint_matches_compatibility(
                target_binding,
                target,
            )
            and link.get("canonical_id")
            == canonical_id
        ):
            matches.append(link)

    return matches


def adapter_binding_semantic_errors(
    profile: dict[str, Any],
    bindings_by_stage: dict[
        str,
        dict[str, Any],
    ],
    adapter_registry: dict[str, Any],
) -> tuple[
    list[str],
    dict[str, dict[str, Any]],
]:
    errors: list[str] = []

    raw_bindings = profile.get(
        "adapter_bindings",
        [],
    )

    if not isinstance(raw_bindings, list):
        return (
            [
                "adapter_bindings must be an array."
            ],
            {},
        )

    adapter_contracts = (
        build_adapter_contract_map(
            adapter_registry
        )
    )

    binding_map: dict[
        str,
        dict[str, Any],
    ] = {}

    semantic_keys: set[
        tuple[str, str, str, str]
    ] = set()

    for index, binding in enumerate(
        raw_bindings
    ):
        if not isinstance(binding, dict):
            errors.append(
                f"adapter_bindings[{index}] "
                "must be an object."
            )
            continue

        binding_id = binding.get(
            "binding_id"
        )

        if not isinstance(binding_id, str):
            continue

        if binding_id in binding_map:
            errors.append(
                f"Adapter binding "
                f"'{binding_id}' appears more "
                "than once."
            )

        binding_map[binding_id] = binding

        adapter_id = str(
            binding.get("adapter_id")
        )

        source_stage = str(
            binding.get("source_stage")
        )

        target_stage = str(
            binding.get("target_stage")
        )

        canonical_id = str(
            binding.get("canonical_id")
        )

        semantic_key = (
            adapter_id,
            source_stage,
            target_stage,
            canonical_id,
        )

        if semantic_key in semantic_keys:
            errors.append(
                f"Adapter binding for "
                f"'{adapter_id}' from "
                f"'{source_stage}' to "
                f"'{target_stage}' and "
                f"'{canonical_id}' is duplicated."
            )

        semantic_keys.add(semantic_key)

        adapter = adapter_contracts.get(
            adapter_id
        )

        if adapter is None:
            errors.append(
                f"Adapter binding "
                f"'{binding_id}' references "
                f"unknown adapter "
                f"'{adapter_id}'."
            )
            continue

        if (
            binding.get("adapter_version")
            != adapter.get("adapter_version")
        ):
            errors.append(
                f"Adapter binding "
                f"'{binding_id}' version does "
                f"not match adapter "
                f"'{adapter_id}'."
            )

        if (
            binding.get("canonical_id")
            != adapter.get("canonical_id")
        ):
            errors.append(
                f"Adapter binding "
                f"'{binding_id}' canonical_id "
                f"does not match adapter "
                f"'{adapter_id}'."
            )

        source_position = STAGE_POSITIONS.get(
            source_stage
        )

        target_position = STAGE_POSITIONS.get(
            target_stage
        )

        if (
            source_position is not None
            and target_position is not None
            and source_position >= target_position
        ):
            errors.append(
                f"Adapter binding "
                f"'{binding_id}' must point "
                "from an earlier stage."
            )

        source_binding = (
            bindings_by_stage.get(
                source_stage
            )
        )

        target_binding = (
            bindings_by_stage.get(
                target_stage
            )
        )

        if source_binding is None:
            errors.append(
                f"Adapter binding "
                f"'{binding_id}' references "
                f"unknown source stage "
                f"'{source_stage}'."
            )
        else:
            source_endpoint = adapter.get(
                "source",
                {},
            )

            if (
                not isinstance(
                    source_endpoint,
                    dict,
                )
                or not profile_endpoint_matches_adapter(
                    source_binding,
                    source_endpoint,
                )
            ):
                errors.append(
                    f"Adapter binding "
                    f"'{binding_id}' source "
                    f"endpoint does not match "
                    f"adapter '{adapter_id}'."
                )

        if target_binding is None:
            errors.append(
                f"Adapter binding "
                f"'{binding_id}' references "
                f"unknown target stage "
                f"'{target_stage}'."
            )
        else:
            target_endpoint = adapter.get(
                "target",
                {},
            )

            if (
                not isinstance(
                    target_endpoint,
                    dict,
                )
                or not profile_endpoint_matches_adapter(
                    target_binding,
                    target_endpoint,
                )
            ):
                errors.append(
                    f"Adapter binding "
                    f"'{binding_id}' target "
                    f"endpoint does not match "
                    f"adapter '{adapter_id}'."
                )

    return errors, binding_map


def find_matching_adapter_bindings(
    binding_map: dict[
        str,
        dict[str, Any],
    ],
    adapter_id: str,
    source_stage: str,
    target_stage: str,
    canonical_id: str,
) -> list[dict[str, Any]]:
    return [
        binding
        for binding in binding_map.values()
        if binding.get("adapter_id")
        == adapter_id
        and binding.get("source_stage")
        == source_stage
        and binding.get("target_stage")
        == target_stage
        and binding.get("canonical_id")
        == canonical_id
    ]


def validate_resolution_policy(
    profile: dict[str, Any],
) -> list[str]:
    errors: list[str] = []

    policy = profile.get(
        "resolution_policy",
        {},
    )

    if not isinstance(policy, dict):
        return [
            "resolution_policy must be an object."
        ]

    for field, expected in (
        REQUIRED_RESOLUTION_POLICY.items()
    ):
        if policy.get(field) != expected:
            errors.append(
                f"resolution_policy.{field} "
                f"must be {expected!r}."
            )

    return errors


def validate_conformance_flags(
    profile: dict[str, Any],
) -> list[str]:
    errors: list[str] = []

    conformance = profile.get(
        "conformance",
        {},
    )

    if not isinstance(conformance, dict):
        return [
            "conformance must be an object."
        ]

    for field, expected in (
        REQUIRED_CONFORMANCE_FLAGS.items()
    ):
        if conformance.get(field) != expected:
            errors.append(
                f"conformance.{field} "
                f"must be {expected!r}."
            )

    return errors


def profile_semantic_errors(
    profile: dict[str, Any],
    identifier_registry: dict[str, Any],
    compatibility_registry: dict[str, Any],
    adapter_registry: dict[str, Any],
) -> list[str]:
    errors: list[str] = []

    errors.extend(
        registry_binding_errors(
            profile,
            "identifier_registry",
            identifier_registry,
            IDENTIFIER_REGISTRY_PATH,
        )
    )

    errors.extend(
        registry_binding_errors(
            profile,
            "compatibility_registry",
            compatibility_registry,
            COMPATIBILITY_REGISTRY_PATH,
        )
    )

    errors.extend(
        registry_binding_errors(
            profile,
            "adapter_registry",
            adapter_registry,
            ADAPTER_REGISTRY_PATH,
        )
    )

    namespace = profile.get(
        "identifier_namespace"
    )

    for label, registry in (
        (
            "identifier",
            identifier_registry,
        ),
        (
            "compatibility",
            compatibility_registry,
        ),
        (
            "adapter",
            adapter_registry,
        ),
    ):
        if namespace != registry.get(
            "namespace"
        ):
            errors.append(
                f"Profile identifier_namespace "
                f"does not match the {label} "
                "registry namespace."
            )

    errors.extend(
        validate_resolution_policy(
            profile
        )
    )

    errors.extend(
        validate_conformance_flags(
            profile
        )
    )

    sequence = profile.get(
        "profile_sequence",
        [],
    )

    if not isinstance(sequence, list):
        return errors + [
            "profile_sequence must be an array."
        ]

    actual_stages = tuple(
        binding.get("stage")
        for binding in sequence
        if isinstance(binding, dict)
    )

    if actual_stages != EXPECTED_STAGES:
        errors.append(
            "profile_sequence must follow "
            "this exact order: "
            + " -> ".join(EXPECTED_STAGES)
            + "."
        )

    bindings_by_stage: dict[
        str,
        dict[str, Any],
    ] = {}

    produced_by_stage: dict[
        str,
        set[str],
    ] = {}

    for index, binding in enumerate(
        sequence
    ):
        if not isinstance(binding, dict):
            errors.append(
                f"profile_sequence[{index}] "
                "must be an object."
            )
            continue

        stage = binding.get(
            "stage"
        )

        if stage not in EXPECTED_STAGES:
            continue

        stage_name = str(stage)

        if stage_name in bindings_by_stage:
            errors.append(
                f"Stage '{stage_name}' "
                "appears more than once."
            )

        bindings_by_stage[
            stage_name
        ] = binding

        expected_position = index + 1

        if (
            binding.get("position")
            != expected_position
        ):
            errors.append(
                f"Stage '{stage_name}' has "
                f"position "
                f"{binding.get('position')}; "
                f"expected {expected_position}."
            )

        produced_ids: list[str] = []

        produces = binding.get(
            "produces",
            [],
        )

        if isinstance(produces, list):
            for output in produces:
                if not isinstance(
                    output,
                    dict,
                ):
                    continue

                canonical_id = output.get(
                    "canonical_id"
                )

                if isinstance(
                    canonical_id,
                    str,
                ):
                    produced_ids.append(
                        canonical_id
                    )

        if len(produced_ids) != len(
            set(produced_ids)
        ):
            errors.append(
                f"Stage '{stage_name}' "
                "produces duplicate canonical "
                "identifiers."
            )

        produced_by_stage[
            stage_name
        ] = set(produced_ids)

    (
        adapter_binding_errors,
        adapter_binding_map,
    ) = adapter_binding_semantic_errors(
        profile,
        bindings_by_stage,
        adapter_registry,
    )

    errors.extend(
        adapter_binding_errors
    )

    identifier_contracts = (
        build_identifier_contract_map(
            identifier_registry
        )
    )

    adapter_contracts = (
        build_adapter_contract_map(
            adapter_registry
        )
    )

    global_producers: dict[
        str,
        str,
    ] = {}

    for stage, canonical_ids in (
        produced_by_stage.items()
    ):
        for canonical_id in canonical_ids:
            previous_stage = (
                global_producers.get(
                    canonical_id
                )
            )

            if previous_stage is not None:
                errors.append(
                    f"Canonical ID "
                    f"'{canonical_id}' is "
                    f"produced by both "
                    f"'{previous_stage}' and "
                    f"'{stage}'."
                )
            else:
                global_producers[
                    canonical_id
                ] = stage

            contract = (
                identifier_contracts.get(
                    canonical_id
                )
            )

            if contract is None:
                errors.append(
                    f"Produced canonical ID "
                    f"'{canonical_id}' is not "
                    "registered."
                )
                continue

            if (
                contract.get(
                    "producer_stage"
                )
                != stage
            ):
                errors.append(
                    f"Identifier contract "
                    f"'{canonical_id}' declares "
                    f"producer "
                    f"'{contract.get('producer_stage')}', "
                    f"but the profile produces "
                    f"it at stage '{stage}'."
                )

    used_adapter_binding_ids: set[str] = (
        set()
    )

    for target_index, target_binding in (
        enumerate(sequence)
    ):
        if not isinstance(
            target_binding,
            dict,
        ):
            continue

        target_stage = target_binding.get(
            "stage"
        )

        if target_stage not in EXPECTED_STAGES:
            continue

        target_stage_name = str(
            target_stage
        )

        seen_inputs: set[
            tuple[str, str]
        ] = set()

        consumes = target_binding.get(
            "consumes",
            [],
        )

        if not isinstance(consumes, list):
            continue

        for item in consumes:
            if not isinstance(item, dict):
                continue

            source_stage = str(
                item.get("from_stage")
            )

            canonical_id = str(
                item.get("canonical_id")
            )

            link_key = (
                source_stage,
                canonical_id,
            )

            if link_key in seen_inputs:
                errors.append(
                    f"Stage "
                    f"'{target_stage_name}' "
                    f"consumes duplicate link "
                    f"'{source_stage}:"
                    f"{canonical_id}'."
                )

            seen_inputs.add(link_key)

            identifier_contract = (
                identifier_contracts.get(
                    canonical_id
                )
            )

            if identifier_contract is None:
                errors.append(
                    f"Consumed canonical ID "
                    f"'{canonical_id}' is not "
                    "registered."
                )
            elif (
                identifier_contract.get(
                    "producer_stage"
                )
                != source_stage
            ):
                errors.append(
                    f"Stage "
                    f"'{target_stage_name}' "
                    f"declares "
                    f"'{canonical_id}' from "
                    f"'{source_stage}', but its "
                    f"registry producer is "
                    f"'{identifier_contract.get('producer_stage')}'."
                )

            source_position = (
                STAGE_POSITIONS.get(
                    source_stage
                )
            )

            if source_position is None:
                errors.append(
                    f"Stage "
                    f"'{target_stage_name}' "
                    f"references unknown source "
                    f"stage '{source_stage}'."
                )
                continue

            if source_position >= (
                target_index + 1
            ):
                errors.append(
                    f"Stage "
                    f"'{target_stage_name}' "
                    f"consumes "
                    f"'{canonical_id}' from "
                    f"non-earlier stage "
                    f"'{source_stage}'."
                )

            source_outputs = (
                produced_by_stage.get(
                    source_stage,
                    set(),
                )
            )

            if canonical_id not in source_outputs:
                errors.append(
                    f"Stage "
                    f"'{target_stage_name}' "
                    f"consumes "
                    f"'{canonical_id}' from "
                    f"'{source_stage}', but "
                    "that stage does not "
                    "produce it."
                )

            source_binding = (
                bindings_by_stage.get(
                    source_stage
                )
            )

            if source_binding is None:
                continue

            matches = (
                matching_compatibility_links(
                    compatibility_registry,
                    source_binding,
                    target_binding,
                    canonical_id,
                )
            )

            if not matches:
                errors.append(
                    f"No compatibility contract "
                    f"for '{canonical_id}' from "
                    f"'{source_stage}' to "
                    f"'{target_stage_name}'."
                )
                continue

            if len(matches) > 1:
                link_ids = sorted(
                    str(
                        match.get("link_id")
                    )
                    for match in matches
                )

                errors.append(
                    f"Ambiguous compatibility "
                    f"contracts for "
                    f"'{canonical_id}' from "
                    f"'{source_stage}' to "
                    f"'{target_stage_name}': "
                    + ", ".join(link_ids)
                    + "."
                )
                continue

            link = matches[0]

            disposition = link.get(
                "disposition"
            )

            if disposition == "compatible":
                continue

            if disposition == "adapter-required":
                adapter_id = str(
                    link.get("adapter_id")
                )

                adapter = (
                    adapter_contracts.get(
                        adapter_id
                    )
                )

                if adapter is None:
                    errors.append(
                        f"Compatibility link "
                        f"'{link.get('link_id')}' "
                        f"references unknown "
                        f"adapter '{adapter_id}'."
                    )
                    continue

                matching_bindings = (
                    find_matching_adapter_bindings(
                        adapter_binding_map,
                        adapter_id,
                        source_stage,
                        target_stage_name,
                        canonical_id,
                    )
                )

                if len(matching_bindings) != 1:
                    errors.append(
                        f"Compatibility link "
                        f"'{link.get('link_id')}' "
                        "requires exactly one "
                        f"binding for adapter "
                        f"'{adapter_id}', but "
                        f"found "
                        f"{len(matching_bindings)}."
                    )
                    continue

                resolved_binding = (
                    matching_bindings[0]
                )

                binding_id = (
                    resolved_binding.get(
                        "binding_id"
                    )
                )

                if isinstance(binding_id, str):
                    used_adapter_binding_ids.add(
                        binding_id
                    )

                if (
                    resolved_binding.get(
                        "adapter_version"
                    )
                    != adapter.get(
                        "adapter_version"
                    )
                ):
                    errors.append(
                        f"Adapter binding "
                        f"'{binding_id}' version "
                        f"does not match adapter "
                        f"'{adapter_id}'."
                    )

                conformance = profile.get(
                    "conformance",
                    {},
                )

                reject_lossy = (
                    isinstance(
                        conformance,
                        dict,
                    )
                    and conformance.get(
                        "reject_lossy_adapters"
                    )
                    is True
                )

                if (
                    reject_lossy
                    and adapter.get(
                        "lossiness"
                    )
                    != "lossless"
                ):
                    errors.append(
                        f"Adapter "
                        f"'{adapter_id}' is "
                        f"'{adapter.get('lossiness')}', "
                        "but the profile rejects "
                        "non-lossless adapters."
                    )

                continue

            if disposition == "blocked":
                errors.append(
                    f"Compatibility link "
                    f"'{link.get('link_id')}' "
                    f"for '{canonical_id}' from "
                    f"'{source_stage}' to "
                    f"'{target_stage_name}' "
                    "is blocked."
                )
                continue

            if disposition == "deprecated":
                errors.append(
                    f"Compatibility link "
                    f"'{link.get('link_id')}' "
                    f"for '{canonical_id}' from "
                    f"'{source_stage}' to "
                    f"'{target_stage_name}' "
                    "is deprecated."
                )
                continue

            errors.append(
                f"Compatibility link "
                f"'{link.get('link_id')}' "
                f"has unknown disposition "
                f"'{disposition}'."
            )

    conformance = profile.get(
        "conformance",
        {},
    )

    reject_unbound_adapters = (
        isinstance(conformance, dict)
        and conformance.get(
            "reject_unbound_adapters"
        )
        is True
    )

    if reject_unbound_adapters:
        for binding_id in sorted(
            adapter_binding_map
        ):
            if (
                binding_id
                not in used_adapter_binding_ids
            ):
                errors.append(
                    f"Adapter binding "
                    f"'{binding_id}' is declared "
                    "but not required by any "
                    "resolved compatibility link."
                )

    for canonical_id, (
        required_stage,
        _,
    ) in REQUIRED_CONTRACTS.items():
        if canonical_id not in (
            produced_by_stage.get(
                required_stage,
                set(),
            )
        ):
            errors.append(
                f"Stage '{required_stage}' "
                f"must produce canonical ID "
                f"'{canonical_id}'."
            )

    for consumer_stage, (
        source_stage,
        canonical_id,
    ) in REQUIRED_LINKS.items():
        binding = bindings_by_stage.get(
            consumer_stage,
            {},
        )

        consumes = (
            binding.get("consumes", [])
            if isinstance(binding, dict)
            else []
        )

        has_required_link = (
            isinstance(consumes, list)
            and any(
                isinstance(item, dict)
                and item.get("from_stage")
                == source_stage
                and item.get("canonical_id")
                == canonical_id
                and item.get("required")
                is True
                for item in consumes
            )
        )

        if not has_required_link:
            errors.append(
                f"Stage '{consumer_stage}' "
                f"must require "
                f"'{canonical_id}' from "
                f"stage '{source_stage}'."
            )

    return errors


def validate_registry(
    label: str,
    path: Path,
    registry: dict[str, Any],
    schema: dict[str, Any],
    semantic_validator: Callable[
        [dict[str, Any]],
        list[str],
    ],
) -> bool:
    print(
        f"[validate-{label}] "
        f"{path.relative_to(ROOT)}"
    )

    errors = schema_errors(
        registry,
        schema,
    )

    if errors:
        for error in errors:
            print(
                f"[{label}-schema-error] "
                f"{error}"
            )

        return False

    print(
        f"[{label}-schema-ok]"
    )

    errors = semantic_validator(
        registry
    )

    if errors:
        for error in errors:
            print(
                f"[{label}-semantic-error] "
                f"{error}"
            )

        return False

    print(
        f"[{label}-semantic-ok]"
    )

    return True


def validate_expected_pass(
    path: Path,
    profile_schema: dict[str, Any],
    identifier_registry: dict[str, Any],
    compatibility_registry: dict[str, Any],
    adapter_registry: dict[str, Any],
) -> bool:
    print(
        f"[validate-pass] "
        f"{path.relative_to(ROOT)}"
    )

    try:
        profile = load_yaml(path)
    except Exception as exc:
        print(
            f"[yaml-error] {exc}"
        )
        return False

    errors = schema_errors(
        profile,
        profile_schema,
    )

    if errors:
        for error in errors:
            print(
                f"[schema-error] {error}"
            )

        return False

    print("[schema-ok]")

    errors = profile_semantic_errors(
        profile,
        identifier_registry,
        compatibility_registry,
        adapter_registry,
    )

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
    profile_schema: dict[str, Any],
    identifier_registry: dict[str, Any],
    compatibility_registry: dict[str, Any],
    adapter_registry: dict[str, Any],
) -> bool:
    print(
        f"[validate-fail] "
        f"{path.relative_to(ROOT)}"
    )

    try:
        profile = load_yaml(path)
    except Exception as exc:
        print(
            f"[expected-yaml-failure] "
            f"{exc}"
        )
        return True

    errors = schema_errors(
        profile,
        profile_schema,
    )

    if errors:
        for error in errors:
            print(
                f"[expected-schema-failure] "
                f"{error}"
            )

        return True

    errors = profile_semantic_errors(
        profile,
        identifier_registry,
        compatibility_registry,
        adapter_registry,
    )

    if errors:
        for error in errors:
            print(
                f"[expected-semantic-failure] "
                f"{error}"
            )

        return True

    print(
        "[unexpected-pass] "
        "Failure example was accepted."
    )

    return False


def main() -> int:
    print(
        "=== Civilization OS "
        "Interoperability Profile Validation ==="
    )

    print(
        "profile schema: "
        f"{PROFILE_SCHEMA_PATH.relative_to(ROOT)}"
    )

    print(
        "identifier schema: "
        f"{IDENTIFIER_SCHEMA_PATH.relative_to(ROOT)}"
    )

    print(
        "compatibility schema: "
        f"{COMPATIBILITY_SCHEMA_PATH.relative_to(ROOT)}"
    )

    print(
        "adapter schema: "
        f"{ADAPTER_SCHEMA_PATH.relative_to(ROOT)}"
    )

    print()

    try:
        profile_schema = load_json(
            PROFILE_SCHEMA_PATH
        )

        identifier_schema = load_json(
            IDENTIFIER_SCHEMA_PATH
        )

        compatibility_schema = load_json(
            COMPATIBILITY_SCHEMA_PATH
        )

        adapter_schema = load_json(
            ADAPTER_SCHEMA_PATH
        )

        identifier_registry = load_yaml(
            IDENTIFIER_REGISTRY_PATH
        )

        compatibility_registry = load_yaml(
            COMPATIBILITY_REGISTRY_PATH
        )

        adapter_registry = load_yaml(
            ADAPTER_REGISTRY_PATH
        )

        Draft202012Validator.check_schema(
            profile_schema
        )

        Draft202012Validator.check_schema(
            identifier_schema
        )

        Draft202012Validator.check_schema(
            compatibility_schema
        )

        Draft202012Validator.check_schema(
            adapter_schema
        )

    except Exception as exc:
        print(
            f"[fatal] {exc}"
        )
        return 1

    success = validate_registry(
        "identifier-registry",
        IDENTIFIER_REGISTRY_PATH,
        identifier_registry,
        identifier_schema,
        identifier_registry_semantic_errors,
    )

    print()

    adapter_validator = (
        lambda registry: (
            adapter_registry_semantic_errors(
                registry,
                identifier_registry,
            )
        )
    )

    success = (
        validate_registry(
            "adapter-registry",
            ADAPTER_REGISTRY_PATH,
            adapter_registry,
            adapter_schema,
            adapter_validator,
        )
        and success
    )

    print()

    compatibility_validator = (
        lambda registry: (
            compatibility_registry_semantic_errors(
                registry,
                identifier_registry,
                adapter_registry,
            )
        )
    )

    success = (
        validate_registry(
            "compatibility-registry",
            COMPATIBILITY_REGISTRY_PATH,
            compatibility_registry,
            compatibility_schema,
            compatibility_validator,
        )
        and success
    )

    print()

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

    for path in pass_files:
        success = (
            validate_expected_pass(
                path,
                profile_schema,
                identifier_registry,
                compatibility_registry,
                adapter_registry,
            )
            and success
        )

        print()

    for path in fail_files:
        success = (
            validate_expected_fail(
                path,
                profile_schema,
                identifier_registry,
                compatibility_registry,
                adapter_registry,
            )
            and success
        )

        print()

    if success:
        print(
            "All registries and interoperability "
            "profile examples behaved as expected."
        )
        return 0

    print("Validation failed.")

    return 1


if __name__ == "__main__":
    sys.exit(main())
