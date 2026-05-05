package main

# List of allowed image prefixes
allowed_registries := [
    "ghcr.io/ethio-connect-et/",
    "quay.io/keycloak/",
    "postgres",
    "redis"
]

deny[msg] {
  input.kind == "Deployment"
  container := input.spec.template.spec.containers[_]
  not is_allowed_registry(container.image)
  msg := sprintf("Container '%s' uses disallowed registry in image '%s'", [container.name, container.image])
}

deny[msg] {
  input.kind == "Deployment"
  container := input.spec.template.spec.containers[_]
  not contains(container.image, "@sha256:")
  msg := sprintf("Container '%s' must use a sha256 digest reference, found '%s'", [container.name, container.image])
}

# Mandatory domain-scoped rollout-policy annotation
deny[msg] {
  input.kind == "Deployment"
  not has_rollout_policy_annotation(input.metadata.annotations)
  msg := sprintf("Deployment '%s' is missing mandatory domain-scoped rollout-policy annotation (e.g. ethio-connect.et/rollout-policy)", [input.metadata.name])
}

# Mandatory domain-scoped baremetal-max-unavailable annotation
deny[msg] {
  input.kind == "Deployment"
  not has_baremetal_annotation(input.metadata.annotations)
  msg := sprintf("Deployment '%s' is missing mandatory domain-scoped baremetal-max-unavailable annotation", [input.metadata.name])
}

# Mandatory maxUnavailable in strategy
deny[msg] {
  input.kind == "Deployment"
  not input.spec.strategy.rollingUpdate.maxUnavailable
  msg := sprintf("Deployment '%s' is missing spec.strategy.rollingUpdate.maxUnavailable", [input.metadata.name])
}

is_allowed_registry(image) {
  registry := allowed_registries[_]
  startswith(image, registry)
}

has_rollout_policy_annotation(annotations) {
  annotations[key]
  contains(key, "/rollout-policy")
}

has_baremetal_annotation(annotations) {
  annotations[key]
  contains(key, "/baremetal-max-unavailable")
}
