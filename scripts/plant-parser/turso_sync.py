"""
Turso HTTP API client for plant database operations.
Uses urllib (no dependencies) — same approach as Lambda.

Turso HTTP API: POST https://[db].turso.io/v2/pipeline
"""
import json
import urllib.request
import urllib.error
import os
import sys
from pathlib import Path

# Load .env if present
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, val = line.split('=', 1)
            os.environ.setdefault(key.strip(), val.strip())

TURSO_DB_URL = os.environ.get('TURSO_DB_URL', '')
TURSO_AUTH_TOKEN = os.environ.get('TURSO_AUTH_TOKEN', '')


def get_turso_http_url():
    """Convert libsql:// URL to https:// for HTTP API."""
    url = TURSO_DB_URL
    if url.startswith('libsql://'):
        url = url.replace('libsql://', 'https://')
    return url


def turso_execute(sql: str, params: list | None = None) -> dict:
    """Execute a single SQL statement via Turso HTTP API."""
    url = f"{get_turso_http_url()}/v2/pipeline"

    stmt = {"type": "execute", "stmt": {"sql": sql}}
    if params:
        stmt["stmt"]["args"] = [_convert_param(p) for p in params]

    body = {"requests": [stmt, {"type": "close"}]}

    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={
            'Authorization': f'Bearer {TURSO_AUTH_TOKEN}',
            'Content-Type': 'application/json',
        },
        method='POST',
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
            result = data.get('results', [{}])[0]
            if 'error' in result:
                raise RuntimeError(f"Turso SQL error: {result['error']}")
            return result.get('response', {}).get('result', {})
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ''
        raise RuntimeError(f"Turso HTTP {e.code}: {body}") from e


def turso_batch(statements: list[tuple[str, list]]) -> list[dict]:
    """Execute multiple SQL statements in a single pipeline request."""
    url = f"{get_turso_http_url()}/v2/pipeline"

    requests = []
    for sql, params in statements:
        stmt = {"type": "execute", "stmt": {"sql": sql}}
        if params:
            stmt["stmt"]["args"] = [_convert_param(p) for p in params]
        requests.append(stmt)
    requests.append({"type": "close"})

    body = {"requests": requests}

    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={
            'Authorization': f'Bearer {TURSO_AUTH_TOKEN}',
            'Content-Type': 'application/json',
        },
        method='POST',
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
            results = []
            for r in data.get('results', []):
                if 'error' in r:
                    raise RuntimeError(f"Turso batch error: {r['error']}")
                results.append(r.get('response', {}).get('result', {}))
            return results
    except urllib.error.HTTPError as e:
        body_text = e.read().decode() if e.fp else ''
        raise RuntimeError(f"Turso HTTP {e.code}: {body_text}") from e


def turso_query(sql: str, params: list | None = None) -> list[dict]:
    """Execute query and return rows as list of dicts."""
    result = turso_execute(sql, params)
    cols = [c['name'] for c in result.get('cols', [])]
    rows = []
    for row in result.get('rows', []):
        rows.append({cols[i]: _extract_value(row[i]) for i in range(len(cols))})
    return rows


def _convert_param(value):
    """Convert Python value to Turso API parameter format."""
    if value is None:
        return {"type": "null", "value": None}
    elif isinstance(value, bool):
        return {"type": "integer", "value": str(int(value))}
    elif isinstance(value, int):
        return {"type": "integer", "value": str(value)}
    elif isinstance(value, float):
        return {"type": "float", "value": value}
    else:
        return {"type": "text", "value": str(value)}


def _extract_value(cell):
    """Extract value from Turso result cell."""
    if cell is None or cell.get('type') == 'null':
        return None
    val = cell.get('value')
    if cell.get('type') == 'integer':
        return int(val)
    elif cell.get('type') == 'float':
        return float(val)
    return val


def upsert_care_fields(plant_id: str, fields: dict, overwrite: bool = False):
    """Update care fields for a plant. Only fills empty fields unless overwrite=True.

    Usage:
        upsert_care_fields('monstera_deliciosa', {
            'soil_types': 'Well-draining mix',
            'difficulty': 'Easy',
            'propagation_methods': '["Stem cuttings", "Division"]',
        })
    """
    if not fields:
        return
    stmts = []
    for col, val in fields.items():
        if val is None:
            continue
        if overwrite:
            stmts.append((
                f"UPDATE care SET {col} = ? WHERE plant_id = ?",
                [val, plant_id],
            ))
        else:
            # Only fill if currently NULL or empty
            stmts.append((
                f"UPDATE care SET {col} = CASE WHEN {col} IS NULL OR {col} = '' OR {col} = '[]' THEN ? ELSE {col} END WHERE plant_id = ?",
                [val, plant_id],
            ))
    if stmts:
        turso_batch(stmts)


def upsert_plant_fields(plant_id: str, fields: dict, overwrite: bool = False):
    """Update plants table fields. Only fills empty fields unless overwrite=True."""
    if not fields:
        return
    stmts = []
    for col, val in fields.items():
        if val is None:
            continue
        if overwrite:
            stmts.append((
                f"UPDATE plants SET {col} = ? WHERE plant_id = ?",
                [val, plant_id],
            ))
        else:
            stmts.append((
                f"UPDATE plants SET {col} = CASE WHEN {col} IS NULL OR {col} = '' THEN ? ELSE {col} END WHERE plant_id = ?",
                [val, plant_id],
            ))
    if stmts:
        turso_batch(stmts)


def test_connection():
    """Test Turso connection and print table info."""
    try:
        rows = turso_query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [r['name'] for r in rows]
        print(f"Connected to Turso. Tables: {', '.join(tables)}")

        count = turso_query("SELECT COUNT(*) as cnt FROM plants")
        print(f"Plants in database: {count[0]['cnt']}")
        return True
    except Exception as e:
        print(f"Connection failed: {e}", file=sys.stderr)
        return False


if __name__ == '__main__':
    test_connection()
