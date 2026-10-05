# 구현 시 참고한 1차 문서

Checked during this build (2026-10-05). Documents are references, not bundled third-party skills.
- OpenAI Codex Skills: https://developers.openai.com/codex/skills/ (redirects to learn.chatgpt.com/docs/build-skills)
- OpenAI AGENTS.md: https://developers.openai.com/codex/guides/agents-md/
- OpenAI Structured Outputs: https://developers.openai.com/api/docs/guides/structured-outputs
- GitHub REST Git Trees: https://docs.github.com/en/rest/git/trees
- HTTPX timeouts: https://www.python-httpx.org/advanced/timeouts/
- FastAPI static files: https://fastapi.tiangolo.com/tutorial/static-files/
- FastAPI testing: https://fastapi.tiangolo.com/tutorial/testing/
- Agent Skills specification: https://agentskills.io/specification

검토한 설치 Skill: Vercel nextjs / agent-browser / eve. 현재 MVP는 durable agent나 Next 런타임을 사용하지 않는다. agent-browser 바이너리가 이 환경에 없어 브라우저 검증은 Playwright로 수행한다. 새로 만든 두 Skill은 이 프로젝트의 계약/검증에만 집중한다.
