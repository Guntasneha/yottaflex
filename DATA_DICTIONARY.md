# Data dictionary

All IDs are immutable strings and primary keys unless noted. CSV field `required` means non-null in baseline data; anomaly rows are isolated in `issues.csv`. Dates use ISO `YYYY-MM-DD`; timestamps use UTC ISO 8601. Synthetic names are placeholders.

| Entity / field | Type | Req. | Allowed / unit | Unique | Validation |
|---|---|---:|---|---|---|
| Student `student_id` | string | yes | `STU-######` | PK | deterministic counter |
| `given_name`, `family_name` | string | yes | synthetic tokens | no | nonempty |
| `zone_id` | string | yes | AddressZone FK | no | parent exists |
| `address_label` | string | yes | synthetic zone/block token | no | no street address; approved-zone lookup required |
| `wheelchair_required` | boolean | yes | true/false | no | accessible bus needed if true |
| `lifecycle_state` | enum | yes | active/inactive | no | declared lifecycle |
| GuardianContact `contact_id` | string | yes | `GUA-######` | PK | deterministic |
| `student_id` | string | yes | Student FK | unique | one contact per student in this cohort |
| `phone` | string | yes | fictional 555-01xx | unique | reserved synthetic range |
| `email` | string | yes | example.invalid | unique | synthetic domain only |
| `valid` | boolean | yes | true/false | no | false only in issue fixture |
| AddressZone `zone_id` | string | yes | `ZONE-###` | PK | deterministic |
| `zone_name` | string | yes | synthetic zone label | yes | nonempty |
| `lifecycle_state` | enum | yes | active/inactive | no | declared lifecycle |
| Stop `stop_id` | string | yes | `STOP-######` | PK | deterministic |
| `zone_id` | string | yes | AddressZone FK | no | parent exists |
| `stop_name` | string | yes | synthetic label | no | nonempty |
| `approved` | boolean | yes | true/false | no | assignments require true |
| `accessible` | boolean | yes | true/false | no | compatible with student need |
| `latitude`, `longitude` | decimal | yes | synthetic coordinate degrees | no | bounded; not geocoded |
| Bus `bus_id` | string | yes | `BUS-######` | PK | deterministic |
| `capacity` | integer | yes | seats, >0 | no | base capacity; changes in event table |
| `accessible` | boolean | yes | true/false | no | wheelchair compatibility |
| `lifecycle_state` | enum | yes | active/inactive | no | declared lifecycle |
| Driver `driver_id` | string | yes | `DRV-######` | PK | deterministic |
| `display_name` | string | yes | synthetic token | no | nonempty |
| `license_class` | enum | yes | standard/accessible | no | accessible routes require accessible qualified driver |
| `lifecycle_state` | enum | yes | active/inactive | no | declared lifecycle |
| CapacityChange `change_id` | string | yes | `CAP-######` | PK | deterministic |
| `bus_id` | string | yes | Bus FK | no | parent exists |
| `effective_date` | date | yes | school calendar | no | after bus creation |
| `capacity` | integer | yes | seats, >0 | no | effective capacity snapshot |
| Route `route_id` | string | yes | `ROUTE-2026-######` | PK | deterministic |
| `bus_id`, `driver_id` | string | yes | Bus/Driver FK | no | parent exists, active |
| `service_date` | date | yes | school calendar | no | valid date |
| `status` | enum | yes | candidate/planned/active/completed/cancelled | no | declared transition |
| RouteStop `route_stop_id` | string | yes | `RST-######` | PK | deterministic |
| `route_id`, `stop_id` | string | yes | Route/Stop FK | pair unique | parent exists |
| `sequence_no` | integer | yes | 1..N | route+sequence unique | increasing |
| `arrival_minute` | integer | yes | minutes after midnight | no | >= previous arrival + travel + dwell |
| `travel_from_previous_min` | integer | yes | minutes, >=0 | no | synthetic travel estimate |
| `dwell_min` | integer | yes | minutes, >=0 | no | synthetic operational assumption |
| Assignment `assignment_id` | string | yes | `ASN-<student-id>-2026` | PK | deterministic one per student/year |
| `student_id`, `route_id`, `stop_id` | string | yes | respective FK | no | all parents exist |
| `effective_start`, `effective_end` | date | yes/no | ISO date | no | start <= end; end can be null |
| `status` | enum | yes | active/suspended/ended | no | active assignments meet safety/capacity rules |
| AttendanceEvent `attendance_id` | string | yes | `ATT-##########` | PK | deterministic sequence |
| `student_id`, `service_date` | string/date | yes | Student FK/calendar | no | one event per assigned student/day |
| `route_id` | string | no | Route FK/null | no | null if no service |
| `status` | enum | yes | present/absent/late/missed_pickup/service_disrupted | no | derived from seed policy and disruption |
| `ground_truth_issue` | string | no | null/issue code | no | null in ordinary records; scoring only |
| Notification `notification_id` | string | yes | `NOT-2026-######` | PK | deterministic |
| `student_id`, `contact_id` | string | yes | Student/GuardianContact FK | no | contact must be valid to send |
| `attendance_id` | string | yes | AttendanceEvent FK | no | event exists |
| `channel` | enum | yes | sms/email | no | synthetic channel |
| `status` | enum | yes | sent/suppressed | no | sent requires valid contact |
| `created_at` | timestamp | yes | UTC | no | after event date start |
| `message_code` | enum | yes | absence/missed_pickup/disruption | no | no sensitive message body |
| RouteDisruption `disruption_id` | string | yes | `DIS-######` | PK | deterministic |
| `route_id` | string | yes | Route FK | no | parent exists |
| `service_date` | date | yes | calendar | no | route date |
| `reason` | enum | yes | vehicle/road/weather | no | synthetic reason |
| `status` | enum | yes | delayed/cancelled | no | explicit disruption event |
| Issue `issue_id` | string | yes | `ISSUE-###` | PK | deterministic |
| `issue_type` | enum | yes | five challenge anomaly labels | no | one known fixture per required case |
| `entity_id` | string | yes | referenced entity ID | no | expected detector and decision documented |
| `expected_decision` | string | yes | rule action | no | fixed documented rule |
