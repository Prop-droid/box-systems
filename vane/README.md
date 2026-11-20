# Vane (ex-Perplexica) on the box

Self-hosted Perplexity-style answer engine: SearXNG metasearch + Gemini. Upstream: https://github.com/ItzCrazyKns/Vane (MIT).

- UI: http://tomas-agent-box.tailb74909.ts.net:3100 (tailnet + LAN; no auth, do NOT funnel)
- API: POST http://127.0.0.1:3100/api/search  (GET /api/providers for ids)
- SearXNG JSON API for other tools: http://127.0.0.1:8088/search?q=...&format=json
- Model provider: Gemini (key = GEMINI_API_KEY from ~/.hermes/.env), stored in docker volume vane-data (/home/vane/data/config.json)
- Engine tuning: ./searxng-settings.yml (mounted read-only)

## Run / recreate
    sg docker -c 'docker rm -f vane; docker run -d --name vane --restart unless-stopped \
      -p 3100:3000 -p 127.0.0.1:8088:8080 \
      -v vane-data:/home/vane/data \
      -v /home/tomas/systems/vane/searxng-settings.yml:/etc/searxng/settings.yml:ro \
      itzcrazykns1337/vane:latest'

## Update
    sg docker -c 'docker pull itzcrazykns1337/vane:latest' && rerun the block above (volume keeps config + history)

## Wire into other tools (pending Tomas go)
- Hermes native web_search: ~/.hermes/.env  SEARXNG_URL=http://127.0.0.1:8088 ; ~/.hermes/config.yaml web.search_backend: searxng ; systemctl --user restart hermes-gateway
- Firecrawl /search: SEARXNG_ENDPOINT=http://host.docker.internal:8088 (or 172.17.0.1) in ~/firecrawl/.env, recreate api container

## Notes
- `docker` needs `sg docker -c '...'` in non-login shells (tomas is in the docker group; sessions started before the add don't have it).
- Perplexity cookie-MCP (Hermes perplexity-user-mcp) is the thing this replaces; it has been in anonymous mode since late Sep 2026.
