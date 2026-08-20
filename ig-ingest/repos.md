# The 6 shortlisted Claude tools — repos confirmed from the video visuals (2026-08-13)

All GitHub URLs verified live (HTTP 200 / resolved via search). Screenshots read
from contact sheets in `sheets/`.

1. **claude-video** — `github.com/bradautomates/claude-video`
   Skill `/watch`: give Claude the ability to watch any video (frames + timestamped transcript → single timeline).
   Install: `/plugin marketplace add bradautomates/claude-video` then `/plugin install watch@claude-video`.
   Needs a Gemini API key (Google AI Studio) — Gemini is natively multimodal. MIT.

2. **Agent-Reach** — `github.com/Panniantong/Agent-Reach`
   Gives an agent read access to Twitter/Reddit/YouTube/Bilibili/GitHub. Works with Claude Code, OpenClaw, Cursor.
   Install: one-liner from `raw.githubusercontent.com/Panniantong/Agent-Reach/main/docs/install.md`.
   All source-platform APIs free; only cost is a ~$1/mo server proxy for oversea IPs.

3a. **opensrc** — `github.com/vercel-labs/opensrc` (2.9k★, opensrc.sh)
    Fetch source code for npm packages to give AI coding agents deeper context.
3b. **graphify** — `github.com/Graphify-Labs/graphify` (was safishamsi/graphify; site graphifylabs.ai)
    AI-coding skill (Claude Code/Codex/OpenCode/Cursor/Gemini CLI): turn any folder of code, SQL schemas,
    docs, papers, images, or videos into a queryable knowledge graph (GraphQL). App code + DB schema + infra in one graph.

4. **agent-browser** — `github.com/vercel-labs/agent-browser` (Apache-2.0)
   Fast native Rust browser-automation CLI built for AI agents; ~15x fewer tokens than screenshots (uses the a11y tree).
   Install: `npm install -g agent-browser`. Semantic locators (`find role button click --name "Submit"`),
   built-in chat command, batch mode (HAR/cookies/screenshot-diff/PDF/CDP connect), bundled Chrome for Testing.

5. **claude-premortem-skill** — `github.com/b1rdmania/claude-premortem-skill`
   Runs a premortem (Gary Klein, HBR 2007) before building: 6-step linear flow, parallel sub-agents do the failure
   analysis at step 4; forces honest risk assessment instead of Claude's default agreeableness.

6. **super-video-maker-skill** — `github.com/Bomx/super-video-maker-skill`
   Claude video-editing skill: Remotion + FFmpeg + "hyperframes"; ships FFMPEG_PLAYBOOK.md, REMOTION_VIDEO_GUIDE.md,
   hyperframes-template, remotion-template. Full render/QA pipeline (the reel even shows a multi-agent QA-audit workflow).
