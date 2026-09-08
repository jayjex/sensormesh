#!/bin/bash
# sensormesh-api origin (:8793). Tunnel lives in its own unit (run-tunnel.sh),
# separate from apimarket/x402-rest/fiatdock units — JANGAN restart unit lain.
cd /home/uwuki/sensormesh/mcp
export PATH="/home/uwuki/.local/bin:/usr/local/bin:/usr/bin:/bin"
export SENSORMESH_MOCK_SETTLEMENT=1
export PORT=8793
exec /home/uwuki/.local/bin/node --max-old-space-size=200 api.js
