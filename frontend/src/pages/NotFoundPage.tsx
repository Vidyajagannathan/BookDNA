import { ArrowLeft,Search } from 'lucide-react'
import { Link } from 'react-router-dom'

export function NotFoundPage(){return <section className="page not-found"><span className="eyebrow">Page not found</span><h1>This page has<br/><em>left the shelf.</em></h1><p>The address may be incomplete, outdated, or mistyped.</p><div><Link className="button primary" to="/"><ArrowLeft size={17}/> Return home</Link><Link className="button" to="/discover"><Search size={17}/> Discover books</Link></div></section>}
