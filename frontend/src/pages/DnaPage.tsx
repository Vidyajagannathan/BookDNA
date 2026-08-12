import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Dna } from 'lucide-react'
import { DnaVisual } from '../components/DnaVisual'
import { api } from '../lib/api'

export function DnaPage(){
  const session=useQuery({queryKey:['auth','me'],queryFn:api.me,retry:false})
  const dna=useQuery({queryKey:['dna'],queryFn:api.dna,enabled:Boolean(session.data)})
  if(session.isPending)return <section className="page"><div className="empty">Loading…</div></section>
  if(!session.data)return <section className="page"><div className="empty"><Dna/><h1>Sign in to reveal your BookDNA</h1><p>Your DNA is private and forms from the books you read, rate, favourite, and leave unfinished.</p><Link className="button primary" to="/login?next=/dna">Sign in</Link> <Link className="button" to="/register?next=/dna">Create account</Link></div></section>
  return <section className="page dna-page"><div className="page-heading"><span className="eyebrow">The pattern behind your pages</span><h1>Your Book<span>DNA</span></h1><p>A transparent portrait based on the reading choices in your Library.</p></div><DnaVisual traits={dna.data?.traits||[]} profileConfidence={dna.data?.profile_confidence||0} confidenceLabel={dna.data?.confidence_label||'Early'}/><div className="dna-explain"><article><strong>{dna.data?.books_shaping??0}</strong><span>books shaping your DNA</span></article><article><strong>{dna.data?.active_traits??0}</strong><span>supported traits</span></article><article><strong>{dna.data?.active_categories??0}</strong><span>reading categories</span></article></div><p className="metric-explanation">Profile confidence grows from completed and rated books, repeated support for traits, and breadth across reading categories. It is not a judgment of how “complete” you are.</p></section>
}
