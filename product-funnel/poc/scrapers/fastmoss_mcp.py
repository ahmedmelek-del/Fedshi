"""Minimal FastMoss MCP client over HTTPS (via curl, so it goes through the session's proxy; the FastMoss CLI's own
binary ignores the proxy). Uses the OAuth login the CLI saves in ~/.fastmoss-mcp/state.json and refreshes it
12 hours before it expires. Never print the tokens."""
import json, subprocess, sys
STATE = '/root/.fastmoss-mcp/state.json'
URL = 'https://mcp.fastmoss.com/mcp'

TOKEN_URL = 'https://mcp.fastmoss.com/oauth/token'


def refresh():
    """Swap the refresh token for a new access token (OAuth refresh_token grant) and save it."""
    import datetime as dt
    d = json.load(open(STATE))
    r = subprocess.run(['curl', '-s', '-m', '60', '-X', 'POST', TOKEN_URL, '-H', 'Content-Type: application/x-www-form-urlencoded',
                        '--data-urlencode', 'grant_type=refresh_token', '--data-urlencode', f"refresh_token={d['oauth_refresh_token']}",
                        '--data-urlencode', f"client_id={d.get('oauth_client_id', 'fastmoss-mcp-public-client')}"],
                       capture_output=True, text=True)
    t = json.loads(r.stdout or '{}')
    if not t.get('access_token'):
        raise SystemExit('FastMoss token refresh failed: ' + (t.get('error_description') or t.get('error') or r.stdout[:200]))
    d['oauth_access_token'] = t['access_token']
    if t.get('refresh_token'):
        d['oauth_refresh_token'] = t['refresh_token']
    if t.get('expires_in'):
        d['oauth_expires_at'] = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=int(t['expires_in']))).isoformat()
    json.dump(d, open(STATE, 'w'))
    return d['oauth_access_token']


def token():
    import datetime as dt
    d = json.load(open(STATE))
    exp = d.get('oauth_expires_at')
    if exp:
        when = dt.datetime.fromisoformat(exp[:26].rstrip('Z') + '+00:00' if exp.endswith('Z') else exp)
        if when - dt.datetime.now(dt.timezone.utc) < dt.timedelta(hours=12):
            return refresh()
    return d.get('oauth_access_token') or d.get('access_token')

def rpc(method, params=None, sid=None, rid=1):
    import tempfile, os
    msg = {'jsonrpc': '2.0', 'method': method, 'params': params or {}}
    if rid is not None:
        msg['id'] = rid
    h = ['-H', f'Authorization: Bearer {token()}', '-H', 'Content-Type: application/json',
         '-H', 'Accept: application/json, text/event-stream']
    if sid:
        h += ['-H', f'Mcp-Session-Id: {sid}']
    d = tempfile.mkdtemp()
    hp, bp = os.path.join(d, 'h'), os.path.join(d, 'b')
    subprocess.run(['curl', '-s', '-m', '120', '-D', hp, '-o', bp, '-X', 'POST', URL, *h, '--data-binary', json.dumps(msg)])
    head = open(hp).read() if os.path.exists(hp) else ''
    body = open(bp).read() if os.path.exists(bp) else ''
    sid = next((l.split(':', 1)[1].strip() for l in head.splitlines() if l.lower().startswith('mcp-session-id')), sid)
    data = [l[5:].strip() for l in body.splitlines() if l.startswith('data:')]
    txt = data[-1] if data else body
    try:
        return json.loads(txt), sid
    except Exception:
        return {'raw': txt[:500]}, sid


if __name__ == "__main__" and len(sys.argv) > 1:
    init, sid = rpc('initialize', {'protocolVersion': '2025-03-26', 'capabilities': {}, 'clientInfo': {'name': 'fedshi-funnel', 'version': '1.0'}})
    rpc('notifications/initialized', sid=sid, rid=None)
    if sys.argv[1] == 'tools':
        res, _ = rpc('tools/list', sid=sid, rid=2)
        for t in (res.get('result') or {}).get('tools', []): print(t['name'], '-', (t.get('description') or '')[:110].replace('\n', ' '))
        if 'result' not in res: print(res)
    else:
        res, _ = rpc('tools/call', {'name': sys.argv[1], 'arguments': json.loads(sys.argv[2] if len(sys.argv) > 2 else '{}')}, sid=sid, rid=3)
        print(json.dumps(res, ensure_ascii=False)[:6000])
