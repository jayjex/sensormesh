#!/bin/bash
# sensormesh-api tunnel: own cloudflared quick tunnel (:8793), harvest URL to public-url.txt.
# Standalone unit; JANGAN restart apimarket / x402-rest / fiatdock units.
cd /home/uwuki/money-mission/projects/sensormesh/mcp
export PATH="/home/uwuki/.local/bin:/usr/local/bin:/usr/bin:/bin"

rm -f tunnel.log public-url.txt
/home/uwuki/money-mission/projects/x402-rest/bin/cloudflared tunnel --url "http://127.0.0.1:8793" --no-autoupdate > tunnel.log 2>&1 &
CF_PID=$!

PUB=""
for i in $(seq 1 40); do
  PUB=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' tunnel.log | head -1)
  [[ -n "$PUB" ]] && break
  sleep 0.5
done
if [[ -n "$PUB" ]]; then
  echo "$PUB" > public-url.txt
  echo "[run] public base: $PUB"
else
  echo "[run] WARNING: no tunnel URL after 20s"
fi

on_term() {
  trap - TERM INT
  kill "$CF_PID" 2>/dev/null
  wait 2>/dev/null
  exit 0
}
trap on_term TERM INT
wait "$CF_PID"
echo "[run] cloudflared exited rc=$?"
