Energy Symposium · Energy & Utilities
Claude Code + Bedrock AgentCore Hackathon
Build autonomous AI agents for real upstream, midstream, downstream, and power & utilities challenges with Claude Code on Amazon Bedrock, and deploy them on Bedrock AgentCore. You get the problem and the data — everything else is yours to work out.

1. Getting Started

Join → Login → Hack

Start here
Join the workshop, log in, then hack away
Join the workshop, walk through the login screens with Instructions to Login (about three minutes), then hand Download & Upload to Claude to Claude and ask it to set up your environment.
🚀 Join the Workshop
🔐 Instructions to Login
🛠️ Download & Upload to Claude (PDF)
Optional
Level up
Prompt craft tips, multi-agent context tricks, and a glossary of every AI and agent term used here.
✍️ Prompting Guide (PDF)
📖 Glossary (PDF)
2. Choose Your Use Case

Pick your battleground

Each one-pager gives you the business problem and a complete dataset dictionary — and stops there. No worked solution, no example output, no capability checklist. Deciding what's worth building is the hackathon.

Upstream
Use Case 1 — Drilling Report Analysis
NPT eats 15–25% of well cost and one stuck-pipe event runs $500K–$2M, but the precedents are buried in daily drilling reports nobody has time to read. You get two DDR corpora — 75 narrative reports for 5 Permian wells and a 192-row tabular set for 9 wells across 3 basins — plus NPT logs, bit records, mud logs, formation tops and per-formation thresholds.

📄 Download One-Pager (PDF)
📦 Download Dataset (.zip)
Downstream
Use Case 2 — Refinery Predictive Maintenance
Unplanned pump failure costs a refinery $50K–$200K per hour, and nobody can watch 144 sensor streams at once. You get 625K readings across 12 CDU pumps (6 months at 5-minute intervals), 8 labeled failures, 59 service records, 120 work orders, 200 alarms, vibration baselines and three OEM manuals.

📄 Download One-Pager (PDF)
📦 Download Dataset (.zip)
Midstream
Use Case 3 — Pipeline Leak Detection
Set the leak alarm too sensitive and you shut the line down for nothing at $100K+ an event; too conservative and a leak runs for a week. You get 207K SCADA readings across 8 stations (90 days at 5-minute intervals) with 5 real leaks and 15 labeled false positives, plus ILI history, cathodic protection, weather, valve status and the DOT/PHMSA rules.

📄 Download One-Pager (PDF)
📦 Download Dataset (.zip)
Power & Utilities
Use Case 4 — Intraday Energy Trading
Every continental European power market now trades in quarter-hours, and the gap between optimal and suboptimal intraday trading is 5–12% of revenue — €40K–€144K a day on one CCGT. You get 90 days of EPEX SPOT quarter-hourly prices, a 4-plant portfolio (CCGT, OCGT, wind, solar), marginal cost curves, grid constraints, contracts and REMIT records.

📄 Download One-Pager (PDF)
📦 Download Dataset (.zip)
3. Judging

Two rounds. Three winners.

1
Claude reviews your code
Automated — picks the top 5
Claude reads your zip and weighs five things: how well you solved your use case, how well designed and genuinely usable your interface is, how your agents work together, how cleanly it deploys on AgentCore, and whether your answers are grounded in the dataset. The top 5 teams go through.

2
Human judges watch your video
Top 5 only — picks 1st, 2nd and 3rd
Judges watch the top 5 videos — a voiced screen capture of your solution running, not a slide deck — and pick 1st, 2nd and 3rd place.

4. Submit

Ship it 🚀

📤 Ready to Submit
Three steps. Everything lands in one folder named after your team.

1	Record a 3-minute demo. A voiced screen capture, not a slide deck: say what problem you're solving, then run your solution live against the dataset and show the output it produces. Walk through what your agents did to get there and show off the interface you built. Three minutes is the cap, not a target.
2	Ask Claude to zip it. Ask it to package everything you built into a single zip, then right-click the zip in the VS Code file explorer → Download.
3	Upload both files. Same team name every time — that's what groups your submission.
500 MB per file, any number of files. Submitting again never destroys an earlier upload, so submit a work-in-progress early rather than leaving it to the last five minutes.

📤 Submit
🚧 Some Gotchas
A few things dry runs caught that are easy to lose an hour to.

AgentCore CLI isn't pre-installed	It's an npm package — install it before Lab 2: npm install -g @aws/agentcore. If that fails with a permission error, don't use sudo — run npm config set prefix ~/.npm-global, add it to your PATH, and retry. (Track 1 doesn't need this.)
Port 8080 is your VS Code session	If your agent's dev server also binds to 8080, you'll disconnect your own editor. Use a different port for anything you run locally — e.g. agentcore dev --port 3000
The dataset is not pre-loaded	Download your use case's zip from this portal and unzip it into your workspace before you ls data/
Use Case 2 — Refinery Predictive Maintenance: large file	sensor_timeseries.csv is 625,536 rows / ~60MB. Don't paste the whole file into a Claude Code turn
Use Case 2 — Refinery Predictive Maintenance: two work-order logs	pump_maintenance_history.json and maintenance_work_orders.csv use non-overlapping ID spaces (WO-00001 vs WO-0001) — don't join on work_order_id
Use Case 3 — Pipeline Leak Detection: segment ID format	valve_status.csv's segment_id is unprefixed (01) while every other Use Case 3 file uses SEG-01 — normalize before joining
Use Case 4 — Intraday Energy Trading: nested folders	Files are grouped into subfolders under data/ — use ls -R data/, not ls data/
Claude Code + Bedrock AgentCore Hackathon — Energy Symposium · Energy & Utilities
Claude Code · Strands Agents SDK · Bedrock AgentCore
All datasets are synthetic and generated for hackathon purposes only.