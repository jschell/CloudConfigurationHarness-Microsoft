# Reusable patterns

Lessons and conventions that apply beyond the specific check/resource
type they were discovered on. When something is learned the hard way
during this harness's work, it gets written here so the next session
(or the next resource type) doesn't have to rediscover it.

- [schema-coverage-discovery.md](schema-coverage-discovery.md) --
  deterministically enumerate every property on a resource, classify
  each for relevance in small batches, and track completeness in a
  ledger, instead of relying on curated doc excerpts and LLM judgment
  alone to decide what to propose and know when to stop.
- [rego-rule-authoring.md](rego-rule-authoring.md) -- prefer denying on
  the negation of a property's safe value over matching one named risky
  value, whenever the property can hold more than two states. Equality
  against a single risky value only ever catches that one value.
- [deterministic-check-id-assignment.md](deterministic-check-id-assignment.md)
  -- never ask a stateless model call to invent an identifier whose
  uniqueness matters (check_ids, package names); assign it in code
  instead. A model-invented check_id collided and silently overwrote
  three already-validated rules before this fix.
