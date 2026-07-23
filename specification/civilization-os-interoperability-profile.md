# Civilization OS Interoperability Profile Specification

Version: 0.1.0  
Status: Draft

## 1. Purpose

The Civilization OS Interoperability Profile defines how independent
Civilization OS protocols are connected without merging their internal
schemas or implementations.

The profile specifies:

1. which protocol is assigned to each lifecycle stage;
2. the order in which the stages are connected;
3. the canonical identifiers passed between stages;
4. the local fields used by each protocol;
5. the minimum rules required for interoperability.

This specification is a coordination layer.

It does not replace the protocols that it references.

## 2. Design principle

A Civilization OS implementation SHOULD preserve the independence of
each protocol.

The interoperability profile MUST describe connections between
protocols rather than copying all protocol definitions into one
monolithic schema.

A profile acts as a nervous system connecting existing organs.

## 3. Standard lifecycle

Version 0.1 defines the following mandatory lifecycle order:

1. Origin
2. Trace
3. Authorization
4. Execution
5. Audit
6. Royalty

The order MUST NOT be changed in a conforming v0.1 profile.

```text
Origin
  |
  v
Trace
  |
  v
Authorization
  |
  v
Execution
  |
  v
Audit
  |
  v
Royalty
4. Profile binding

Each lifecycle stage MUST contain a profile binding.

A profile binding identifies:

the stage name;
the stage position;
the external protocol;
the protocol version;
the repository containing the protocol;
the referenced schema;
the record type;
the canonical identifiers consumed;
the canonical identifiers produced.

A protocol MAY be used by more than one stage when it defines more than
one relevant record type.

For example, the Authorization and Execution stages MAY reference
different schemas from the same repository.

5. Canonical identifiers

A canonical identifier provides a protocol-independent name for a
cross-protocol reference.

Version 0.1 defines the following minimum identifiers:

Stage	Required output
Origin	origin_id
Trace	trace_id
Authorization	authorization_receipt_id
Execution	execution_id
Audit	audit_id
Royalty	allocation_id

Canonical identifiers do not require every protocol to use identical
field names.

The local_field property maps a canonical identifier to the field
used by the referenced protocol.

Example:

produces:
  - canonical_id: authorization_receipt_id
    local_field: authorization_receipt_id

Another protocol may consume the same identifier through a differently
named field:

consumes:
  - canonical_id: authorization_receipt_id
    from_stage: authorization
    local_field: authorization_receipt_ref
    required: true
6. Required lifecycle links

A conforming v0.1 profile MUST include at least the following links:

Consumer stage	Source stage	Canonical identifier
Trace	Origin	origin_id
Authorization	Trace	trace_id
Execution	Authorization	authorization_receipt_id
Audit	Execution	execution_id
Royalty	Audit	audit_id

Additional links MAY be defined.

For example, Royalty MAY also consume origin_id directly from the
Origin stage.

7. Reference direction

A stage MUST consume identifiers only from an earlier stage.

A stage MUST NOT reference an identifier produced by itself or by a
later stage.

The following connection is invalid:

Authorization
    |
    | consumes audit_id
    v
Audit

At the time Authorization is evaluated, audit_id does not yet exist.

This rule prevents circular dependencies and future-stage references.

8. Identifier production

Each canonical identifier MUST have no more than one producer within a
profile.

Multiple stages MUST NOT claim to produce the same canonical
identifier.

A consuming stage MUST reference the stage that actually produces the
identifier.

9. Conformance

A v0.1 conforming profile MUST:

use schema version 0.1.0;
use profile kind
civilization-os-interoperability-profile;
contain all six lifecycle stages;
preserve the standard lifecycle order;
define the required canonical outputs;
define the required lifecycle links;
resolve every consumed identifier to an earlier producer;
reject unknown lifecycle stages;
declare whether optional profile behavior is permitted.

Schema validation alone is not sufficient.

Implementations MUST also perform semantic validation of stage order
and identifier references.

10. Non-goals

Version 0.1 does not define:

protocol execution;
network transport;
cryptographic signatures;
distributed identifier resolution;
protocol discovery;
schema downloading;
runtime orchestration;
rollback behavior;
branch or parallel lifecycle paths.

These capabilities may be introduced in later versions.

11. Versioning

The profile schema and semantic rules are versioned independently from
the protocols referenced by a profile.

Updating an external protocol version does not automatically change the
interoperability profile version.

A profile revision SHOULD be created when an external protocol update
changes:

a referenced schema;
a record type;
a local identifier field;
a required lifecycle dependency;
the meaning of a canonical identifier.
