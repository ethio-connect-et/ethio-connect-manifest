package main

deny[msg] {
  input.kind == "Deployment"
  container := input.spec.template.spec.containers[_]
  not startswith(container.image, "ghcr.io/ethio-connect-et/")
  msg := sprintf("Container '%s' uses disallowed registry in image '%s'", [container.name, container.image])
}

deny[msg] {
  input.kind == "Deployment"
  container := input.spec.template.spec.containers[_]
  not contains(container.image, "@sha256:")
  msg := sprintf("Container '%s' must use a sha256 digest reference, found '%s'", [container.name, container.image])
}
