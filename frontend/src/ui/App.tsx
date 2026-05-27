import React, { useState } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

type JsonRecord = Record<string, unknown>;

async function postJson<T>(path: string, body: JsonRecord): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error((data as { detail?: string }).detail || res.statusText);
  }
  return data as T;
}

export default function App() {
  const [namespace, setNamespace] = useState('ai-healing-system');
  const [workload, setWorkload] = useState('');
  const [workloadKind, setWorkloadKind] = useState('deployment');
  const [replicas, setReplicas] = useState(2);
  const [dryRun, setDryRun] = useState(true);
  const [autoHeal, setAutoHeal] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<JsonRecord | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = async (path: string, body: JsonRecord) => {
    setLoading(true);
    setError(null);
    try {
      const data = await postJson<JsonRecord>(path, body);
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const basePayload = { namespace, workload, workload_kind: workloadKind, dry_run: dryRun };

  return (
    <div style={{ padding: 24, fontFamily: 'system-ui, sans-serif', maxWidth: 960 }}>
      <h1>AI Self-Healing Kubernetes Platform</h1>
      <p>ChatOps console — analyze logs, restart, rollback, or scale deployments.</p>

      <section style={cardStyle}>
        <h2>Target workload</h2>
        <div style={gridStyle}>
          <label>
            Namespace
            <input value={namespace} onChange={(e) => setNamespace(e.target.value)} style={inputStyle} />
          </label>
          <label>
            Workload (deployment or pod name)
            <input value={workload} onChange={(e) => setWorkload(e.target.value)} style={inputStyle} />
          </label>
          <label>
            Kind
            <select value={workloadKind} onChange={(e) => setWorkloadKind(e.target.value)} style={inputStyle}>
              <option value="deployment">deployment</option>
              <option value="pod">pod</option>
            </select>
          </label>
          <label>
            Replicas (scale only)
            <input
              type="number"
              min={0}
              value={replicas}
              onChange={(e) => setReplicas(Number(e.target.value))}
              style={inputStyle}
            />
          </label>
        </div>
        <label style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 12 }}>
          <input type="checkbox" checked={dryRun} onChange={(e) => setDryRun(e.target.checked)} />
          Dry run (no mutations)
        </label>
        <label style={{ display: 'flex', gap: 8, alignItems: 'center', marginTop: 8 }}>
          <input type="checkbox" checked={autoHeal} onChange={(e) => setAutoHeal(e.target.checked)} />
          Auto-heal on analyze
        </label>
      </section>

      <section style={{ ...cardStyle, marginTop: 16 }}>
        <h2>Actions</h2>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          <button
            style={btnStyle}
            disabled={loading || !workload}
            onClick={() =>
              run('/analyze', {
                ...basePayload,
                auto_heal: autoHeal,
                tail_lines: 600,
              })
            }
          >
            Analyze
          </button>
          <button
            style={btnStyle}
            disabled={loading || !workload}
            onClick={() => run('/restart', basePayload)}
          >
            Restart
          </button>
          <button
            style={btnStyle}
            disabled={loading || !workload}
            onClick={() => run('/rollback', basePayload)}
          >
            Rollback
          </button>
          <button
            style={btnStyle}
            disabled={loading || !workload}
            onClick={() => run('/scale', { ...basePayload, replicas })}
          >
            Scale
          </button>
        </div>
        {loading && <p style={{ marginTop: 12 }}>Running…</p>}
        {error && (
          <pre style={{ ...preStyle, color: '#b91c1c', marginTop: 12 }}>{error}</pre>
        )}
        {result && (
          <pre style={{ ...preStyle, marginTop: 12 }}>{JSON.stringify(result, null, 2)}</pre>
        )}
      </section>
    </div>
  );
}

const cardStyle: React.CSSProperties = {
  padding: 16,
  border: '1px solid #e5e7eb',
  borderRadius: 12,
  background: '#fafafa',
};

const gridStyle: React.CSSProperties = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
  gap: 12,
};

const inputStyle: React.CSSProperties = {
  display: 'block',
  width: '100%',
  marginTop: 4,
  padding: 8,
  borderRadius: 8,
  border: '1px solid #d1d5db',
};

const btnStyle: React.CSSProperties = {
  padding: '8px 16px',
  borderRadius: 8,
  border: 'none',
  background: '#2563eb',
  color: '#fff',
  cursor: 'pointer',
};

const preStyle: React.CSSProperties = {
  background: '#111827',
  color: '#f9fafb',
  padding: 12,
  borderRadius: 8,
  overflow: 'auto',
  fontSize: 12,
};
