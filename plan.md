Mission
Use all project subagents in .claude/agents to coordinate and complete the HIVE’s real-time, sub-500 ms translation upgrade. Enforce best practices for software quality, parallel work, and security. Aim for a polished, scalable, free-to-run product.

Success Criteria
p95 time-to-first translated audio (TTFT): ≤ 450 ms

p95 caption latency: ≤ 250 ms

<5% retraction rate on live captions

Seamless 1:1/group calls, per-listener language/voice, resilient quality on poor networks

Fully self-hosted: no paid APIs required

Agent Responsibilities
project-orchestrator
Coordinates all phases; creates the project task DAG and assigns responsibilities; tracks overall progress.

rtc-architect
Plans and configures LiveKit SFU, coturn, JWT room security, and audio routing; outputs config/scripts for local/dev.

translator-agent-dev
Implements backend/agents/translator_worker.py: consumes audio, streams STT→MT→TTS, publishes translated tracks and captions.

stt-engineer
Builds backend/services/stt service: FastAPI with streaming faster-whisper/whisper_streaming, VAD, chunking, stabilization.

mt-specialist
Builds backend/services/mt for incremental streaming machine translation, with short-context and low-latency.

tts-engineer
Builds backend/services/tts for streaming TTS (XTTS/Piper/Kokoro), audio streaming, low TTFT; publishes demo client.

net-perf-optimizer
Tunes networking for UDP-first coturn, SFU/worker co-location, jitter and loss resilience, RED, and PLC.

observability-owner
Adds telemetry at every pipeline stage, metrics logging, synthetic load harnesses, and monitoring dashboards.

security-hardener
Implements JWT/ACL security, service-account scoping, TLS/mTLS; provisions secrets rotation.

qa-lead
Sets up automated p95/p99 SLO tests, network impairment sim, functional and integration test suites.

ux-lead
Designs and implements language/voice selectors, premium captions/audio UIs, push-to-translate—all accessible, responsive, and polished.

docs-keeper
Maintains the master README, RUNBOOK, setup scripts, troubleshooting, and developer onboarding docs.

Execution Story Path
Kickoff:
Use project-orchestrator to generate a full execution DAG, mapping every sub-task to one or more agents below.
Output the DAG and a summary table before work begins.

RTC & Infrastructure:
rtc-architect sets up LiveKit OSS + coturn, JWT script, and local testing env; outputs configs and run instructions.

Translation Pipeline:

stt-engineer builds the streaming STT service + client.

mt-specialist builds incremental MT service.

tts-engineer builds streaming TTS service (multiple voices/models) + test.

translator-agent-dev wires these into translator_worker.py: subscribes to live audio, streams pipeline, publishes per-language tracks/captions.

Networking Optimization:
net-perf-optimizer ensures low-latency, high-resilience routing, SFU/worker co-location, UDP-first TURN, and jitter/loss handling.

Observability & Testing:
observability-owner instruments metrics at every stage and adds dashboards.
qa-lead builds SLO/impairment tests and validation pipelines.

Security Hardening:
security-hardener provisions JWT, enforce least privilege, mTLS, and sanity-checks public endpoints.

UX/UI Polish:
ux-lead builds per-user language/voice selectors, captions/audio UI, and interaction hooks.

Documentation:
docs-keeper ensures all code and infra is fully documented, updating the README, RUNBOOK, and deployment guides.

Approval & Integration:
At each major milestone, agents propose PRs, config changes, and run scripts for manual approval.
project-orchestrator tracks branch status, collects results, and resolves blockers by prompting the appropriate agent.

Acceptance Tests & Final QA:
Run qa-lead’s test suites. Resolve any final bugs or performance issues using the responsible agent.

Parallelism and Best Subagent Practices
Distinct agents should run in parallel where tasks don’t depend on each other (e.g., backend services vs. docs vs. RTC config).

Always propose planned file writes, branch names, and commands for human approval.

If a blocking issue is found (missing config, bug), escalate to project-orchestrator.

After each subagent completes, output a summary and proposed PR diff before merging or deploying.

Use observability-owner and qa-lead to verify SLOs after deployment on test/production hardware.