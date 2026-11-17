import { useEffect, useMemo, useState } from "react";
import "./style.css";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000/api";
const ROOT = API.endsWith("/api") ? API.slice(0, -4) : API;
const categories = ["All Emails", "Important", "Work", "Personal", "Finance", "Receipts", "Travel", "Promotions", "Social", "Updates", "Other"];
const decisions = [
  ["", "All reply states"],
  ["reply", "Reply needed"],
  ["no_reply", "No reply"],
  ["review", "Needs review"],
];

export default function App() {
  const [user, setUser] = useState(null);
  const [csrfToken, setCsrfToken] = useState("");
  const [authChecked, setAuthChecked] = useState(false);
  const [emails, setEmails] = useState([]);
  const [pagination, setPagination] = useState({ page: 1, page_size: 20, total: 0, total_pages: 1 });
  const [page, setPage] = useState(1);
  const [category, setCategory] = useState("All Emails");
  const [replyDecision, setReplyDecision] = useState("");
  const [priority, setPriority] = useState("");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [replyBody, setReplyBody] = useState("");
  const [loading, setLoading] = useState(false);
  const [actionBusy, setActionBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [syncStatus, setSyncStatus] = useState(null);

  async function apiFetch(path, options = {}) {
    const method = (options.method || "GET").toUpperCase();
    const headers = { ...(options.headers || {}) };
    if (method !== "GET" && method !== "HEAD") headers["X-CSRF-Token"] = csrfToken;
    return fetch(API + path, { ...options, method, headers, credentials: "include" });
  }

  useEffect(() => {
    let active = true;
    fetch(ROOT + "/api/me", { credentials: "include" })
      .then(async response => response.ok ? response.json() : null)
      .then(profile => {
        if (!active) return;
        setUser(profile);
        setCsrfToken(profile?.csrf_token || "");
        setAuthChecked(true);
      })
      .catch(() => {
        if (!active) return;
        setUser(null);
        setCsrfToken("");
        setAuthChecked(true);
      });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!user) {
      setEmails([]);
      setPagination({ page: 1, page_size: 20, total: 0, total_pages: 1 });
      setSyncStatus(null);
      return;
    }
    let active = true;
    const timer = setTimeout(async () => {
      setLoading(true);
      setError("");
      const query = new URLSearchParams({ page: String(page), page_size: "20" });
      if (category !== "All Emails") query.set("category", category);
      if (replyDecision) query.set("reply_decision", replyDecision);
      if (priority) query.set("priority", priority);
      if (search.trim()) query.set("search", search.trim());
      try {
        const response = await apiFetch("/emails?" + query.toString());
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Could not load conversations.");
        if (active) {
          setEmails(data.items);
          setPagination(data.pagination);
        }
      } catch (err) {
        if (active) setError(err.message || "Could not load conversations.");
      } finally {
        if (active) setLoading(false);
      }
    }, search ? 200 : 0);
    return () => { active = false; clearTimeout(timer); };
  }, [user, page, category, replyDecision, priority, search, csrfToken]);

  useEffect(() => {
    if (!user) return;
    apiFetch("/sync/status")
      .then(response => response.ok ? response.json() : null)
      .then(setSyncStatus)
      .catch(() => setSyncStatus(null));
  }, [user, csrfToken]);

  const repliesOnPage = useMemo(() => emails.filter(item => item.reply_decision === "reply").length, [emails]);
  const reviewOnPage = useMemo(() => emails.filter(item => item.reply_decision === "review").length, [emails]);

  async function openEmail(email) {
    setSelected({ ...email, messages: [] });
    setReplyBody(email.suggested_reply || "");
    setDetailLoading(true);
    try {
      const response = await apiFetch("/emails/" + encodeURIComponent(email.thread_id));
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not load the conversation.");
      setSelected(data);
      setReplyBody(data.suggested_reply || "");
    } catch (err) {
      setNotice(err.message || "Could not load the conversation.");
    } finally {
      setDetailLoading(false);
    }
  }

  async function changeCategory(email, value) {
    setActionBusy(true);
    try {
      const response = await apiFetch("/emails/" + encodeURIComponent(email.thread_id) + "/category", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ category: value }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Category update failed.");
      setEmails(current => current.map(item => item.id === email.id ? data : item));
      setSelected(current => current?.id === email.id ? { ...current, ...data } : current);
      setNotice("Category updated.");
    } catch (err) {
      setError(err.message || "Category update failed.");
    } finally {
      setActionBusy(false);
    }
  }

  async function createDraft() {
    if (!selected || !replyBody.trim()) return;
    setActionBusy(true);
    try {
      const response = await apiFetch("/emails/" + encodeURIComponent(selected.thread_id) + "/draft", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ body: replyBody }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Draft creation failed.");
      setSelected(current => ({ ...current, draft_id: data.draft_id, draft_status: "draft" }));
      setEmails(current => current.map(item => item.id === selected.id ? { ...item, draft_id: data.draft_id, draft_status: "draft" } : item));
      setNotice("Draft created. Review it before sending.");
    } catch (err) {
      setError(err.message || "Draft creation failed.");
    } finally {
      setActionBusy(false);
    }
  }

  async function sendDraft() {
    if (!selected?.draft_id || selected.draft_status !== "draft") return;
    if (!window.confirm("Confirm this draft action? In mock mode, no email is sent.")) return;
    setActionBusy(true);
    try {
      const response = await apiFetch("/emails/" + encodeURIComponent(selected.thread_id) + "/send", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ draft_id: selected.draft_id, confirmed: true }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Send action failed.");
      setSelected(current => ({ ...current, draft_status: "sent" }));
      setEmails(current => current.map(item => item.id === selected.id ? { ...item, draft_status: "sent" } : item));
      setNotice(data.simulated ? "Mock send completed; no email was sent." : "Draft sent.");
    } catch (err) {
      setError(err.message || "Send action failed.");
    } finally {
      setActionBusy(false);
    }
  }

  async function syncMailbox() {
    if (!user) return;
    setActionBusy(true);
    setError("");
    try {
      const response = await apiFetch("/sync", { method: "POST" });
      let state = await response.json();
      if (!response.ok) throw new Error(typeof state.detail === "string" ? state.detail : (state.detail?.message || "Could not start sync."));
      setSyncStatus(state);
      setNotice("Mailbox sync queued.");
      for (let attempt = 0; attempt < 40 && (state.status === "queued" || state.status === "running"); attempt++) {
        await new Promise(resolve => setTimeout(resolve, 500));
        const statusResponse = await apiFetch("/sync/status");
        if (statusResponse.ok) {
          state = await statusResponse.json();
          setSyncStatus(state);
        }
      }
      if (state.status === "completed") setNotice("Sync finished: " + state.processed + " processed, " + state.failed + " failed.");
      else if (state.status === "failed") setError("Sync failed. Review backend status and logs.");
      else setNotice("Sync is still running. Status will remain available here.");
      const refreshQuery = new URLSearchParams({ page: String(page), page_size: "20" });
      if (category !== "All Emails") refreshQuery.set("category", category);
      if (replyDecision) refreshQuery.set("reply_decision", replyDecision);
      if (priority) refreshQuery.set("priority", priority);
      if (search.trim()) refreshQuery.set("search", search.trim());
      const refresh = await apiFetch("/emails?" + refreshQuery.toString());
      if (refresh.ok) {
        const data = await refresh.json();
        setEmails(data.items);
        setPagination(data.pagination);
      }
    } catch (err) {
      setError(err.message || "Sync failed.");
    } finally {
      setActionBusy(false);
    }
  }

  async function signOut() {
    try {
      const response = await fetch(ROOT + "/auth/logout", {
        method: "POST",
        credentials: "include",
        headers: { "X-CSRF-Token": csrfToken },
      });
      if (!response.ok) throw new Error("Could not sign out.");
      setUser(null);
      setCsrfToken("");
      setSelected(null);
      setNotice("");
      setError("");
    } catch (err) {
      setError(err.message || "Could not sign out.");
    }
  }

  if (!authChecked) return <div className="app-loading">Loading your mailbox…</div>;

  return <div className="layout">
    <aside className="sidebar">
      <div className="brand"><span className="brand-icon">M</span><div>mailroom<span>AI</span></div></div>
      {user && <button className="compose" onClick={syncMailbox} disabled={actionBusy}>↻　Sync mailbox</button>}
      <div className="nav-label">MAILBOX</div>
      {categories.map((item, index) => <button key={item} className={category === item ? "nav active" : "nav"} onClick={() => { setCategory(item); setPage(1); }}>
        <span>{["▤", "!", "▣", "♡", "＄", "▧", "✈", "◇", "◎", "◌", "••"][index]}</span>{item}
      </button>)}
      <div className="sidebar-foot">
        <span className={"status-dot " + (syncStatus?.status === "running" || syncStatus?.status === "queued" ? "busy" : "")}></span>
        {syncStatus ? "Sync " + syncStatus.status : "Sign in to connect"}
      </div>
    </aside>

    <main className="main">
      <header>
        <div><div className="eyebrow">YOUR INBOX</div><h1>{category}</h1></div>
        <div className="account">
          {user ? <><span>{user.name || user.email}</span><button className="auth-link" onClick={signOut}>Sign out</button></> :
            <button className="auth-link" onClick={() => { window.location.href = ROOT + "/auth/google/start"; }}>Continue with Google</button>}
        </div>
      </header>

      {!user ? <section className="signin-card">
        <div className="brand-icon">M</div><h2>Sign in to manage your mail</h2>
        <p>Connect with Google to view, classify, and draft replies for your conversations.</p>
        <button className="compose" onClick={() => { window.location.href = ROOT + "/auth/google/start"; }}>Continue with Google</button>
        <small>This demo uses sample conversations. It does not connect to Gmail or send real messages.</small>
      </section> : <>
        <section className="stats">
          <div className="stat"><span>CONVERSATIONS</span><b>{pagination.total}</b><small>matching filters</small></div>
          <div className="stat"><span>REPLIES NEEDED</span><b>{repliesOnPage}</b><small>on this page</small></div>
          <div className="stat"><span>NEEDS REVIEW</span><b>{reviewOnPage}</b><small>on this page</small></div>
        </section>

        <section className="toolbar">
          <input value={search} onChange={event => { setSearch(event.target.value); setPage(1); }} placeholder="Search sender, subject, or summary…" aria-label="Search conversations" />
          <select value={replyDecision} onChange={event => { setReplyDecision(event.target.value); setPage(1); }} aria-label="Filter by reply decision">
            {decisions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
          <select value={priority} onChange={event => { setPriority(event.target.value); setPage(1); }} aria-label="Filter by priority">
            <option value="">All priorities</option><option value="high">High priority</option><option value="medium">Medium priority</option><option value="low">Low priority</option>
          </select>
          <button className="sync" onClick={syncMailbox} disabled={actionBusy}>↻ Sync</button>
        </section>

        {notice && <div className="notice" role="status">{notice}<button onClick={() => setNotice("")}>×</button></div>}
        {error && <div className="error-banner" role="alert">{error}<button onClick={() => setError("")}>×</button></div>}

        <section className="table-wrap">
          <div className="table-head"><span>SENDER / SUBJECT</span><span>AI SUMMARY</span><span>CATEGORY</span><span>PRIORITY</span></div>
          {loading ? <div className="empty">Loading conversations…</div> : emails.map(email => <div className="email-row" key={email.id} role="button" tabIndex={0} onClick={() => openEmail(email)} onKeyDown={event => {
            if (event.target === event.currentTarget && (event.key === "Enter" || event.key === " ")) { event.preventDefault(); openEmail(email); }
          }}>
            <span className="sender"><i>{(email.sender_name || "?").charAt(0)}</i><span><b>{email.sender_name}</b><small>{email.subject}</small><small>{email.sender_email}</small></span></span>
            <span className="summary">{email.summary}<small className={"decision " + email.reply_decision}>{email.reply_decision.replace("_", " ")}</small></span>
            <span><select className="category-select" value={email.category} aria-label={"Category for " + email.subject} disabled={actionBusy} onClick={event => event.stopPropagation()} onKeyDown={event => event.stopPropagation()} onChange={event => changeCategory(email, event.target.value)}>{categories.slice(1).map(value => <option key={value}>{value}</option>)}</select></span>
            <span><label className={"priority " + email.priority}>{email.priority}</label></span>
          </div>)}
          {!loading && emails.length === 0 && <div className="empty">{error ? "Could not load conversations." : "No conversations match these filters."}</div>}
          <div className="pagination"><span>{pagination.total} conversations · Page {page} of {pagination.total_pages || 1}</span><div>
            <button disabled={page <= 1 || loading} onClick={() => setPage(page - 1)}>←</button>
            <button disabled={page >= (pagination.total_pages || 1) || loading} onClick={() => setPage(page + 1)}>→</button>
          </div></div>
        </section>
      </>}

      {selected && <div className="scrim" onClick={() => setSelected(null)}><aside className="detail" onClick={event => event.stopPropagation()}>
        <button className="close" onClick={() => setSelected(null)} aria-label="Close details">×</button>
        <div className="eyebrow">CONVERSATION DETAILS</div><h2>{selected.subject}</h2>
        <div className="from"><i>{(selected.sender_name || "?").charAt(0)}</i><span><b>{selected.sender_name}</b><small>{selected.sender_email}</small></span></div>
        {detailLoading ? <div className="empty">Loading conversation…</div> : <>
          <div className="detail-block"><div className="eyebrow">AI SUMMARY</div><p>{selected.summary}</p></div>
          <div className="detail-block"><div className="eyebrow">CATEGORY</div><select className="category-select" value={selected.category} disabled={actionBusy} onChange={event => changeCategory(selected, event.target.value)}>{categories.slice(1).map(value => <option key={value}>{value}</option>)}</select></div>
          <div className="detail-block"><div className="eyebrow">PRIORITY · {selected.priority}</div><div className={"priority " + selected.priority}>{selected.priority}</div></div>
          <div className="detail-block"><div className="eyebrow">REPLY DECISION · {selected.reply_decision.replace("_", " ")}</div><p>{selected.reply_reason}</p></div>
          {selected.key_points?.length > 0 && <div className="detail-block"><div className="eyebrow">KEY POINTS</div><ul>{selected.key_points.map(point => <li key={point}>{point}</li>)}</ul></div>}
          <div className="detail-block"><div className="eyebrow">FULL CONVERSATION</div>
            {selected.messages?.length ? selected.messages.map(message => <article className={"message " + (message.is_user ? "own" : "")} key={message.message_id}>
              <div className="message-meta"><b>{message.sender_name || message.sender_email}</b><time>{new Date(message.timestamp).toLocaleString()}</time></div>
              <div className="message-body">{message.body_text}</div>
            </article>) : <p className="muted">No original message content was returned.</p>}
          </div>
          {selected.reply_decision === "reply" && <div className="detail-block"><label className="eyebrow" htmlFor="reply-body">SUGGESTED REPLY</label><textarea id="reply-body" value={replyBody} disabled={actionBusy} onChange={event => setReplyBody(event.target.value)} /></div>}
          <div className="detail-actions">
            {selected.reply_decision === "reply" && selected.draft_status !== "sent" && <button className="sync" onClick={createDraft} disabled={actionBusy || !replyBody.trim()}>{selected.draft_status === "draft" ? "Update demo draft" : "Create demo draft"}</button>}
            {selected.draft_status === "draft" && <button className="send" onClick={sendDraft} disabled={actionBusy}>Review & simulate send</button>}
            {selected.draft_status === "sent" && <span className="muted">Demo send completed</span>}
          </div>
          <small className="disclaimer">Mock mode only. This demo cannot access Gmail or send real mail.</small>
        </>}
      </aside></div>}
    </main>
  </div>;
}
