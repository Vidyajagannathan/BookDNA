import { useQuery } from '@tanstack/react-query'
import { DnaVisual } from '../components/DnaVisual'
import { api } from '../lib/api'
export function DnaPage(){ const dna=useQuery({queryKey:['dna'],queryFn:api.dna}); return <section className="page dna-page"><div className="page-heading"><span className="eyebrow">The pattern behind your pages</span><h1>Your Book<span>DNA</span></h1><p>A living model shaped by what you finish, rate, favourite, and leave behind.</p></div><DnaVisual traits={dna.data?.traits}/><div className="dna-explain"><article><strong>{dna.data?.evidence ?? 0}</strong><span>meaningful signals</span></article><article><strong>8</strong><span>trait dimensions</span></article><article><strong>∞</strong><span>ways to evolve</span></article></div></section> }

