# Blameless postmortem template

Status: TEMPLATE — not evidence of a real operational incident.

Incident ID / signal:
Severity:
Author / reviewers:
Start / detection / mitigation / fresh successful probe / resolved times (timezone):
Observation window and detector configuration:

## Impact

Affected endpoint templates, request denominator, errors, latency distribution and synthetic attendee impact. Distinguish HTTP failures from slow successful responses. State what cannot be measured.

## Timeline

| Timestamp | Observation or action | Evidence |
|---|---|---|
| Fill in | Trigger and independent fault schedule | Log, metric or scenario ID |

## Contributing factors

Describe system and process factors without assigning blame. Separate confirmed evidence from hypotheses. Note whether the database failure was simulated or actual.

## Detection and response

Which detector fired? How was it grouped? What was missed? What fresh evidence demonstrated recovery? Did no traffic merely clear the predicate?

## Actions

| Action | Owner | Due date | Verification |
|---|---|---|---|
| Fill in | Assign explicitly | Set explicitly | Measurable check |

## Lessons

What helped, what delayed investigation, and what changes should be tested next? Synthetic experiment results do not establish production savings.
