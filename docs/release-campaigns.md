# Release Campaigns

Open `/workspace/campaigns` to group required environment/scenario slots into a deterministic release decision. Drafts may contain missing slots and report INCOMPLETE. Finalization is allowed only when every slot references a persisted run.

Readiness precedence is FAIL, INCOMPLETE, ADVISORY, then PASS. Different policy identities, baseline identities, or a baseline older than 30 days produce advisory drift unless a stronger status applies. Finalized campaign JSON uses schema `performance-campaign/v1` and a stable SHA-256 identity; Markdown carries the same readiness and slot results.

## Draft concurrency

Campaign repository updates accept the exact persisted `updated` token. A stale update returns `CAMPAIGN_CHANGED`; finalized campaigns return `CAMPAIGN_FINALIZED`. Draft updates replace the ordered slot set transactionally and validate run environment and sample eligibility.
