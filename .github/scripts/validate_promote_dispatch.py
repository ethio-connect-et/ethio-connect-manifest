#!/usr/bin/env python3
import json, os, re, sys

def fail(msg):
    print(msg)
    sys.exit(1)

event_path = os.environ.get("GITHUB_EVENT_PATH")
if not event_path or not os.path.exists(event_path):
    fail("Missing GITHUB_EVENT_PATH for dispatch validation")

with open(event_path, encoding="utf-8") as f:
    event = json.load(f)
with open(".github/schemas/promote-image-dispatch.schema.json", encoding="utf-8") as f:
    schema = json.load(f)

if event.get("action") != schema["properties"]["event_type"]["const"]:
    fail("event_type must be 'promote-image'")

payload = event.get("client_payload")
if not isinstance(payload, dict):
    fail("client_payload must be an object")

props = schema["properties"]["client_payload"]["properties"]
for key in schema["properties"]["client_payload"]["required"]:
    if key not in payload:
        fail(f"client_payload missing required field: {key}")

for field, rules in props.items():
    value = payload.get(field)
    if rules.get("type") == "string" and not isinstance(value, str):
        fail(f"client_payload.{field} must be a string")
    if "minLength" in rules and len(value) < rules["minLength"]:
        fail(f"client_payload.{field} must be non-empty")
    if "const" in rules and value != rules["const"]:
        fail(f"client_payload.{field} must equal '{rules['const']}'")
    if "enum" in rules and value not in rules["enum"]:
        fail(f"client_payload.{field} must be one of {','.join(rules['enum'])}")
    if "pattern" in rules and not re.match(rules["pattern"], value):
        fail(f"client_payload.{field} failed pattern check")

expected_ref = {"testing": "refs/heads/testing", "staging": "refs/heads/staging", "production": "refs/heads/main"}[payload["env"]]
if payload["source_ref"] != expected_ref:
    fail(f"client_payload.source_ref '{payload['source_ref']}' does not match env policy for '{payload['env']}' (expected '{expected_ref}')")

print("repository_dispatch payload validation passed")
