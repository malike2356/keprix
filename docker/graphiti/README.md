# Local Graphiti MCP for Keprix

Runs `zepai/knowledge-graph-mcp:1.0.2` on the Keprix docker network.

## Start

```bash
# docker/.graphiti.env must contain OPENAI_API_KEY + OPENAI_API_URL
# (OpenRouter works once max_tokens is clamped via the mounted patches)
docker rm -f keprix-graphiti-mcp 2>/dev/null || true
docker run -d \
  --name keprix-graphiti-mcp \
  --network keprix_keprix_network \
  --env-file /opt/lampp/htdocs/verlox/keprix/docker/.graphiti.env \
  -p 127.0.0.1:8000:8000 \
  -p 127.0.0.1:8010:3000 \
  -p 127.0.0.1:6391:6379 \
  -v keprix_graphiti_data:/var/lib/falkordb/data \
  -v "$PWD/config.yaml:/app/mcp/config/config.yaml:ro" \
  -v "$PWD/patches/factories.py:/app/mcp/src/services/factories.py:ro" \
  -v "$PWD/patches/openai_client.py:/app/mcp/.venv/lib/python3.11/site-packages/graphiti_core/llm_client/openai_client.py:ro" \
  -v "$PWD/patches/llm_config.py:/app/mcp/.venv/lib/python3.11/site-packages/graphiti_core/llm_client/config.py:ro" \
  --restart unless-stopped \
  zepai/knowledge-graph-mcp:1.0.2
```

Health: `http://127.0.0.1:8000/health`  
MCP: `http://127.0.0.1:8000/mcp/`

Keprix backend should use:

```bash
GRAPHITI_MCP_URL=http://keprix-graphiti-mcp:8000/mcp
KEPRIX_GRAPHITI_ENABLED=1
```
