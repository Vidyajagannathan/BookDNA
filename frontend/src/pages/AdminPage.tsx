import { type FormEvent, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

export function AdminPage(){
  const [email,setEmail]=useState(""); const [lookup,setLookup]=useState("");
  const stats=useQuery({queryKey:["admin","stats"],queryFn:api.adminStats,retry:false});
  const diagnostic=useQuery({queryKey:["admin","dna",lookup],queryFn:()=>api.dnaDiagnostic(lookup),enabled:Boolean(lookup),retry:false});
  const submit=(event:FormEvent)=>{event.preventDefault();setLookup(email.trim().toLowerCase())};
  if(stats.isPending)return <section className="page"><div className="empty">Loading dashboard…</div></section>;
  if(stats.isError)return <section className="page"><div className="empty"><h2>Dashboard unavailable</h2><p>This private area is only available to configured administrators.</p></div></section>;
  const totals=stats.data.totals;
  return <section className="page admin-page"><span className="eyebrow">Private</span><h1>BookDNA dashboard</h1>
    <div className="metric-grid">{Object.entries(totals).map(([key,value])=><article key={key}><strong>{value.toLocaleString()}</strong><span>{key.replaceAll("_"," ")}</span></article>)}</div>
    <h2>Reader DNA diagnostic</h2><p>Inspect classification coverage for an active account. Private notes and passwords are never returned.</p>
    <form className="admin-lookup" onSubmit={submit}><input type="email" value={email} onChange={event=>setEmail(event.target.value)} placeholder="reader@example.com" required/><button className="button primary">Inspect DNA</button></form>
    {diagnostic.isPending&&lookup&&<p>Rebuilding and checking this reader’s DNA…</p>}{diagnostic.isError&&<p className="error">{diagnostic.error.message}</p>}
    {diagnostic.data&&<div className="settings-card"><h3>{diagnostic.data.email}</h3><p><b>{diagnostic.data.coverage_percent}% classification coverage</b> · {diagnostic.data.profile.books_shaping} books shaping · {diagnostic.data.profile.unclassified_books} need details · classifier {diagnostic.data.profile.classifier_version}</p><div className="table-wrap"><table><thead><tr><th>Book</th><th>State</th><th>Traits</th><th>Reason</th></tr></thead><tbody>{diagnostic.data.profile.completed_classifications.map(book=><tr key={book.id}><td>{book.title}</td><td>{book.state.replaceAll("_"," ")}</td><td>{book.traits.join(", ")||"—"}</td><td>{book.reason}</td></tr>)}</tbody></table></div></div>}
    <h2>Recent activity</h2><div className="table-wrap"><table><thead><tr><th>Day</th><th>Registrations</th><th>Logins</th><th>Books saved</th><th>DNA generated</th></tr></thead><tbody>{stats.data.daily.map(row=><tr key={row.day}><td>{row.day}</td><td>{row.registrations}</td><td>{row.logins}</td><td>{row.books_saved}</td><td>{row.dna_generated}</td></tr>)}</tbody></table></div>
  </section>
}
