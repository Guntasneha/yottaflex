# Schema, decisions and validation

## Entity relationships

- `AddressZone` 1:N `Student`; `AddressZone` 1:N `Stop`.
- `Student` 1:1 `GuardianContact` for this synthetic cohort. A contact is also referenced by many `Notification` events (1:N). Contact may be absent; notification then is not attempted.
- `Bus` 1:N `Route` over time; `Driver` 1:N `Route` over time. Bus and driver IDs are nullable on a proposed route but required for an active route.
- `Route` 1:N `RouteStop`; `Stop` 1:N `RouteStop`. This is the route-stop bridge, with unique `(route_id, sequence_no)` and `(route_id, stop_id)`.
- `Student` 1:N `Assignment` over effective periods; `Route` 1:N `Assignment`; `Stop` 1:N `Assignment`. One active assignment per student and date.
- `Student` 1:N `AttendanceEvent`; `Route` 1:N `AttendanceEvent` (nullable when no service). `AttendanceEvent` and `Notification` are append-only event history.
- `Bus` 1:N `CapacityChange`; `Route` 1:N `RouteDisruption`. These dated event tables preserve history.

## Lifecycle and policy

Master data lifecycle: `active`, `inactive`. Stops have `approved` or `pending` approval. Routes progress `candidate` → `planned` → `active` → `completed`, or `cancelled`; only planned/active routes receive assignments. Assignment states: `active`, `suspended`, `ended`; effective start must not follow end. Attendance states: `present`, `absent`, `late`, `missed_pickup`, `service_disrupted`. Notification statuses: `sent`, `suppressed`; only synthetic valid guardian contacts are eligible.

Baseline decisions: approved stop must match student's zone; wheelchair requirement implies accessible bus; assignment count on a route/day must be at most its effective bus capacity; route stop time must be at least the preceding travel time plus dwell; notification requires a present, valid contact. Absence suppresses pickup and emits no missed-pickup notification. A disrupted route emits `service_disrupted` events and guardian notices. Capacity and disruption are evaluated against dated changes, not current master values.

The explicit anomaly rows are labeled in `ground_truth.json` and `issues.csv`. They are separate from normal records. They intentionally exhibit the named condition; do not treat them as accepted baseline assignments or feature labels.

## Deterministic evaluation metrics

`validation_summary.json` reports record counts, baseline rule violations (expected zero), anomaly detections (expected five), and attendance/notification totals. Metrics are computed from generated records, not independently sampled. A deployment could extend this with route miles or on-time rates; this prototype does not claim road-network accuracy.
