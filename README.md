# Civilization OS Interoperability Profile

A meta-specification for connecting independently versioned Civilization OS
protocols through ordered lifecycle profiles, canonical identifiers,
compatibility contracts, registered adapters, and digest-locked resolution
receipts.

## Overview

Civilization OS is composed of many independent protocols.

Each protocol may define a specialized capability such as:

- origin and provenance registration;
- trace propagation;
- action authorization;
- execution evidence;
- auditing;
- contribution evaluation;
- royalty allocation;
- protocol migration;
- conformance testing.

This repository does not merge those protocols into one monolithic schema.

Instead, it defines:

1. which protocol is assigned to each lifecycle stage;
2. the order in which those stages are connected;
3. which canonical identifiers pass between them;
4. which protocol versions are compatible;
5. when a registered adapter is required;
6. which connections must be blocked;
7. how the resolved composition is locked and handed off for testing.

The profile acts as the interoperability and coordination layer of
Civilization OS.

```text
Origin
  ↓ origin_id
Trace
  ↓ trace_id
Authorization
  ↓ authorization_receipt_id
Execution
  ↓ execution_id
Audit
  ↓ audit_id
Royalty
  ↓ allocation_id
Resolution Receipt
  ↓
Kazene Protocol Conformance Suite
```

## Core principle

> Preserve protocol independence while standardizing protocol connection.

Each protocol remains independently maintained and versioned.

The interoperability profile does not copy the complete schema of every
connected protocol. It records only the information necessary to connect and
validate them.

```yaml
protocol:
  protocol_id: trace-relay-protocol
  version: v1.0
  repository: SamuraiWriter7/trace-relay-protocol
  schema_ref: schemas/trace-relay-record.schema.json
  record_type: trace_relay_record
```

This repository is therefore not a new organ.

It is the nervous system that connects existing organs.

## Current release

Current profile version:

```text
v0.5.0
```

The registries are versioned independently:

| Component | Current version |
|---|---:|
| Interoperability Profile | `v0.5.0` |
| Canonical Identifier Registry | `v0.2` |
| Protocol Compatibility Registry | `v0.4` |
| Protocol Adapter Registry | `v0.4` |
| Resolution Receipt | `v0.5.0` |

A registry version does not need to match the profile version.

Each component changes only when its own contract changes.

## Standard lifecycle

Version 0.5 defines six mandatory stages.

| Position | Stage | Required canonical output |
|---:|---|---|
| 1 | Origin | `origin_id` |
| 2 | Trace | `trace_id` |
| 3 | Authorization | `authorization_receipt_id` |
| 4 | Execution | `execution_id` |
| 5 | Audit | `audit_id` |
| 6 | Royalty | `allocation_id` |

The order is fixed.

```text
Origin → Trace → Authorization → Execution → Audit → Royalty
```

A conforming profile must not:

- reorder the six stages;
- omit a mandatory stage;
- introduce an unknown stage;
- consume an identifier from a future stage;
- assign one canonical identifier to multiple producers;
- bypass a blocked compatibility contract.

## Canonical identifiers

Protocols may use different local field names for the same
cross-protocol concept.

The canonical identifier registry provides stable, protocol-independent
identifier names.

### Producer example

```yaml
produces:
  - canonical_id: trace_id
    local_field: trace_record_id
```

### Consumer example

```yaml
consumes:
  - canonical_id: trace_id
    from_stage: trace
    local_field: evidence_refs.trace_id
    required: true
```

The local fields differ, but both refer to the same canonical `trace_id`.

### Core identifier contracts

| Canonical identifier | Producer stage | Semantic role |
|---|---|---|
| `origin_id` | Origin | Provenance-root reference |
| `trace_id` | Trace | Observable trace-chain reference |
| `authorization_receipt_id` | Authorization | Authorization-decision reference |
| `execution_id` | Execution | Execution-evidence reference |
| `audit_id` | Audit | Audit-determination reference |
| `allocation_id` | Royalty | Allocation-ledger reference |

The canonical identifier registry also declares:

- value type;
- cardinality;
- mutability;
- integrity requirement;
- semantic type;
- producer ownership.

## Required lifecycle links

A conforming profile must include at least the following links.

| Consumer | Producer | Canonical identifier |
|---|---|---|
| Trace | Origin | `origin_id` |
| Authorization | Trace | `trace_id` |
| Execution | Authorization | `authorization_receipt_id` |
| Audit | Execution | `execution_id` |
| Royalty | Audit | `audit_id` |

Additional earlier-stage references may be declared.

For example:

```text
Origin ───────────────→ Authorization
Origin ─────────────────────────────→ Royalty
Trace ─────────────────→ Execution
Authorization ───────────────→ Audit
```

Every declared link must still resolve through the compatibility registry.

## Protocol compatibility contracts

Matching identifier names are not sufficient to prove interoperability.

The compatibility registry defines the exact connection between:

- source stage;
- source protocol;
- source version;
- source record type;
- target stage;
- target protocol;
- target version;
- target record type;
- canonical identifier.

A compatibility link has one of four dispositions.

| Disposition | Meaning |
|---|---|
| `compatible` | Direct connection is allowed |
| `adapter-required` | Connection requires a registered adapter |
| `blocked` | Connection is explicitly prohibited |
| `deprecated` | Connection must no longer be used |

### Direct compatibility

```yaml
canonical_id: trace_id
disposition: compatible
```

### Adapter-required compatibility

```yaml
canonical_id: trace_id
disposition: adapter-required
adapter_id: trace-relay-v0-9-to-authorization-v0-5
```

### Blocked compatibility

```yaml
canonical_id: execution_id
disposition: blocked
```

The current core registry explicitly blocks direct
Execution-to-Royalty use of `execution_id`.

```text
Execution ──X──→ Royalty
```

Royalty allocation must depend on audited evidence rather than raw execution
evidence.

```text
Execution → Audit → Royalty
```

## Protocol adapters

A registered adapter provides an explicit migration path between protocol
versions that are not directly compatible.

An adapter contract declares:

- adapter identity and version;
- source endpoint;
- target endpoint;
- canonical identifier;
- field transformations;
- lossiness;
- integrity behavior;
- lifecycle status.

Example:

```yaml
adapter_id: trace-relay-v0-9-to-authorization-v0-5
adapter_version: v0.1
status: active

source:
  stage: trace
  protocol_id: trace-relay-protocol
  version: v0.9
  record_type: trace_relay_record

target:
  stage: authorization
  protocol_id: agent-action-authorization-receipt-protocol
  version: v0.5
  record_type: action_authorization_receipt

canonical_id: trace_id

transforms:
  - operation: copy
    from_field: trace_record_id
    to_field: evidence_refs.trace_id
    required: true

lossiness: lossless
integrity_behavior: preserve
```

The profile must bind the adapter explicitly.

```yaml
adapter_bindings:
  - binding_id: legacy-trace-authorization-binding
    adapter_id: trace-relay-v0-9-to-authorization-v0-5
    adapter_version: v0.1
    source_stage: trace
    target_stage: authorization
    canonical_id: trace_id
```

Adapters are never inferred automatically.

An `adapter-required` connection without exactly one matching adapter binding
is invalid.

## Resolution receipts

Version 0.5 introduces the Interoperability Resolution Receipt.

The resolver combines:

```text
Interoperability Profile
        +
Canonical Identifier Registry
        +
Protocol Compatibility Registry
        +
Protocol Adapter Registry
        ↓
Interoperability Resolution Receipt
```

The receipt records:

- profile identifier;
- profile SHA-256 digest;
- registry identifiers and versions;
- registry SHA-256 digests;
- resolved six-stage protocol snapshot;
- resolved compatibility links;
- resolved adapter bindings;
- conformance state;
- handoff target;
- required downstream checks.

A resolution receipt proves which exact files and protocol versions were used
when the profile was resolved.

Changing a locked profile or registry changes its digest and invalidates the
existing receipt.

## Conformance handoff

A successfully resolved profile is handed off to:

```text
kazene-protocol-conformance-suite
```

The receipt requests downstream checks such as:

- schema validation;
- semantic validation;
- registry resolution;
- compatibility resolution;
- adapter resolution;
- digest verification;
- cross-protocol fixture validation;
- failure-propagation validation.

This repository establishes that a composition is structurally resolvable.

The conformance suite tests whether the composed protocols behave correctly
together.

## Validation model

Validation is divided into two layers.

### JSON Schema validation

Schema validation checks structural requirements such as:

- required properties;
- fixed versions;
- allowed values;
- field formats;
- six-stage tuple order;
- object shapes;
- unknown properties.

### Semantic validation

Semantic validation checks rules that JSON Schema alone cannot enforce, such
as:

- canonical identifier ownership;
- forward-only stage references;
- required lifecycle links;
- unique producers;
- registry-to-profile consistency;
- exact protocol compatibility;
- blocked-link rejection;
- adapter endpoint matching;
- missing adapter rejection;
- unused adapter rejection;
- lossiness policy;
- resolution policy;
- conformance handoff policy.

A YAML document may pass schema validation and still fail semantic
validation.

## Passing examples

### Core direct-compatibility profile

```text
examples/pass/civilization-os-interoperability-profile.example.yaml
```

This profile uses:

- Trace Relay Protocol `v1.0`;
- direct compatibility;
- no adapter binding;
- complete six-stage lifecycle;
- resolution-receipt handoff.

### Adapter-mediated profile

```text
examples/pass/adapter-mediated-profile.example.yaml
```

This profile uses:

- Trace Relay Protocol `v0.9`;
- an `adapter-required` compatibility contract;
- a registered lossless adapter;
- an explicit adapter binding.

## Expected-failure examples

| File | Expected failure |
|---|---|
| `blocked-audit-bypass.example.yaml` | Blocked Execution-to-Royalty link |
| `future-stage-reference.example.yaml` | Authorization consumes a future `audit_id` |
| `missing-required-adapter.example.yaml` | Required adapter binding is absent |
| `unregistered-identifier.example.yaml` | Origin produces unregistered `policy_id` |

Failure examples are considered successful tests when the validator rejects
them for the intended reason.

## Repository structure

```text
.
├── .github/
│   └── workflows/
│       └── validate.yml
├── build/
│   └── resolution/
├── examples/
│   ├── fail/
│   │   ├── blocked-audit-bypass.example.yaml
│   │   ├── future-stage-reference.example.yaml
│   │   ├── missing-required-adapter.example.yaml
│   │   └── unregistered-identifier.example.yaml
│   └── pass/
│       ├── adapter-mediated-profile.example.yaml
│       └── civilization-os-interoperability-profile.example.yaml
├── registry/
│   ├── canonical-identifiers.yaml
│   ├── protocol-adapters.yaml
│   └── protocol-compatibility.yaml
├── schemas/
│   ├── canonical-identifier-registry.schema.json
│   ├── civilization-os-interoperability-profile.schema.json
│   ├── interoperability-resolution-receipt.schema.json
│   ├── protocol-adapter-registry.schema.json
│   └── protocol-compatibility-registry.schema.json
├── scripts/
│   ├── generate_resolution_receipt.py
│   ├── validate_examples.py
│   └── validate_resolution_receipt.py
├── specification/
│   └── civilization-os-interoperability-profile.md
├── .gitignore
├── CHANGELOG.md
├── README.md
└── requirements.txt
```

The `build/` directory is generated and should not be committed unless a
release process explicitly requires committed receipts.

## Installation

Python 3.12 or later is recommended.

Install dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Validate registries and examples

Run:

```bash
python scripts/validate_examples.py
```

The validator checks:

1. Canonical Identifier Registry;
2. Protocol Adapter Registry;
3. Protocol Compatibility Registry;
4. passing profile examples;
5. expected-failure profile examples.

A successful run ends with:

```text
All registries and interoperability profile examples behaved as expected.
```

## Generate a resolution receipt

Generate the default core receipt:

```bash
python scripts/generate_resolution_receipt.py
```

Or specify the input profile and output path:

```bash
python scripts/generate_resolution_receipt.py \
  examples/pass/civilization-os-interoperability-profile.example.yaml \
  build/resolution/kazene-core-lifecycle.resolution.yaml
```

The generator validates the repository before producing the receipt unless
the validation step is explicitly skipped.

```bash
python scripts/generate_resolution_receipt.py \
  examples/pass/civilization-os-interoperability-profile.example.yaml \
  build/resolution/kazene-core-lifecycle.resolution.yaml \
  --skip-repository-validation
```

Use the skip option only when validation has already run successfully in the
same workflow.

## Validate a resolution receipt

Run:

```bash
python scripts/validate_resolution_receipt.py \
  build/resolution/kazene-core-lifecycle.resolution.yaml
```

The receipt validator checks:

- receipt schema;
- profile digest;
- registry digests;
- registry references;
- profile identity;
- registry identity and version;
- resolved stage snapshot;
- resolved compatibility links;
- adapter-binding resolution;
- conformance handoff policy.

A successful result ends with:

```text
[schema-ok]
[semantic-ok]
[digest-lock-ok]
[conformance-handoff-ready] kazene-protocol-conformance-suite
```

## GitHub Actions

The validation workflow performs:

1. repository checkout;
2. Python setup;
3. dependency installation;
4. registry and example validation;
5. resolution receipt generation;
6. resolution receipt validation;
7. receipt artifact upload.

Generated receipts are stored as workflow artifacts for downstream
conformance testing.

## Conformance requirements

A v0.5 profile must declare:

```yaml
conformance:
  require_ordered_execution: true
  require_reference_resolution: true
  require_registry_resolution: true
  require_registered_identifiers: true
  require_unique_contract_producers: true
  require_compatibility_resolution: true
  require_exact_protocol_versions: true
  reject_blocked_compatibility: true
  require_adapter_resolution: true
  reject_unbound_adapters: true
  reject_lossy_adapters: true
  require_resolution_receipt: true
  require_digest_lock: true
  require_conformance_handoff: true
  reject_unknown_stages: true
  allow_optional_profiles: false
```

The current core profile rejects non-lossless adapters.

Other future profiles may set:

```yaml
reject_lossy_adapters: false
```

Such a profile must still resolve the adapter explicitly and remain subject to
downstream conformance testing.

## Resolution policy

Every v0.5 profile must declare:

```yaml
resolution_policy:
  require_resolution_receipt: true
  require_digest_lock: true
  require_exact_stage_snapshot: true
  require_conformance_handoff: true
  handoff_target: kazene-protocol-conformance-suite
```

This ensures that an approved profile cannot silently drift after resolution.

## Design principles

### Independent versioning

Protocols and registries remain independently versioned.

### Explicit composition

Every protocol, version, record type, and identifier link is declared.

### Forward-only causality

A stage may consume identifiers only from earlier stages.

### Canonical identity

Cross-protocol references use stable canonical identifiers.

### Explicit compatibility

No connection is assumed merely because field names look similar.

### Registered migration

Version migration requires a named and registered adapter.

### Audit before allocation

Raw execution evidence must not bypass audit before value distribution.

### Digest-locked resolution

Resolved compositions are bound to exact file contents.

### Machine-verifiable handoff

A resolved profile produces structured evidence for downstream conformance
testing.

## Non-goals

Version 0.5 does not define:

- execution of referenced protocols;
- network transport;
- protocol package downloading;
- remote schema fetching;
- distributed registry discovery;
- cryptographic signing of receipts;
- runtime scheduling;
- rollback and compensation;
- parallel lifecycle branches;
- optional stage omission;
- settlement execution;
- payment-network integration.

These capabilities belong to later protocol layers or separate repositories.

## Security considerations

Implementations should treat profile and registry files as governance inputs.

A production implementation should additionally consider:

- signed registries;
- signed release tags;
- trusted repository allowlists;
- immutable artifact storage;
- digest verification before execution;
- protection against path traversal;
- adapter-code review;
- schema supply-chain verification;
- revocation of compromised compatibility links;
- conformance-suite isolation.

The current reference scripts protect local repository references from
escaping the repository root.

## Status

The project is experimental.

Version `v0.5.0` completes the first interoperability lifecycle:

```text
Ordered composition
  ↓
Canonical identifier contracts
  ↓
Protocol compatibility
  ↓
Adapter-mediated migration
  ↓
Digest-locked resolution receipt
  ↓
Conformance-suite handoff
```

The next major layer is not another larger integration schema.

It is the independent conformance suite that verifies the composed lifecycle
as a working system.
