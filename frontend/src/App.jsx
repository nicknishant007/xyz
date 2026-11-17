import { useEffect, useMemo, useState } from "react";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000/api";
const ROOT = API.endsWith("/api") ? API.slice(0, -4) : API;
const categories = ["All Emails", "Work", "Personal", "Finance", "Receipts", "Travel", "Promotions", "Social", "Updates", "Other"];

export default function App() {
  const [emails, setEmails] = useState([]);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [category, setCategory] = useState("All Emails");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState(null);
  const [reply, setReply] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [user, setUser] = useState(null);

  useEffect(() => {
    fetch(ROOT + "/api/me", { credentials: "include" })
      .then(response => response.ok ? response.json() : null)
      .then(setUser)
      .catch(() => setUser(null));
  }, []);

  async function load() {
    setBusy(true);
    try {
      const query = new URLSearchParams({ page, page_size: 20 });
      if (category !== "All Emails") query.set("category", category);
      if (search) query.set("search", search);
      const response = await fetch(`${API}/emails?${query}`, { credentials: "include" });
      if (!response.ok) throw new Error("Could not load conversations");
      const data = await response.json();
      setEmails(data.items);
      setPages(data.pagination.total_pages || 1);
    } catch (error) { setNotice(error.message); }
    finally { setBusy(false); }
  }

  useEffect(() => { load(); }, [page, category, search]);
  const needsReply = useMemo(() => emails.filter(e => e.reply_decision === "reply").length, [emails]);

  async function openEmail(email) {
    setSelected(email);
    setReply(email.suggested_reply || "");
  }

  async function changeCategory(email, value) {
    const response = await fetch(`${API}/emails/${email.id}/category`, {
      method: "PATCH",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ category: value }),
    });
    const data = await response.json();
    if (!response.ok) return setNotice(data.detail || "Category update failed");
    setEmails(current => current.map(item => item.id === email.id ? data : item));
    if (selected?.id === email.id) setSelected(data);
  }

  async function createDraft() {
    if (!selected || !reply.trim()) return;
    const response = await fetch(`${API}/emails/${selected.id}/draft`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ body: reply }),
    });
    const data = await response.json();
    if (!response.ok) return setNotice(data.detail || "Draft creation failed");
    setSelected(current => ({ ...current, draft_id: data.draft_id, draft_status: "draft" }));
    setEmails(current => current.map(item => item.id === selected.id ? { ...item, draft_id: data.draft_id, draft_status: "draft" } : item));
    setNotice(`Demo draft saved: ${data.draft_id}`);
  }

  async function sendDemoDraft() {
    if (!selected?.draft_id) return setNotice("Create a draft first.");
    if (!window.confirm("Simulate sending this draft? No real email will be sent.")) return;
    const response = await fetch(`${API}/emails/${selected.id}/send`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ draft_id: selected.draft_id, confirmed: true }),
    });
    const data = await response.json();
    if (response.ok) {
      setSelected(current => ({ ...current, draft_status: "sent" }));
      setEmails(current => current.map(item => item.id === selected.id ? { ...item, draft_status: "sent" } : item));
    }
    setNotice(response.ok ? "Demo send completed. No email was sent." : (data.detail || "Send failed"));
  }

  async function sync() {
    const response = await fetch(`${API}/sync`, { method: "POST", credentials: "include" });
    const data = await response.json();
    setNotice(response.ok ? `Sync ${data.status}: ${data.processed} demo conversations` : (data.detail || "Sync failed"));
    await load();
  }

  return <div className="layout">
    <aside className="sidebar">
      <div className="brand"><span className="brand-icon">M</span><div>mailroom<span>AI</span></div></div>
      <button className="compose" onClick={sync}>↻　Sync Gmail</button>
      <div className="nav-label">MAILBOX</div>
      {categories.map((item, i) => <button key={item} className={category === item ? "nav active" : "nav"} onClick={() => { setCategory(item); setPage(1); }}>
        <span>{["▤","▣","♡","＄","▧","✈","◇","◎","◌","••"][i]}</span>{item}
      </button>)}
      <div className="sidebar-foot">Demo mode · no live mailbox</div>
    </aside>
    <main className="main">
      <header><div><div className="eyebrow">YOUR INBOX</div><h1>{category}</h1></div><div className="account">{user ? <><span>{user.name || user.email}</span><button className="auth-link" onClick={async () => { await fetch(ROOT + "/auth/logout", { method: "POST", credentials: "include" }); setUser(null); }}>Sign out</button></> : <button className="auth-link" onClick={() => { window.location.href = ROOT + "/auth/google/start"; }}>Continue with Google</button>}</div></header>
      <section className="stats">
        <div className="stat"><span>CONVERSATIONS</span><b>{emails.length}</b><small>on this page</small></div>
        <div className="stat"><span>REPLIES NEEDED</span><b>{needsReply}</b><small>in current view</small></div>
        <div className="stat"><span>NEEDS REVIEW</span><b>{emails.filter(e => e.reply_decision === "review").length}</b><small>in current view</small></div>
      </section>
      <section className="toolbar"><input value={search} onChange={e => { setSearch(e.target.value); setPage(1); }} placeholder="Search conversations…" /><select aria-label="Reply filter" onChange={e => setNotice(e.target.value ? `Filter: ${e.target.value} (demo view)` : "")}><option value="">All reply states</option><option value="reply">Reply needed</option><option value="no_reply">No reply</option><option value="review">Review</option></select><button className="sync" onClick={sync}>↻ Sync</button></section>
      {notice && <div className="notice" role="status">{notice}<button onClick={() => setNotice("")}>×</button></div>}
      <section className="table-wrap">
        <div className="table-head"><span>SENDER / SUBJECT</span><span>AI SUMMARY</span><span>CATEGORY</span><span>PRIORITY</span></div>
        {busy ? <div className="empty">Loading conversations…</div> : emails.map(email => <div className="email-row" key={email.id} role="button" tabIndex={0} onClick={() => openEmail(email)} onKeyDown={event => { if (event.key === "Enter") openEmail(email); }}>
          <span className="sender"><i>{email.sender_name.charAt(0)}</i><span><b>{email.sender_name}</b><small>{email.subject}</small></span></span>
          <span className="summary">{email.summary}<small className={`decision ${email.reply_decision}`}>{email.reply_decision.replace("_", " ")}</small></span>
          <span><select className="category-select" value={email.category} aria-label="Edit category" onClick={event => event.stopPropagation()} onChange={event => changeCategory(email, event.target.value)}>{categories.slice(1).map(value => <option key={value}>{value}</option>)}</select></span>
          <span><label className={`priority ${email.priority}`}>{email.priority}</label></span>
        </div>)}
        {!busy && emails.length === 0 && <div className="empty">No conversations found.</div>}
        <div className="pagination"><span>Page {page} of {pages}</span><div><button disabled={page <= 1} onClick={() => setPage(page - 1)}>←</button><button disabled={page >= pages} onClick={() => setPage(page + 1)}>→</button></div></div>
      </section>
    </main>
    {selected && <div className="scrim" onClick={() => setSelected(null)}><aside className="detail" onClick={e => e.stopPropagation()}>
      <button className="close" onClick={() => setSelected(null)}>×</button><div className="eyebrow">CONVERSATION DETAILS</div><h2>{selected.subject}</h2>
      <div className="from"><i>{selected.sender_name.charAt(0)}</i><span><b>{selected.sender_name}</b><small>{selected.sender_email}</small></span></div>
      <div className="detail-block"><div className="eyebrow">AI SUMMARY</div><p>{selected.summary}</p></div>
      <div className="detail-block"><div className="eyebrow">CATEGORY</div><select className="category-select" value={selected.category} onChange={event => changeCategory(selected, event.target.value)}>{categories.slice(1).map(value => <option key={value}>{value}</option>)}</select></div>
      <div className="detail-block"><div className="eyebrow">WHY {selected.reply_decision.replace("_", " ").toUpperCase()}</div><p>{selected.reply_reason}</p></div>
      {selected.key_points.length > 0 && <div className="detail-block"><div className="eyebrow">KEY POINTS</div><ul>{selected.key_points.map(point => <li key={point}>{point}</li>)}</ul></div>}
      {selected.reply_decision === "reply" && <div className="detail-block"><div className="eyebrow">SUGGESTED REPLY</div><textarea value={reply} onChange={e => setReply(e.target.value)} /></div>}
      <div className="detail-actions"><button className="sync" onClick={createDraft}>Create demo draft</button><button className="send" disabled={!selected.draft_id || selected.draft_status === "sent"} onClick={sendDemoDraft}>{selected.draft_status === "sent" ? "Already simulated" : "Simulate send…"}</button></div>
      <small className="disclaimer">Mock mode only. This demo cannot access Gmail or send mail.</small>
    </aside></div>}
  </div>;
}