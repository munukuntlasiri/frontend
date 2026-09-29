# CivicResolve AI API Contract

This is the integration boundary between the Member 1 intelligence service and the Member 2 FastAPI/PostgreSQL/PostGIS backend. Examples are illustrative; model scores depend on the supplied evidence.

## Service Boundary

- Local base URL: `http://127.0.0.1:8000`
- OpenAPI/Swagger: `http://127.0.0.1:8000/docs`
- JSON endpoints use `application/json`; image endpoints use `multipart/form-data`.
- Datetimes must be ISO 8601 values with a timezone, preferably UTC (`Z`).
- Member 1 performs stateless analysis and returns recommendations.
- Member 2 owns authentication, persistence, candidate retrieval, scheduling, notifications, and issue-state changes.

## Common Errors

| Status | Meaning |
|---|---|
| `400` | Empty/corrupt evidence or an unsupported resolution target. |
| `413` | An image exceeds the configured per-file limit. |
| `415` | The declared or decoded image is not JPEG, PNG, or WebP. |
| `422` | FastAPI/Pydantic request validation failed; inspect `detail`. |
| `503` | Local SigLIP loading or inference failed. |
| `500` | An unexpected server failure. Normal API responses do not expose stack traces. |

## `GET /health`

**Purpose:** Lightweight availability check. It never initializes SigLIP.

**Content type:** No request body; response is `application/json`.

**Ownership:** Member 1 owns the returned metadata. **Logic:** Static and deterministic.

```http
GET /health HTTP/1.1
Host: 127.0.0.1:8000
```

Response fields are `status` (string), `service` (string), and `version` (string).

```json
{"status":"healthy","service":"CivicResolve AI","version":"0.1.0"}
```

**Important errors:** Only an unexpected service failure should produce `500`.

## `POST /analyze`

**Purpose:** Classify complaint text, calculate priority, and route the issue.

**Content type:** `application/json`.

**Ownership:** Member 2 supplies the citizen report received from Member 3. Member 1 owns the derived result. **Logic:** Deterministic keyword/rule based; no model call.

### Request fields

| Field | Type | Required | Validation |
|---|---|---|---|
| `description` | string | yes | 1-5,000 characters after trimming. |
| `latitude` | number/null | no | `-90` to `90`. |
| `longitude` | number/null | no | `-180` to `180`. |
| `citizen_count` | integer | no | Default `1`; minimum `1`. |

```json
{
  "description": "Large pothole on the main road may cause an accident.",
  "latitude": 17.385,
  "longitude": 78.4867,
  "citizen_count": 3
}
```

### Response fields

`category`, `issue`, `severity`, deterministic `confidence`, `confidence_basis`, `risk`, `priority`, `priority_score`, `department`, `duplicate_probability`, `classification_reasons`, and `priority_reasons`. `duplicate_probability` is `null`; duplicate evaluation is separate.

```json
{
  "category": "Road Damage",
  "issue": "Pothole",
  "severity": "High",
  "confidence": 0.65,
  "confidence_basis": "deterministic_rule_match",
  "risk": "Accident Risk",
  "priority": "High",
  "priority_score": 83,
  "department": "Road Maintenance Department",
  "duplicate_probability": null,
  "classification_reasons": ["Matched Pothole indicator(s): pothole."],
  "priority_reasons": ["Final score 83/100 maps to High priority."]
}
```

**Important errors:** `422` for a missing/blank description, invalid coordinates, or `citizen_count < 1`.

## `POST /classify-image`

**Purpose:** Classify one photograph against supported civic and control prompt groups.

**Content type:** `multipart/form-data`.

**Ownership:** Member 2 supplies the stored/new citizen image. Member 1 owns derived visual evidence. **Logic:** Local SigLIP model inference plus deterministic aggregation and rejection gates.

### Request fields

| Field | Type | Required | Validation |
|---|---|---|---|
| `file` | binary file | yes | JPEG, PNG, or WebP; configured size limit. |

```powershell
curl.exe -X POST "http://127.0.0.1:8000/classify-image" -F "file=@sample_images/pothole.jpg;type=image/jpeg"
```

### Response fields

`detected`, nullable backward-compatible `category` and `issue`, nullable `taxonomy_category` and `taxonomy_issue`, nullable `relative_score`, `score_type`, `provider`, `model`, `device`, `image_width`, `image_height`, ranked `predictions`, `reasons`, and `limitations`. Each prediction contains both label sets, `relative_score`, and `top_prompt`.

The implemented taxonomy is:

| Taxonomy category | Issues |
|---|---|
| Road | Pothole; Cracked Road; Damaged Pavement; Broken Footpath |
| Waste Management | Garbage Accumulation; Overflowing Bin; Illegal Dumping |
| Water | Water Leakage; Drainage Overflow; Waterlogging; Open Drain |
| Infrastructure | Broken Streetlight; Damaged Public Infrastructure; Broken Traffic-related Infrastructure |

The model and prompt architecture support all 14. Water Leakage and Broken Streetlight retain previously validated prompt sets. Road, waste, and drainage sibling prompts were recalibrated and require fresh representative-image validation; all other expanded classes remain provisional pending broader evaluation.

```json
{
  "detected": true,
  "category": "Road Damage",
  "issue": "Pothole",
  "taxonomy_category": "Road",
  "taxonomy_issue": "Pothole",
  "relative_score": 0.4508,
  "score_type": "relative_zero_shot_prompt_score",
  "provider": "siglip_local",
  "model": "google/siglip-base-patch16-224",
  "device": "cpu",
  "image_width": 640,
  "image_height": 480,
  "predictions": [{"category":"Road Damage","issue":"Pothole","taxonomy_category":"Road","taxonomy_issue":"Pothole","relative_score":0.4508,"top_prompt":"a photo of a pothole in a road"}],
  "reasons": ["All provisional MVP detection gates passed; broader calibration is required."],
  "limitations": ["Scores are relative prompt-match scores, not calibrated probabilities."]
}
```

**Important errors:** `400` corrupt/empty image, `413` oversized image, `415` unsupported or mismatched media type, `422` missing file, `503` model failure.

## `POST /duplicate-check`

**Purpose:** Compare a new report with candidate Master Issues selected by Member 2.

**Content type:** `application/json`.

**Ownership:** Member 2 owns candidate retrieval, candidate data, and persisted associations. Member 1 owns the comparison. **Logic:** Deterministic text, location, and label fusion; scores are not calibrated probabilities. Image similarity is `null`.

### Request fields

| Field | Type | Required | Validation |
|---|---|---|---|
| `new_report` | object | yes | Same contract as `/analyze`. |
| `candidates` | array | yes | May be empty; Member 2 supplies a relevant shortlist. |
| `candidates[].issue_id` | string | yes | 1-200 characters. |
| `candidates[].description` | string | yes | 1-5,000 characters. |
| `candidates[].category` | string/null | no | Existing normalized category. |
| `candidates[].issue` | string/null | no | Existing normalized issue. |
| `candidates[].latitude` | number/null | no | `-90` to `90`. |
| `candidates[].longitude` | number/null | no | `-180` to `180`. |
| `candidates[].status` | string/null | no | Backend lifecycle status. |

```json
{
  "new_report": {"description":"Large pothole on the main road.","latitude":17.385,"longitude":78.4867,"citizen_count":1},
  "candidates": [{"issue_id":"MI-1024","description":"Large hole in road causing problems.","category":"Road Damage","issue":"Pothole","latitude":17.3852,"longitude":78.4867,"status":"Open"}]
}
```

### Response fields

`is_duplicate`, deterministic `duplicate_probability`, nullable `matched_issue_id`, nullable `best_match`, all `candidate_results`, `evaluated_candidates`, and `decision_reasons`. Each comparison contains `issue_id`, text/location scores, nullable distance, compatibility flags, nullable `image_similarity`, `fusion_score`, and reasons.

```json
{
  "is_duplicate": true,
  "duplicate_probability": 0.7831,
  "matched_issue_id": "MI-1024",
  "best_match": {"issue_id":"MI-1024","text_similarity":0.5889,"location_similarity":0.85,"distance_meters":22.24,"category_compatible":true,"issue_compatible":true,"image_similarity":null,"fusion_score":0.7831,"reasons":["Both reports describe Road Damage / Pothole."]},
  "candidate_results": [{"issue_id":"MI-1024","text_similarity":0.5889,"location_similarity":0.85,"distance_meters":22.24,"category_compatible":true,"issue_compatible":true,"image_similarity":null,"fusion_score":0.7831,"reasons":["Both reports describe Road Damage / Pothole."]}],
  "evaluated_candidates": 1,
  "decision_reasons": ["Score meets the duplicate threshold of 0.72, and compatibility and distance gates passed."]
}
```

**Important errors:** `422` for malformed reports, candidates, coordinates, or identifiers.

## `POST /follow-up`

**Purpose:** Recommend the next lifecycle action for one current issue snapshot.

**Content type:** `application/json`.

**Ownership:** Member 2 supplies authoritative state and executes/stores recommendations. Member 1 neither schedules calls nor sends notifications. **Logic:** Deterministic prototype SLA rules.

### Request fields

| Field | Type | Required | Validation |
|---|---|---|---|
| `issue_id` | string | yes | 1-200 characters. |
| `status` | string | yes | Current lifecycle status. |
| `priority` | string | yes | Critical, High, Medium, or Low; input is case-insensitive. |
| `assigned_at` | datetime/null | no | Timezone-aware ISO 8601. |
| `last_updated_at` | datetime/null | no | Timezone-aware; not before assignment. |
| `reminder_count` | integer | no | Default `0`; non-negative. |
| `escalation_count` | integer | no | Default `0`; non-negative. |
| `department` | string/null | no | Assigned department. |
| `citizen_count` | integer | no | Default `1`; minimum `1`. |
| `severity` | string/null | no | Current context. |
| `risk` | string/null | no | Current context. |
| `now` | datetime/null | no | Optional deterministic evaluation time; server UTC is used otherwise. |

```json
{
  "issue_id":"MI-1024","status":"Assigned","priority":"High",
  "assigned_at":"2026-01-15T02:00:00Z","last_updated_at":null,
  "reminder_count":0,"escalation_count":0,
  "department":"Road Maintenance Department","citizen_count":3,
  "severity":"High","risk":"Accident Risk","now":"2026-01-15T12:00:00Z"
}
```

### Response fields

`issue_id`, `action`, `urgency`, `should_notify`, nullable `target`, nullable elapsed-hour fields, `reasons`, and nullable `next_check_hours`. Actions: `NO_ACTION`, `REMINDER`, `ESCALATE`, `CRITICAL_ESCALATION`, `STOP_FOLLOWUP`.

```json
{
  "issue_id":"MI-1024","action":"REMINDER","urgency":"MEDIUM",
  "should_notify":true,"target":"Road Maintenance Department",
  "hours_since_assignment":10.0,"hours_since_last_update":null,
  "reasons":["Initial response SLA has been exceeded.","Recommended action: REMINDER."],
  "next_check_hours":2.0
}
```

**Important errors:** `422` for unsupported priority, naive/out-of-order timestamps, future timestamps relative to `now`, or negative counters.

## `POST /verify-resolution`

**Purpose:** Compare before/after photographs for one known visible civic issue.

**Content type:** `multipart/form-data`.

**Ownership:** Member 2 retrieves/supplies evidence and target labels, stores the result, manages citizen confirmation, and owns close/reopen decisions. Member 1 owns the comparison. **Logic:** Two local SigLIP inferences using the shared cached model, then deterministic evidence gates.

### Request fields

| Field | Type | Required | Validation |
|---|---|---|---|
| `before_file` | binary file | yes | JPEG, PNG, or WebP; configured size limit. |
| `after_file` | binary file | yes | JPEG, PNG, or WebP; configured size limit. |
| `category` | string | yes | Must match a supported pair below. |
| `issue` | string | yes | Must match a supported pair below. |
| `issue_id` | string | no | Backend ID echoed in the response. |

All 14 taxonomy pairs accepted by `/classify-image` can be supplied to this endpoint. Existing integration aliases remain accepted.

Automated `VERIFIED`/`UNSUCCESSFUL` decisions remain enabled only for the five previously validated visual types: Pothole, Garbage Accumulation, Water Leakage, Drainage Overflow, and Broken Streetlight. The other nine types always return `UNCERTAIN`, `requires_human_review: true`, and `HUMAN_REVIEW` until representative paired-image validation is completed. Text-only `Streetlight Failure` remains unsupported because ordinary photographs cannot verify electrical operation.

```powershell
curl.exe -X POST "http://127.0.0.1:8000/verify-resolution" -F "before_file=@sample_images/pothole.jpg;type=image/jpeg" -F "after_file=@sample_images/pothole_repaired.jpg;type=image/jpeg" -F "category=Road Damage" -F "issue=Pothole" -F "issue_id=MI-1024"
```

### Response fields

Nullable `issue_id`, `decision`, nullable `verification_score`, `score_type`, `before_evidence`, `after_evidence`, target scores, absolute/proportional reductions, `reasons`, `limitations`, `requires_human_review`, and `recommended_action`. Evidence contains backward-compatible labels, taxonomy labels, relative score, detection result, top prompt, and dimensions.

```json
{
  "issue_id":"MI-1024","decision":"VERIFIED","verification_score":0.88,
  "score_type":"relative_target_score_reduction_not_probability",
  "before_evidence":{"category":"Road Damage","issue":"Pothole","taxonomy_category":"Road","taxonomy_issue":"Pothole","relative_score":0.45,"detected":true,"top_prompt":"a photo of a pothole in a road","image_width":640,"image_height":480},
  "after_evidence":{"category":"Road Damage","issue":"Pothole","taxonomy_category":"Road","taxonomy_issue":"Pothole","relative_score":0.054,"detected":false,"top_prompt":"broken asphalt road surface","image_width":640,"image_height":480},
  "issue_score_before":0.45,"issue_score_after":0.054,
  "score_reduction":0.396,"score_reduction_ratio":0.88,
  "reasons":["Strong target-score reduction and normal-scene evidence passed all provisional verification gates."],
  "limitations":["A VERIFIED decision requests citizen confirmation and never closes an issue automatically."],
  "requires_human_review":false,"recommended_action":"REQUEST_CITIZEN_CONFIRMATION"
}
```

Decisions are `VERIFIED`, `UNSUCCESSFUL`, and `UNCERTAIN`; recommended actions are `REQUEST_CITIZEN_CONFIRMATION`, `KEEP_OPEN`, and `HUMAN_REVIEW`. **Important errors:** image errors listed for `/classify-image`, `400` unsupported category/issue pair, `422` missing fields.

## Integration Flow

```text
Citizen report:
Member 3 UI -> Member 2 Backend -> /analyze -> optional /classify-image
-> Member 2 retrieves candidate Master Issues -> /duplicate-check
-> Member 2 persists complaint/Master-Issue association

Lifecycle:
Member 2 scheduler/backend -> /follow-up -> Member 2 stores recommendation
-> Member 2 performs reminder/escalation

Resolution:
Member 2 retrieves before + after evidence -> /verify-resolution
-> Member 2 stores VERIFIED / UNSUCCESSFUL / UNCERTAIN
-> citizen confirmation/application workflow -> Member 2 closes/reopens issue
```

## Runtime Configuration

| Variable | Default | Purpose |
|---|---|---|
| `CIVICRESOLVE_CORS_ORIGINS` | `*` | Comma-separated browser origins. Use explicit origins when integrated. |
| `CIVICRESOLVE_SIGLIP_MODEL_ID` | `google/siglip-base-patch16-224` | Local Hugging Face model ID. |
| `CIVICRESOLVE_MAX_UPLOAD_MB` | `10` | Positive integer limit for each image. |

The service reads process environment variables and does not automatically load `.env`. No secret is required.
