# Claude Submission Prompt: GeoDrill Risk Copilot

Use this prompt with Claude Code for the final AWS AI Hackathon packaging and
video-production pass. The goal is a submission-ready zip plus a three-minute
commercial technical demo video. Keep this Codex-centric: Codex is the
implementation source of truth in this repository; Claude should integrate,
verify, package, capture, and narrate without inventing features or deployment
evidence.

---

## Copy/Paste Prompt For Claude

You are working in:

```text
/data/dev/setup/app/AWS-Energy-AI-Hackathon-2026
```

You are preparing the final submission for the Claude Code + Bedrock AgentCore
Energy Hackathon. Your job is to merge the implemented components into a
submission package and produce a polished, technical, commercial three-minute
demo video. Do not rewrite the solution unless a validation blocker forces a
minimal fix.

### Non-Negotiables

1. Codex is the primary implementation assistant for this repo. Do not add
   Gemini, Hermes, or Claude development adapters. Do not replace the Codex-owned
   architecture or team contracts.
2. Read these files first:
   - `AGENTS.md`
   - `README.md`
   - `teams.md`
   - `Hackathon/web-instructions.md`
   - `docs/hpc-catalog-feature-contract.md`
   - `docs/architecture/solution.md`
   - `docs/judging/evidence-map.md`
   - `docs/subsurface-digital-twin-seed.md`
   - `docs/toolbox-documentation-index.md`
   - `docs/prompts/claude-full-deployment.md` if present
3. Run and preserve the evidence from:
   - `make validate`
   - `make demo`
   - `agentcore validate --directory .`
   - `agentcore package`
   - `agentcore deploy --target hackathon --dry-run` after a real
     `agentcore/aws-targets.json` target exists
4. The final deployment must use Amazon Bedrock AgentCore. Do not claim cloud
   deployment from config, package, or dry run alone. Cloud readiness requires:
   runtime or endpoint identifier, region, deployment status, and a successful
   grounded invocation with catalog IDs/source citations.
5. Submission outputs:
   - one zip file of the complete submission;
   - one video file, no more than 500 MB;
   - both files must use the same team/project name prefix.
6. The video must be a voiced screen capture, not a slide deck. Keep it under
   three minutes.
7. Every visible score, map point, target, hazard, or chat/agent answer must
   retain provenance: `run_id`, catalog IDs, source row/file, artifact path, and
   synthetic-data notice where available.
8. Never commit or package AWS credentials, `.env`, virtual environments, caches,
   `.git`, local deployment state with secrets, or generated dependency folders.

### Product Story To Preserve

Project name: **GeoDrill Risk Copilot**

Decision question:

> Where are attractive reservoir targets, where are fault/fracture drilling
> hazards, and which catalog files and drilling records support the
> recommendation?

Business value:

- Drilling NPT is expensive: the hackathon use-case notes 15-25% of complex well
  cost and stuck-pipe events around $500K-$2M.
- GeoDrill reduces pre-drill evidence search time by joining synthetic seismic
  interpretation with drilling precedents and source citations.
- The product is defensible because every recommendation can be traced back to
  catalog IDs, physical artifacts, CSV rows, manifests, or drilling passages.
- Generated seismic data is synthetic. Hazard, target, and confidence scores are
  deterministic screening ranks, not calibrated reservoir predictions.

### Team-Owned Contributions To Highlight

Use `teams.md` as the source of truth and explicitly give each teammate a
meaningful on-screen moment:

| Teammate | Contribution To Show | Evidence To Point At |
|---|---|---|
| Aditya | Subsurface Digital Twin Seed: generated catalog as wells, faults, horizons, reservoir probability, stable IDs, physical file provenance | `src/aws_ai_energy/generate/`, `src/aws_ai_energy/subsurface/points.py`, `docs/subsurface-digital-twin-seed.md`, `metadata/runs/<run_id>/digital_twin/` |
| Shrayani | Chat-driven feature heatmaps: supported feature parsing and deterministic heatmap JSON for wells, faults, horizons, reservoir probability, provenance | `src/aws_ai_energy/dashboard.py`, dashboard/chat integration, heatmap JSON tests |
| Rongrong | Risk-ranked prospect list: hazard/target/confidence components, deterministic ranking, JSON/CSV exports | `src/aws_ai_energy/subsurface/scoring.py`, `src/aws_ai_energy/subsurface/export.py`, `reservoir_targets.json`, `fault_fracture_hotspots.json` |
| Yuxin | Streamlit and AWS delivery: local dashboard journey, downloads/citations, AgentCore runtime packaging/deployment/runbooks | `streamlit_app.py`, `agentcore/`, `agentcore_app/`, `docs/runbooks/`, AgentCore validation/package/deploy evidence |

If one teammate-owned artifact is missing, do not hide it. Add the smallest
completion needed if possible, or call it out as a deployment blocker in the
submission readiness notes.

### Validation Pass

Before validation, make sure the AgentCore CLI is available. If it is missing,
install or activate it in the project environment before proceeding; do not skip
AgentCore checks.

Preferred bootstrap:

```bash
command -v agentcore >/dev/null 2>&1 || .venv/bin/python -m pip install 'bedrock-agentcore>=1.9.1,<2'
command -v agentcore
agentcore --version
```

If the Python package does not expose the CLI in the current shell, locate it
inside `.venv/bin/`, add that directory to `PATH`, or reinstall the AgentCore
tooling according to the current AWS/Bedrock AgentCore documentation. Record the
exact install command and version in submission notes.

Run:

```bash
make validate
make demo
agentcore validate --directory .
agentcore package
```

If `agentcore deploy --target hackathon --dry-run` fails because the
`hackathon` target is missing, ask the operator for the real AWS account and
region, then run:

```bash
.venv/bin/python scripts/configure_aws_target.py <12_DIGIT_ACCOUNT> <AWS_REGION>
agentcore deploy --target hackathon --dry-run
```

Deploy only when credentials, region, and target are real:

```bash
agentcore deploy --target hackathon
```

After deployment, capture:

- target name;
- AWS account alias or account ID;
- region;
- runtime name;
- runtime ARN or endpoint;
- deployment status;
- smoke invocation payload;
- smoke invocation response with provenance fields.

If real deployment cannot be completed, state plainly:

```text
AgentCore schema validation and package succeeded, but real AWS deployment was
not completed because <reason>. Do not claim cloud deployment in the video or
submission notes.
```

### Playwright Capture Requirement

Use Playwright for browser automation and screen capture. If Playwright is not
available, download/install it locally in the project environment.

Preferred checks:

```bash
node -e "require('@playwright/test')" || npm install -D @playwright/test
npx playwright install chromium
```

If the project is Python-only or npm is unavailable, use:

```bash
.venv/bin/python -m pip install playwright
.venv/bin/python -m playwright install chromium
```

Do not use port `8080`; it may disconnect the lab editor. Prefer:

```bash
make dashboard
# or, if dashboard is not ready:
.venv/bin/python -m http.server 8502 --directory outputs/hazard_demo/analysis/<run_id>
```

Use Playwright to capture the actual running interface or generated atlas. If a
Streamlit dashboard exists, record it. If it does not, record the generated
`hazard_atlas.html`, exported JSON/CSV, AgentCore package/validation evidence,
and terminal outputs.

### Video Deliverable

Create a voiced screen capture video:

```text
submissions/GeoDrill-Risk-Copilot-demo.mp4
```

Constraints:

- duration: 2:40 to 3:00, never over 3:00;
- file size: under 500 MB;
- format: MP4/H.264/AAC preferred;
- resolution: 1080p if possible, 720p if needed for size;
- bitrate target: 2.5-4 Mbps video, 128 kbps audio;
- include voiceover; if local TTS/mic capture is impossible, create a narration
  script and explicit TODO, but do not call the video final.

If `ffmpeg` is available, compress with:

```bash
ffmpeg -y -i raw-demo.webm \
  -vf "scale=1920:-2,fps=30" \
  -c:v libx264 -preset veryfast -crf 24 \
  -c:a aac -b:a 128k \
  submissions/GeoDrill-Risk-Copilot-demo.mp4
```

Check size:

```bash
ls -lh submissions/GeoDrill-Risk-Copilot-demo.mp4
```

If the MP4 exceeds 500 MB, rerun with 720p and/or higher CRF:

```bash
ffmpeg -y -i raw-demo.webm \
  -vf "scale=1280:-2,fps=30" \
  -c:v libx264 -preset veryfast -crf 28 \
  -c:a aac -b:a 96k \
  submissions/GeoDrill-Risk-Copilot-demo.mp4
```

### Three-Minute Video Script

Use this exact structure. Keep pacing fast and commercial, but technical.

#### 0:00-0:20 - Problem And Stakes

Voiceover:

> This is GeoDrill Risk Copilot. Before drilling, engineers need to know where
> attractive reservoirs are, where fault and fracture hazards sit, and exactly
> which files support the recommendation. In complex wells, NPT can consume
> 15-25% of cost, and a single stuck-pipe event can run hundreds of thousands to
> millions of dollars.

On screen:

- product title;
- use-case one-liner;
- `Hackathon/web-instructions.md` or README business value;
- no slide-only dwell longer than three seconds.

#### 0:20-0:50 - Architecture And Team Ownership

Voiceover:

> Four team-owned components integrate through one catalog provenance contract.
> Aditya seeds the subsurface digital twin. Rongrong ranks prospects and
> hotspots. Shrayani turns user requests into supported heatmap JSON. Yuxin
> packages the local and AgentCore deployment path. Codex keeps the
> implementation consistent with the shared contracts.

On screen:

- `teams.md`;
- `docs/hpc-catalog-feature-contract.md`;
- architecture/data-flow diagram or README journey;
- highlight each teammate's row briefly.

#### 0:50-1:25 - Live Data Run

Voiceover:

> The demo starts from a deterministic generated seismic catalog. Each run
> publishes immutable metadata, digital-twin points, metrics, and physical file
> lineage so the analysis can be restarted and audited.

On screen, run or show:

```bash
make demo
.venv/bin/python -m generate.seismic_catalog \
  --output-dir outputs/hazard_demo/catalog \
  --digital-twin-endpoints
```

Show:

- `run_id`;
- `digital_twin_seed.json`;
- `digital_twin_points.csv`;
- `digital_twin_metrics.json`;
- `digital_twin_layers.geojson`;
- synthetic-data notice.

#### 1:25-2:05 - Interface And Recommendations

Voiceover:

> The analyzer detects faults and fracture corridors, screens wells, ranks
> reservoir targets, and exports the same evidence as JSON and CSV. This target
> is attractive because reservoir probability is high, hazard is bounded, and
> confidence is explicitly scored. This hotspot needs geomechanics review
> because fault likelihood and fracture intensity are elevated.

On screen:

- dashboard or `hazard_atlas.html`;
- fault/fracture map;
- ranked `reservoir_targets.json`;
- `fault_fracture_hotspots.json`;
- a visible row with `run_id`, `fileid`, `sampleid`, `source_row`,
  `artifact_path`, and `synthetic_data=true`.

#### 2:05-2:35 - AgentCore And Grounded Automation

Voiceover:

> The same deterministic tools are packaged for Bedrock AgentCore. The model is
> used for answer composition, while measurements and citations come from the
> generated catalog, analyzer exports, and drilling evidence. We do not ask the
> model to invent risk numbers.

On screen:

```bash
make validate
agentcore validate --directory .
agentcore package
agentcore deploy --target hackathon --dry-run
```

If real deployment is complete, show:

- runtime/endpoint;
- deployed smoke invocation;
- response with citations.

If real deployment is not complete, say:

> The local package and AgentCore schema are ready; final deployment requires the
> authenticated hackathon AWS target and smoke invocation.

#### 2:35-2:55 - Close And Commercial Value

Voiceover:

> GeoDrill gives drilling teams a repeatable pre-drill risk screen: attractive
> targets, drilling hazards, cited precedents, and auditable file lineage in one
> workflow. It is not a black box prediction. It is a grounded decision copilot
> built for engineers who need to trust every number.

On screen:

- summary page or README;
- evidence map;
- final output folder and submission zip/video names.

#### 2:55-3:00 - Final Frame

Text:

```text
GeoDrill Risk Copilot
Synthetic seismic digital twin + drilling evidence + Bedrock AgentCore
Team-owned, provenance-first, deployment-ready when cloud smoke succeeds
```

### Video Capture Implementation Guidance

Create a temporary capture script if needed:

```text
scripts/capture_demo_playwright.(js|py)
```

The script should:

1. open the dashboard or atlas;
2. wait for charts/tables to render;
3. zoom enough for judges to read IDs and citations;
4. move through the four team-owned features in the order above;
5. capture browser video using Playwright context video recording;
6. save raw output under `submissions/raw/`;
7. call `ffmpeg` only for final compression.

Do not commit the raw video or generated package unless requested. Keep the
final video in `submissions/`.

### Submission Zip

Create:

```text
submissions/GeoDrill-Risk-Copilot-submission.zip
```

The zip should include:

- source code under `src/`, `agentcore_app/`, `agentcore/`, `generate/`,
  `scripts/`, and tests;
- `README.md`, `teams.md`, `AGENTS.md`;
- `docs/`;
- `.codex/skills/` and `.codex/prompts/` if present;
- required Hackathon use-case documents and data under `Hackathon/use-case-1/`;
- generated demo evidence required to judge offline:
  `outputs/hazard_demo/catalog/metadata/runs/<run_id>/digital_twin/` and
  `outputs/hazard_demo/analysis/<run_id>/`;
- `coverage.xml` if generated;
- a `SUBMISSION_NOTES.md` file with validation commands, run IDs, AgentCore
  package path, deployment status, video filename, and known limitations.

Exclude:

```text
.git/
.venv/
__pycache__/
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
*.pyc
node_modules/
agentcore/cdk/node_modules/
agentcore/.cli/logs/
agentcore/.env.local
.env
.env.*
raw-demo.webm
submissions/raw/
```

Recommended packaging approach:

```bash
mkdir -p submissions/GeoDrill-Risk-Copilot
rsync -a \
  --exclude '.git' \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude '.pytest_cache' \
  --exclude '.mypy_cache' \
  --exclude '.ruff_cache' \
  --exclude 'node_modules' \
  --exclude 'agentcore/cdk/node_modules' \
  --exclude 'agentcore/.cli/logs' \
  --exclude '.env' \
  --exclude '.env.*' \
  --exclude 'submissions' \
  ./ submissions/GeoDrill-Risk-Copilot/
cd submissions
zip -r GeoDrill-Risk-Copilot-submission.zip GeoDrill-Risk-Copilot
cd -
```

Then verify:

```bash
unzip -l submissions/GeoDrill-Risk-Copilot-submission.zip | head -80
ls -lh submissions/GeoDrill-Risk-Copilot-submission.zip
ls -lh submissions/GeoDrill-Risk-Copilot-demo.mp4
```

### `SUBMISSION_NOTES.md` Template

Create this inside the packaged folder:

```markdown
# GeoDrill Risk Copilot Submission Notes

## Validation

- `make validate`: <pass/fail and timestamp>
- `make demo`: <pass/fail and run id>
- `agentcore validate --directory .`: <pass/fail>
- `agentcore package`: <package path>
- `agentcore deploy --target hackathon --dry-run`: <pass/fail or blocker>
- Real AgentCore deployment: <runtime/endpoint/status or not completed>
- Smoke invocation: <summary or not completed>

## Demo Evidence

- Catalog run: `<run_id>`
- Digital twin seed: `<path>`
- Analysis run: `<path>`
- Atlas: `<path>`
- Manifest: `<path>`
- Ranked targets JSON: `<path>`
- Hotspots JSON: `<path>`

## Team Contributions

- Aditya: <digital twin seed evidence>
- Shrayani: <chat/heatmap evidence>
- Rongrong: <risk-ranked prospect evidence>
- Yuxin: <dashboard/cloud evidence>

## Limits

- Generated seismic data is synthetic.
- Scores are deterministic screening ranks, not calibrated predictions.
- Corpus A and Corpus B drilling identifiers are not joined.
- Cloud deployment is claimed only if runtime and smoke evidence are listed.
```

### Final Readiness Checklist

Before declaring final:

- [ ] `make validate` passes.
- [ ] `make demo` passes and produces a current run id.
- [ ] Digital-twin endpoints are visible.
- [ ] Dashboard or atlas can be opened locally.
- [ ] AgentCore validates.
- [ ] AgentCore package exists.
- [ ] AgentCore dry run succeeds, or blocker is documented.
- [ ] Real deployment and smoke invocation are captured, if credentials are
      available.
- [ ] Video is voiced, under three minutes, and under 500 MB.
- [ ] Zip excludes secrets, virtualenvs, caches, and raw capture files.
- [ ] Submission notes state exactly what is deployed versus validated locally.
- [ ] Every teammate's contribution is explicitly shown in the video and notes.

Return a final report with:

1. zip path and size;
2. video path, duration, and size;
3. validation command results;
4. AgentCore deployment/runtime status;
5. smoke invocation result or blocker;
6. any gaps that should not be claimed to judges.
