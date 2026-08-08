import type { Trait } from '../types'

const demo: Trait[] = [
  { id:'fantasy', name:'Fantasy', category:'Genre', score:89, confidence:.88 }, { id:'mythology', name:'Mythology', category:'Knowledge', score:81, confidence:.82 },
  { id:'intrigue', name:'Political Intrigue', category:'Theme', score:76, confidence:.78 }, { id:'academia', name:'Dark Academia', category:'Subgenre', score:71, confidence:.72 },
  { id:'classics', name:'Classics', category:'Genre', score:67, confidence:.7 }, { id:'philosophy', name:'Philosophical', category:'Style', score:54, confidence:.62 },
]

export function DnaVisual({ traits = demo, compact = false }: { traits?: Trait[]; compact?: boolean }) {
  return <div className={`dna-card ${compact ? 'compact' : ''}`}>
    <div className="dna-card-head"><div><span className="eyebrow">Your reading identity</span><h2>YOUR BOOK<span>DNA</span></h2></div><div className="confidence"><strong>{traits.length ? '86%' : '0%'}</strong><span>formed</span></div></div>
    <div className="trait-list">{traits.slice(0, compact ? 4 : 8).map((trait, i) => <div className="trait" key={trait.id} style={{'--delay': `${i * 70}ms`} as React.CSSProperties}><div className="trait-meta"><span>{trait.name}</span><b>{Math.round(trait.score)}%</b></div><div className="track"><i style={{ width: `${trait.score}%` }}/></div></div>)}</div>
    {!compact && <p className="dna-note"><span>✦</span> Your strongest signal is <b>{traits[0]?.name ?? 'still forming'}</b>. Every rating makes this portrait sharper.</p>}
  </div>
}

