# AURA — Technical Audit (Phase 1)

**Audited commit:** working tree at `C:\Users\VIGNESH\AURA\AURA-Privacy-Guardian`
**Date:** 2026-08-24
**Scope:** complete repository — 6 Python modules, 2 data files, README, requirements

---

## 0. Executive summary

AURA is a single-process Streamlit application of roughly 8,100 physical lines across six
Python modules. It is not a demo shell: the telemetry it collects is real, the anomaly
detector is genuinely trained on a real baseline captured from this machine, and the risk
score is derived from weighted observable signals rather than invented. The historical log
in `data/system_logs.csv` contains real scans from 2026-08-19 onward, and
`data/baseline.csv` contains a real 3-feature behavioural baseline. That foundation is
worth preserving and is the reason this should be an evolution rather than a rewrite.

The honest framing in the current product is also an asset. Phrases such as "security
indicators are triage signals, not forensic proof", the explicit refusal to treat camera
availability as evidence of camera misuse, and the "AURA does not claim" section are
exactly the right posture for this class of tool. That language should survive the
migration verbatim.

What does not hold up is everything structural. The application is described as
"real-time" but only collects telemetry when a human clicks a button. The risk thresholds
are implemented four separate times in four files. Persistence is a CSV that is fully read,
re-parsed, re-migrated, concatenated and rewritten on every single event, which is
quadratic and will not survive continuous monitoring. Sensor failure is indistinguishable
from a genuine zero reading, which quietly contradicts the product's own claim to separate
what is observed from what is unknown. There are no tests of any kind. And one number
shown to the user — anomaly confidence — is computed twice by two different formulas that
disagree, with a third hardcoded variant overwriting it.

The recommendation is a phased migration to a FastAPI backend with a continuous background
sampling loop, SQLite persistence behind a repository layer, and a React/TypeScript
frontend, reusing the existing sensor, privacy, model and schema code as the starting point
for the new service layer.

---

## 1. Current architecture

Execution is a single Python process. Streamlit runs `app.py` top to bottom on every user
interaction, including on every widget change. There is no server, no API, no background
worker and no event loop. Data flows in one direction, synchronously, and only when
triggered:

```
button click
    ↓
app.run_aura_scan()
    ↓
aura_core.scan_once()
    ├─ sensors.get_full_sensor_snapshot()     CPU, mem, disk, disk I/O, net, battery, uptime, camera
    ├─ model.detect()                          IsolationForest + LOF on [CPU, Net, Cam]
    ├─ privacy_monitor.get_process_snapshot()  iterate every process
    ├─ privacy_monitor.get_connection_snapshot()
    ├─ privacy_monitor.sensitive_files_in_common_locations()   os.walk of user folders
    ├─ privacy_monitor.privacy_risk()          weighted rule scoring → 0–100
    └─ logger.append_log()                     rewrite entire CSV
    ↓
dict merged from ~6 sources
    ↓
st.session_state → re-render
```

Module responsibilities, as they actually exist rather than as documented:

`app.py` (2,138 lines) is the UI, but also contains a fourth independent copy of the risk
threshold logic, the demo-mode log preservation hack, and its own set of `safe_int` /
`safe_float` / `safe_text` coercion helpers that duplicate identical helpers in
`aura_core.py` and `logger.py`.

`aura_core.py` (1,366 lines) is the orchestrator. It flattens the sensor snapshot into
stable field names, runs detection, and assembles the result. It also re-derives risk
severity as a "defensive fallback", and computes a second, contradictory confidence metric.

`sensors.py` (964 lines) is the psutil telemetry layer. Well-organised per-sensor
functions, each independently failure-tolerant. Holds process-global mutable state for
rate calculations.

`privacy_monitor.py` (1,612 lines) collects process, connection and sensitive-file
telemetry, and owns the primary risk engine including all threshold constants and signal
weights. This is the most valuable single file in the repository.

`model.py` (876 lines) is the ML layer: `StandardScaler` → `IsolationForest` +
`LocalOutlierFactor`, with a dataclass carrying the fitted objects plus baseline
statistics and training score distributions.

`logger.py` (1,156 lines) is CSV persistence with a genuinely well-built forward migration
that adds missing columns and drops unknown ones, so old logs keep working.

A stylistic note that has real engineering cost: the code is formatted with roughly one
token per line, so 8,100 physical lines represent perhaps 2,500 lines of conventional
Python. This inflates apparent size, makes diffs noisy, and makes review harder than it
needs to be.

---

## 2. What already works

Telemetry collection is real and reasonably broad. `psutil` provides CPU total and
per-core utilisation and frequency, RAM and swap, disk capacity, disk read/write rates
derived from counter deltas, network upload/download rates derived from counter deltas,
active interfaces with addresses, battery state, boot time and uptime, the full process
list with PID, name, user, status, CPU% and memory%, and the inet connection table with
status, local and remote address and owning PID. None of this is fabricated.

The detection ensemble is legitimate. The baseline is collected from actual observed
behaviour over 30 samples, features are standardised before fitting, Isolation Forest uses
300 trees with a fixed seed, LOF uses `novelty=True` with a neighbour count clamped to the
available sample size, and the model retains its own training score distributions and
per-feature baseline mean and standard deviation. Input validation in `model._prepare` is
strict: it checks feature presence, shape, dimensionality and finiteness, and raises rather
than silently coercing.

The risk engine is explainable by construction. Each contributing signal appends both a
human-readable reason and a structured evidence record carrying signal name, severity,
observed value, unit and weight. Weights are deliberately calibrated — an AI anomaly is
worth 30 points while a high remote-connection count is worth 8, with an explicit comment
noting that a normal Windows machine has dozens of remote connections and that the signal
is therefore weak. The exfiltration flag requires suspicious outbound traffic *and* an
independent behavioural indicator, never traffic volume alone. This is careful work.

Failure tolerance at the individual sensor level exists. Every sensor function wraps its
psutil call and returns a structurally valid default rather than propagating, so one broken
sensor does not abort a scan. Process iteration explicitly catches `NoSuchProcess`,
`AccessDenied` and `ZombieProcess` and skips, which is correct for Windows where protected
processes will always deny.

The CSV schema migration works. `_migrate_logs` adds any missing column with a typed
default, drops columns not in the current schema, and coerces numerics with `errors="coerce"`
before filling. Historical data survives schema changes, which is why five-day-old rows
still load.

Demo data is labelled honestly. Synthetic scans are tagged `SAFE_DEMONSTRATION`, the UI
prints an unmissable warning that the telemetry shown does not represent the current state
of the computer, and headings change from "Live Telemetry" to "Synthetic Test Telemetry".

---

## 3. Finding register

Findings are numbered for reference from the migration plan. Severity reflects impact on
correctness, security or the product's own stated goals.

### F1 — Monitoring is not real-time — **HIGH**

The product is titled "Real-Time … Intrusion Detection System" and the dashboard offers a
"Live Security Scan", but telemetry is only collected inside a button handler. Between
clicks, AURA observes nothing. There is no scheduler, no background thread and no polling
loop in the web application. `aura_core.run_terminal_monitoring()` does implement a
continuous loop, but it is CLI-only, writes to stdout, and shares no state with the
dashboard. Behavioural baselining, event correlation, alert cooldowns and trend analysis
are all impossible without continuous sampling, which makes this the root blocker for most
of the target feature set.

### F2 — Blocking collection on the render thread — **HIGH**

A single `scan_once` performs, in sequence and synchronously: `cpu_percent(interval=0.2)`,
`cpu_percent(interval=0.1, percpu=True)`, a full iteration of every running process
(≈390 on this machine per the logged `Process_Count`), a full connection-table enumeration
that then calls `psutil.Process(pid).name()` *once per connection* for up to 150
connections, and an `os.walk` over Documents, Desktop, Downloads and Pictures bounded at
2,500 files. Those 0.3 s of deliberate sleeps are the floor, not the cost. Each per-connection
`Process(pid).name()` is a separate process open. The file walk touches the disk. All of it
runs on the thread that is supposed to be rendering, so the UI is frozen for the duration
and the cost scales with how much data the user has in their home folders.

### F3 — Risk thresholds implemented four times — **HIGH**

The mapping from a 0–100 score to `NORMAL / LOW / MEDIUM / HIGH / CRITICAL` at cut points
80 / 55 / 25 / 10 appears independently in `privacy_monitor.privacy_risk` (lines ~1192-1210),
`privacy_monitor.get_privacy_health_summary` (lines ~1522-1535), `aura_core.scan_once` as a
"defensive fallback" (lines ~990-1003), and `app.risk_from_score` (lines ~443-455). Four
copies will drift, and per F9 they demonstrably already have.

Relatedly, `app.normalize_risk(value, score)` accepts a `value` parameter and never reads
it — the body returns `risk_from_score(score)` unconditionally, so every call site passes a
carefully extracted risk level that is then discarded. This looks like dead code but is
deliberate, and the comment explaining it is correct: it exists to prevent contradictory
displays such as a score of 29 labelled `PROTECTED`. The stored data justifies the defence —
the row at 2026-08-19 20:39:46 records `Risk_Score=10` with `Risk=NORMAL`, whereas the
current bands place 10 in `LOW`. So the right response is not to start honouring the
discarded parameter but to consolidate the four threshold implementations into one and
normalise on read, keeping this defensive behaviour as the single source of truth.

### F4 — Anomaly confidence is computed twice and disagrees — **HIGH**

`model._ensemble_confidence` computes confidence as
`agreement * 60 + mean_intensity * 0.40`, returning a continuous value. Separately,
`aura_core._calculate_anomaly_metrics` computes confidence as a hardcoded 100.0 when both
detectors fire, 60.0 when one fires, 0.0 otherwise. Both results are then merged into the
same result dictionary in `scan_once` — `**ml_result` contributes lowercase
`anomaly_confidence`, `**anomaly_metrics` contributes capitalised `Anomaly_Confidence` —
so the same scan carries two different confidence values under two different keys. The
hardcoded variant is the one whose name matches the CSV column. A confidence figure of
exactly 100.0 is also not defensible for an unsupervised detector agreeing with itself.

### F5 — LOF score normalisation is mathematically unsound — **MEDIUM**

`model._normalize_lof_score` applies `(0.5 - score + 0.5) * 100` clipped to 0–100 — the
identical transform used for Isolation Forest. Isolation Forest's `decision_function` is
approximately bounded within ±0.5, so that mapping is roughly sensible for it. LOF's
novelty `decision_function` is not bounded on that scale and has entirely different
dynamics. The resulting `lof_anomaly_intensity` is therefore not a meaningful 0–100
quantity, and because it feeds `_ensemble_confidence`, part of the confidence figure shown
to the user is noise. The model already stores `lof_training_scores`; percentile ranking
against that empirical distribution would be defensible, and the same applies to
`if_training_scores`.

### F6 — CSV write amplification and corruption risk — **HIGH**

`logger.append_log` reads the entire log file, runs the full migration over every
historical row, builds a one-row DataFrame, concatenates, and rewrites the complete file —
for every event. Cost per write grows linearly with history, so total cost is quadratic.
The write is not atomic: `to_csv` truncates in place, so a crash or power loss mid-write
leaves a truncated or corrupt log with no recovery path. There is no locking, so two
writers interleave destructively. There are no indexes, so the Event Explorer's required
filtering by severity, category, process, date and risk would mean a full parse and scan
per query. There is no retention or cleanup, so the file grows without bound. Under the
continuous monitoring that F1 requires, this design fails outright.

### F7 — Sensor failure is indistinguishable from a zero reading — **HIGH**

Roughly forty `except Exception` handlers return a structurally valid zero. A CPU sensor
that raises returns `0.0`, which the dashboard renders as "CPU Usage 0.0%" — a healthy
idle machine. `get_sensor_health` does not help: it checks only whether a key is *present*
in the snapshot dictionary, and `get_full_sensor_snapshot` always populates every key, so
health is reported as 100% even if every underlying call failed. This directly contradicts
the product's own requirement to distinguish observed from inferred from unknown, and the
docstring's stated intent to distinguish "NORMAL SYSTEM" from "SENSOR UNAVAILABLE". The
distinction is asserted but not implemented.

### F8 — Process-global mutable sampling state — **MEDIUM**

`sensors.py` holds `_net_sent`, `_net_received`, `_net_timestamp`, `_disk_read`,
`_disk_write`, `_disk_timestamp` at module scope. Rate calculation is a delta against
whatever the last caller left behind. Two consequences are already live. First, any call
sequence where `_sample_network()` runs twice in quick succession makes the second call
measure a near-zero time window, producing meaningless rates. Second, the first call after
process start always returns 0.0 for upload and download because there is no prior sample —
so the very first scan of every session reports zero network activity as fact. Under
concurrency this becomes silent cross-contamination between callers.

### F9 — Silent persistence regression: 20 of 34 fields are no longer written — **HIGH**

`logger.append_log` accepts 34 parameters and correctly handles all of them —
`established_connections`, `listening_connections`, `model_health` and `training_samples`
are read and written at `logger.py:841`, `844`, `900` and `902`. There is exactly one call
site, `aura_core.py:1074`, and it passes 14: `cpu`, `net`, `cam`, the three anomaly flags,
`risk`, `process_count`, `remote_connections`, `sensitive_files`, `risk_score`,
`network_level`, `privacy_event` and `potential_data_exfiltration`. Every parameter under
the function's own `Extended telemetry`, `AI intelligence`, `Risk intelligence` and
`Model information` headings — 20 fields — is left at its default, so memory, disk, disk
I/O, CPU frequency, download and upload rates, connection state counts, both detector
scores, both intensities, confidence, strongest feature and deviation, severity, process
level, model health and training sample count are all written as `0.0` / `""` /
`"UNKNOWN"` despite being in local scope at the call site.

The historical data shows this is a **regression rather than an unfinished feature**, which
makes it more serious. Three rows written on 2026-08-19 between 20:16:38 and 20:32:43 carry
fully populated extended telemetry — `Memory=81.0`, `Disk=95.6`, `CPU_Frequency=2000.0`,
`IF_Score=0.1994`, `LOF_Score=0.7927`, `IF_Anomaly_Intensity=19.94`,
`LOF_Anomaly_Intensity=79.27`, `Established_Connections=32`, `Listening_Connections=29`,
`Model_Health=HEALTHY`, `Training_Samples=30`, and one row also has `Disk_Read=15.526`,
`Disk_Write=2.486`, `Network_Download=7.032`, `Network_Upload=4.253`. From the row at
20:39:46 onward every one of those fields reverts to `0.0` or `UNKNOWN` and stays there.
The wiring existed, worked, and was lost — with no test to catch it, per F15.

`Severity` was lost in the same regression and demonstrates the user-visible cost. The row
at 20:32:03 records `Risk_Score=70, Risk=HIGH, Severity=HIGH`. The row at 20:40:49 records
the same `Risk_Score=70, Risk=HIGH` but `Severity=INFO`, and every subsequent high-risk row
is also labelled `INFO`. The persisted severity of historical high-risk events is simply
wrong.

This is the highest value-to-effort fix in the repository: the receiving function is already
correct, the values are already computed, and the change is passing arguments that are
already in scope.

Two further pieces of drift are visible in the same file, worth recording because they
affect how history should be migrated. First, `Event_ID` is empty for the five earliest rows
and correctly populated from 19:52:39 onward, so the importer must tolerate missing IDs
rather than assume the column is reliable. Second, scoring weights have changed at least
twice. Rows from 21:57:17 onward reconcile exactly against the current weight set — a row
with `Anomaly=1` and `Remote_Connections=62` scores 32, matching an ML anomaly at +30 plus a
remote-connection watch at +2; a row with `Net=5000` added scores 62, matching a further +30
for `NETWORK_VERY_HIGH`. Earlier rows do not reconcile: the same 96%/5000 input scored 70 at
20:32:03 and 20:40:49, and the five earliest rows carry `Risk_Score=1`, which the current
weights cannot produce at all. Consequently historical risk scores are **not comparable
across time**, and any trend analysis or baseline built from this file must either record a
scoring-version per row or treat pre-21:57 rows as a different scale.

### F10 — Demo mode restores the log by overwriting it — **MEDIUM**

`app.run_aura_scan` handles synthetic scans by reading the entire log into memory, calling
`scan_once` (which appends to it), then writing the saved bytes back in a `finally` block.
The intent — keeping synthetic data out of production history — is right. The mechanism is
a read-modify-write race that discards any event written in between and loses data outright
if the process dies inside the window. The correct fix is for the scan path to accept a
flag and not persist at all.

### F11 — Camera probe activates the camera — **MEDIUM (privacy)**

`sensors.get_camera_status` calls `cv2.VideoCapture(0, cv2.CAP_DSHOW)` and reports
`isOpened()`. On Windows this genuinely powers on the webcam and lights the activity LED. A
privacy tool that switches on your camera in order to determine whether your camera can be
switched on is a real privacy cost, and it also perturbs the thing being measured — while
AURA holds the device, another application cannot. It is correctly defaulted off and
correctly documented as not proving misuse, but the signal's value does not justify its
cost. It also contributes a `Cam` column to the ML feature vector that is almost always
constant 0, which adds a near-zero-variance feature to a 3-feature model.

### F12 — Sensitive file paths are collected and retained — **MEDIUM (privacy)**

`sensitive_files_in_common_locations` returns up to 250 absolute paths to the user's
documents, and `scan_once` places them in the result under `Sensitive_File_Paths`, which
lands in Streamlit session state. The risk engine only ever uses the *count*. Retaining
full paths to a user's private documents in order to display a number violates the
data-minimisation principle the product claims. The extension list is also broad enough to
be near-meaningless — it includes `.txt`, `.md`, `.py`, `.json` and `.csv`, so on a
developer's machine the count is dominated by source files and is not a privacy signal at
all.

### F13 — Hardcoded and fragile paths — **LOW**

`get_disk_info` defaults to `path="C:\\"`. `COMMON_SENSITIVE_DIRS` is a hardcoded set of
lowercase English folder names, which survives only because Windows filesystems are
case-insensitive and breaks on localised Windows installations and on OneDrive-redirected
Known Folders. `logger.save_data` defaults to a relative `"data/system_logs.csv"`. There is
no configuration layer at all: thresholds, intervals, limits and paths are constants spread
across four modules.

### F14 — Broken first-run experience — **MEDIUM**

`load_model` is decorated `@st.cache_resource` and calls `get_or_create_baseline()`, which
falls through to `collect_baseline()` when no baseline exists. That runs a 30-iteration loop
with 0.5 s sleeps and `cpu_percent(interval=0.5)` per iteration — roughly 30 seconds of
blocking work — inside a cached resource initialiser, with progress reported via `print()`
to a terminal the user is not looking at. A first-time user sees a frozen page.

### F15 — No tests — **HIGH**

There are no test files, no test framework in `requirements.txt`, and no CI configuration.
Every finding above was found by reading rather than by a failing test, and nothing prevents
regression.

### F16 — Debug detail rendered into the browser — **LOW (security)**

`st.exception(exc)` is called in three places, rendering full Python tracebacks including
absolute filesystem paths and local variable context into the page. Acceptable in
development, wrong for a distributed application.

### F17 — `unsafe_allow_html` as a latent XSS vector — **LOW (security)**

`unsafe_allow_html=True` is used four times. Every current use passes a static string
literal, so there is no exploitable injection today. It is listed because the pattern
becomes a live vulnerability the moment any telemetry value is interpolated into those
templates — and process names, which are attacker-controllable by anyone who can name an
executable, are exactly the kind of value a future dashboard would want to render there.

### F18 — Duplicated coercion helpers — **LOW**

`safe_float` / `safe_int` / `safe_text` are independently reimplemented in `app.py`,
`aura_core.py` (as `_safe_*`) and `logger.py` (as `_safe_*`), with subtly different
behaviour — `logger._safe_int` omits the `pd.isna` guard its siblings have.

---

## 4. Security assessment

The requested review covered command injection, unsafe shell execution, path traversal,
unsafe file handling, insecure deserialisation, hardcoded secrets, weak authentication,
excessive privilege, debug exposure, unsafe CORS, unvalidated input, SQL injection, XSS and
CSRF. The result is better than expected, and it is worth stating plainly rather than
manufacturing findings.

There is no `subprocess`, `os.system`, `os.popen`, `eval`, `exec` or `compile` anywhere in
the codebase, so there is no command injection surface. There is no `pickle`,
`joblib.load`, `yaml.load` or `marshal`, so there is no unsafe deserialisation — the model
is retrained from CSV at startup rather than loaded from a serialised artifact. There are
no credentials, tokens or API keys in the source, and `.gitignore` correctly excludes
`.streamlit/secrets.toml`. There is no SQL, so no SQL injection. There is no authentication
or session handling to be weak, because there is no API. There is no CORS configuration,
because there are no cross-origin endpoints. The application opens no listening sockets of
its own beyond Streamlit's.

File access is read-only on metadata: `os.walk` and `Path.suffix` only. The code never
opens, reads, modifies, deletes or transmits a user file, and the docstring's claim to that
effect is accurate. Path traversal is not reachable because no user-supplied path reaches
the filesystem layer — all paths derive from `Path.home()` or the module directory.

The application requests no elevation and degrades correctly without it. On Windows,
`psutil.net_connections(kind="inet")` typically requires administrator rights to attribute
connections to processes owned by other users; the code catches `AccessDenied` and returns
an empty list, so an unprivileged run silently reports zero connections. That is safe
behaviour, but per F7 it is reported as a real zero rather than as a permission limitation,
which is the more serious problem.

The genuine issues are the four already registered: privacy-relevant data collection beyond
what is needed (F12), a sensor that activates hardware to probe it (F11), tracebacks
rendered to the browser (F16), and an HTML-injection pattern that is currently safe but
fragile (F17). To that list, migrating to an HTTP API adds a new surface that does not
exist today and must be designed rather than retrofitted: bind address, authentication for
non-local deployment, CORS allow-list, request validation, rate limiting and secure
headers.

One further point deserves emphasis. AURA contains no offensive capability — no credential
access, no keylogging, no persistence mechanism, no evasion, no exploitation, no packet
capture. The "Security Lab" is genuinely synthetic: it injects numeric values into the
detection pipeline and explicitly does not generate system activity. This posture is
correct and must be preserved through the migration.

---

## 5. Performance assessment

No measurements exist, and I cannot produce real ones from this environment — see section 10.
The following are structural predictions with their reasoning, to be replaced by measured
figures once the code can be executed on Windows.

Per-scan latency is dominated by four costs. The deliberate CPU sampling sleeps contribute
a fixed 0.3 s minimum. Full process iteration over roughly 390 processes with seven
attributes each is a bounded but non-trivial cost. Connection enumeration followed by a
separate `psutil.Process(pid).name()` call per connection — up to 150 process opens — is
likely the single largest contributor, and it is entirely avoidable by building one
PID-to-name map from the process snapshot already collected moments earlier. The `os.walk`
over four user directories bounded at 2,500 files is disk-bound and varies by an order of
magnitude depending on the user's home folder contents.

Streamlit's execution model multiplies all of this. `load_logs()` is called at module scope
in `app.py`, so every widget interaction — every checkbox toggle, every navigation change —
triggers a complete CSV read plus full schema migration plus timestamp parsing of the
entire history, before any page content renders.

Memory growth is bounded per scan but unbounded across a session, because each result dict
embeds the full raw sensor snapshot, up to 100 process names, up to 150 connection records,
up to 100 endpoints and up to 250 file paths, and the latest two of these are retained
indefinitely in session state.

The CSV quadratic behaviour described in F6 is the hard ceiling. At button-click frequency
it is invisible. At the 1–5 second sampling interval that continuous monitoring requires, it
becomes the dominant cost within hours.

---

## 6. UI assessment

The current interface is a competently themed Streamlit application. The dark palette is
coherent, the metric cards have consistent borders and radii, and the seven-section sidebar
navigation is sensible. Empty states exist on most pages. Demo-versus-live labelling is
clear and prominent. This is well above a default Streamlit deployment.

It is nonetheless recognisably Streamlit, and the gap to a professional security product is
structural rather than cosmetic. Layout is constrained to Streamlit's column primitives, so
the dense grid a SOC dashboard needs is not expressible. Charts are `st.line_chart` with no
interaction, no brushing, no zoom, no tooltips and no shared cursor across panels. Tables
are `st.dataframe` with no server-side pagination, sorting, faceted filtering or row
selection, which makes the required Event Explorer impossible. There is no modal or drawer
primitive, so the event investigation workflow — click an alert, see summary, evidence,
timeline, process context, network context and recommended action — has nowhere to live.
There is no light theme; the CSS hardcodes dark values. Accessibility is unverified, and
severity is communicated primarily through colour and emoji, which fails the requirement not
to rely on colour alone. Nothing updates without a rerun.

Specific content problems: the eight-metric telemetry block on the Command Center shows CPU
twice, once under "Live Telemetry" and again under "Current System Snapshot". The "Camera"
metric reads "NOT DETECTED" when the probe is simply disabled, conflating "off" with
"absent". Several metrics render as `0` when their sensor failed rather than indicating
failure, which is F7 surfacing in the UI. The Network Intelligence page displays remote
endpoints as a single-column list of `ip:port` strings with no owning process, protocol or
state, despite `get_connection_snapshot` collecting all of that.

---

## 7. ML and detection assessment

The pipeline is sound in construction and thin in substance. Three features — CPU, outbound
network rate, and camera availability — are not enough signal for behavioural intrusion
detection, and one of the three is effectively constant zero because the camera probe
defaults off (F11). `Cam` is therefore a near-zero-variance feature occupying a third of
the input space.

The `Settings` page is admirably honest about this, stating that process counts, remote
connections and sensitive-file inventory "should only become ML features after being
consistently collected during baseline training". That is exactly the right reasoning. The
problem is that the baseline collector only ever records the same three features, so the
condition can never be satisfied. Breaking that deadlock requires the continuous collector
from F1 writing richer telemetry, and a versioned feature schema so that a model trained on
feature set v1 is never fed a v2 vector.

Contamination is fixed at 0.10, which asserts a priori that 10% of observed normal
behaviour is anomalous. With `MIN_BASELINE_SAMPLES = 10`, a minimal baseline means exactly
one training point is labelled an outlier. This directly determines the false-positive
floor and should be configurable and documented rather than a constant.

There is no separation between training, evaluation and inference. The model is retrained
from CSV on every process start and never persisted, so there is no model artifact, no
version, no training date, no feature-schema version and no recorded dataset provenance.
Consequently there are no evaluation metrics — no precision, recall, F1, ROC-AUC, false
positive rate or confusion matrix. This is the correct state to be in given that no labelled
data exists, and it is much better than displaying invented numbers. The requirement going
forward is to keep it honest: where a metric has not been measured, the UI must say
"not measured" rather than showing a plausible-looking figure. Producing real metrics needs
a labelled or synthetically-labelled evaluation set, which is a deliberate piece of work,
not a side effect of the migration.

Explainability is the strongest part of the existing detection stack and should be extended
rather than replaced. `feature_deviations` already reports per-feature standardised
distance, `strongest_feature` identifies the dominant contributor, and the risk engine
attaches weighted evidence records. What is missing is provenance in the UI: a user cannot
currently tell whether a given statement came from a deterministic rule, a statistical
baseline comparison, the ML ensemble, or the combined risk engine. Every explanation in the
new frontend should be tagged with its source.

---

## 8. Deployment assessment

There is no deployment story. Running AURA requires a terminal, a Python environment,
`pip install -r requirements.txt` and `streamlit run app.py`. `requirements.txt` pins six
packages with `>=` lower bounds and no upper bounds and no lockfile, so builds are not
reproducible. One of those six is `opencv-python`, a heavyweight dependency pulled in solely
for the camera probe of F11.

Data, logs, models and configuration all live inside the source tree, which breaks the
moment the application is installed to a read-only location such as `Program Files`. There
is no versioning mechanism beyond `APP_VERSION = "1.0"` hardcoded in `app.py`, no build
script, no installer, no packaging configuration, no service or autostart integration, and
no `pyproject.toml`.

On containerisation: Docker is the wrong tool for the sensor component and this needs to be
stated clearly rather than provided because it was requested. A container cannot observe the
Windows host's processes, connections or hardware — that is the entire point of the isolation
boundary. Containerising AURA would produce a dashboard that monitors an empty Linux
namespace. If a container is wanted, the only correct architecture separates a Windows-native
agent that collects telemetry from a server component that stores and serves it, and only the
latter is containerisable. That split should be designed deliberately if remote deployment is
a real goal, and skipped entirely if it is not.

---

## 9. Migration plan

The ordering below is deliberate: each phase leaves the repository in a state that can be
verified before the next begins, per the stated implementation rule. The existing Streamlit
app stays runnable until the replacement demonstrably works, so there is never a window with
no working application.

**Phase A — foundations, no behaviour change.** Introduce `pyproject.toml`, a pinned
dependency set, a single `backend/app/core/config.py` holding every threshold, interval,
limit and path currently scattered across four modules, structured logging with rotation and
a redaction filter, a single canonical `platformdirs`-based location for data, logs, models
and config, and one shared coercion module replacing the three duplicate helper sets (F13,
F18). Add pytest and write the first tests against the *existing* `privacy_risk`,
`classify_*` and `model.detect` functions, pinning current behaviour before anything moves.

**Phase B — storage.** Define the SQLAlchemy schema for events, alerts, risk history,
metrics, configuration and model metadata, with indexes on the fields the Event Explorer
must filter by. Put it behind a repository interface so the SQLite-to-PostgreSQL path stays
open. Write a one-time importer that reads `data/system_logs.csv` through the existing
`logger._migrate_logs` and `data/baseline.csv`, so no history is lost. Keep the CSV writer
operational in parallel until the new path is verified. This retires F6.

**Phase C — sensor framework.** Wrap the existing `sensors.py` functions in a sensor
abstraction that returns an explicit status of `OK`, `DEGRADED`, `PERMISSION_DENIED` or
`UNAVAILABLE` alongside its value, so a failed reading is never a zero (F7). Move the
rate-sampling state out of module globals into per-sensor instances (F8). Build the
PID-to-name map once per cycle and share it with the connection collector instead of
reopening every process (F2). Make the sensitive-file scan return counts and categories
only, never paths, and run it on its own slower schedule rather than every cycle (F12).
Make the camera probe opt-in, clearly labelled as activating the device, and excluded from
the feature vector when disabled (F11).

**Phase D — service layer and continuous collection.** Build the async background collector
that samples on a configurable interval, feeds a bounded queue, and drives detection, risk
scoring, alerting and persistence — with per-sensor fault isolation so one failure degrades
one sensor rather than stopping the loop (F1). Consolidate the four threshold
implementations into one risk module (F3). Fix the double confidence computation by deleting
`_calculate_anomaly_metrics` and keeping a single defensible formula (F4). Replace the LOF
normalisation with percentile ranking against the stored `lof_training_scores`, and do the
same for Isolation Forest against `if_training_scores` (F5). Add the alert engine with
deduplication, aggregation, cooldowns, escalation, acknowledgement and suppression. Write
the full record rather than 13 of 40 fields (F9). Add a `persist` flag so demo scans simply
do not write, deleting the backup-and-restore hack (F10).

**Phase E — API and real-time transport.** FastAPI with Pydantic schemas on every endpoint,
a WebSocket channel for pushed events with bounded server-side buffering, an observability
endpoint exposing per-sensor status, last successful collection timestamp and error counts,
and the security controls the current codebase has never needed: loopback-only bind by
default, a CORS allow-list, request validation, rate limiting, secure headers, and no
tracebacks in responses (F16).

**Phase F — frontend.** React, TypeScript, Vite, Tailwind. Layout and navigation first, then
the dashboard, then Threat Center, Process Intelligence, Network Intelligence, Privacy
Intelligence, Behavioral Intelligence, Event Explorer, Analytics, Reports, System Health,
Settings and About. Every page gets explicit loading, empty, error and degraded states.
Severity is encoded with shape and text as well as colour. Dark mode is primary, light mode
is complete rather than an afterthought. Explanations are tagged with their provenance —
rule, statistic, model or combined.

**Phase G — model lifecycle.** Persist the trained model with version, feature-schema
version, training date and dataset provenance. Separate training, evaluation and inference
entry points. Report metrics only where actually measured, and display "not measured"
everywhere else.

**Phase H — hardening, performance, packaging, QA.** Security review of the new HTTP
surface. Measured performance figures replacing the predictions in section 5. Production
frontend build served by the backend. Windows packaging with user-data paths outside the
install directory. Full acceptance pass against the criteria in the brief.

---

## 10. Environment constraint affecting execution

This audit was produced by reading the repository. It was not possible to execute anything.

The sandboxed Linux environment available in this session failed to start
(`VM_DISK_SPACE_INSUFFICIENT`), so there is currently no shell: no `pip`, no `pytest`, no
`python -c`, no `npm`, no `uvicorn`, no ability to import a module and see whether it
raises.

Independently of that failure, the sandbox could not have validated the parts of AURA that
matter most. It is a Linux container. `psutil` inside it reports the container's own
processes, connections and hardware — not this Windows machine's. The Windows sensor layer,
`AccessDenied` behaviour on `net_connections`, the DirectShow camera path, Windows drive
handling and the packaging story are all only testable by running on Windows.

This has a direct consequence for how the remaining phases should be executed. Findings
F1 through F18 are grounded in code that has been read closely and are reliable. The
performance figures in section 5 are explicitly labelled predictions, not measurements. And
any new code written from this session must be verified by running it on the Windows host —
writing a full backend and frontend without executing a single line would contradict the
brief's own rule that intermediate states be validated before proceeding.
