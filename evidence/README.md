Evidence Bundle v0 (Contract)



Purpose

Every Brain output must include an Evidence Bundle. The Evidence Bundle is an auditable packet that explains:

\- what data was used

\- what models were called

\- what calculations were performed

\- what KB rules were applied

\- what assumptions were made

\- what is missing / uncertain



If evidence is insufficient, the Brain must lower confidence or refuse to answer.





Evidence Bundle (v0) – Fields



1\) Summary

\- `evidence\_id`: unique id (string)

\- `generated\_at`: timestamp

\- `question`: original user/system question

\- `intent`: resolved intent name (e.g., `soh\_trend`, `anomaly\_scan`)

\- `role`: target audience (optional; e.g., `ops`, `asset\_manager`, `cfo`)



2\) Data Used

A list of all data pulls made by adapters.



Each entry:

\- `source\_type`: `telemetry` | `market` | `kb` | `synthetic`

\- `source\_name`: adapter/provider name (e.g., `synthetic\_v0`, `bms\_api\_vendor\_x`)

\- `query`: what was requested (asset\_id, signals, market, etc.)

\- `time\_window`: start/end

\- `row\_count`: how much data returned

\- `quality\_notes`: missingness, gaps, outliers, stale data



3\) Computations Performed

A list of deterministic operations performed on data.



Each entry:

\- `name`: e.g., `rolling\_mean`, `slope\_estimate`, `revenue\_at\_risk`

\- `inputs`: which signals/fields were used

\- `method`: short description of formula/approach

\- `outputs`: key computed values

\- `assumptions\_refs`: references into the Assumption Registry (KB)



4\) Model Calls (Optional)

If any model adapter was invoked.



Each entry:

\- `model\_name`

\- `model\_version` (if available)

\- `inputs\_summary` (not raw full payload)

\- `outputs\_summary`

\- `model\_confidence` (if provided)

\- `limitations`



5\) Knowledge Base Rules Applied

List KB artifacts that shaped the answer.



Each entry:

\- `kb\_ref`: path or id (e.g., `thresholds/bess\_temp.md#high\_temp`)

\- `rule\_summary`: what it enforced

\- `impact\_on\_answer`: why it mattered



6\) Assumptions \& Gaps

\- `assumptions`: list of assumption refs + plain-English description

\- `gaps`: what we could not know / missing data / missing context

\- `risk\_notes`: why the gaps matter



7\) Attachments (Optional)

\- `charts`: list of chart payload references (ids or filenames)

\- `tables`: list of table payload references

\- `links`: internal links (avoid external for now)





Minimal Example (v0)



```json

{

&nbsp; "evidence\_id": "ev\_2025-12-14T00:35:12Z\_001",

&nbsp; "generated\_at": "2025-12-14T00:35:12Z",

&nbsp; "question": "Is Rack-12 degrading faster than last week?",

&nbsp; "intent": "soh\_trend\_compare",

&nbsp; "role": "asset\_manager",

&nbsp; "data\_used": \[

&nbsp;   {

&nbsp;     "source\_type": "telemetry",

&nbsp;     "source\_name": "synthetic\_v0",

&nbsp;     "query": { "asset\_id": "rack\_12", "signals": \["soh"], "granularity": "15m" },

&nbsp;     "time\_window": { "start": "2025-12-01T00:00:00Z", "end": "2025-12-14T00:00:00Z" },

&nbsp;     "row\_count": 1344,

&nbsp;     "quality\_notes": "2% missing points; no major gaps > 1h"

&nbsp;   }

&nbsp; ],

&nbsp; "computations": \[

&nbsp;   {

&nbsp;     "name": "slope\_estimate",

&nbsp;     "inputs": \["soh"],

&nbsp;     "method": "Linear regression slope over 7d windows (week1 vs week2)",

&nbsp;     "outputs": { "week1\_slope": -0.0012, "week2\_slope": -0.0021, "delta": -0.0009 },

&nbsp;     "assumptions\_refs": \["ASSUMP\_SOH\_IS\_VALID\_PROXY\_V0"]

&nbsp;   }

&nbsp; ],

&nbsp; "model\_calls": \[],

&nbsp; "kb\_rules\_applied": \[

&nbsp;   {

&nbsp;     "kb\_ref": "knowledge\_base/thresholds/soh.md#drift\_alert",

&nbsp;     "rule\_summary": "Flag if weekly SoH slope worsens beyond threshold",

&nbsp;     "impact\_on\_answer": "Marked as 'Watch' not 'Critical' due to limited horizon"

&nbsp;   }

&nbsp; ],

&nbsp; "assumptions\_and\_gaps": {

&nbsp;   "assumptions": \[

&nbsp;     { "ref": "ASSUMP\_SOH\_IS\_VALID\_PROXY\_V0", "description": "SoH provided is comparable week-to-week." }

&nbsp;   ],

&nbsp;   "gaps": \[

&nbsp;     "No maintenance events available for Rack-12 in this window."

&nbsp;   ],

&nbsp;   "risk\_notes": "If a recalibration happened, week-to-week slope comparison may be misleading."

&nbsp; },

&nbsp; "attachments": {

&nbsp;   "charts": \["chart\_soh\_rack12\_2025-12-01\_2025-12-14"],

&nbsp;   "tables": \["table\_soh\_week\_compare\_rack12"]

&nbsp; }

}



