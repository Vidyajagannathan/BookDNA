import { ArrowRight, BookOpen, Sparkles, Users } from 'lucide-react'
import { Link } from 'react-router-dom'
import { DnaVisual } from '../components/DnaVisual'

export function Home() { return <>
  <section className="hero"><div className="hero-copy"><span className="eyebrow">A living portrait of your reading life</span><h1>Books shape you.<br/><em>See how.</em></h1><p>Track what you read, uncover the patterns in what you love, and meet readers whose literary fingerprint matches yours.</p><div className="hero-actions"><Link className="button primary" to="/register">Start your BookDNA <ArrowRight size={18}/></Link><Link className="text-link" to="/discover">Explore books</Link></div><div className="proof"><div className="avatars"><span>V</span><span>M</span><span>A</span><span>+</span></div><p><strong>14,200</strong> curious readers<br/>are decoding their shelves</p></div></div><div className="hero-visual"><div className="orbit one"/><div className="orbit two"/><DnaVisual compact/><span className="floating-tag tag-one">Mythology <b>+11%</b></span><span className="floating-tag tag-two">87% match with Maya</span></div></section>
  <section className="manifesto"><span>THE IDEA</span><h2>Your bookshelf is more than a list.<br/>It’s a map of <em>who you are.</em></h2><p>BookDNA turns every finish, favourite, rating and abandoned read into a nuanced portrait—without quizzes, boxes, or assumptions.</p></section>
  <section className="steps"><article><span>01</span><BookOpen/><h3>Build your shelf</h3><p>Add the books that stayed with you—and the ones that didn’t.</p></article><article><span>02</span><Sparkles/><h3>Watch your DNA form</h3><p>Your tastes resolve into themes, moods, settings and styles.</p></article><article><span>03</span><Users/><h3>Find your people</h3><p>Discover readers and books through a shared literary fingerprint.</p></article></section>
  <section className="cta"><span className="eyebrow">Your next chapter</span><h2>What does your reading<br/>say about you?</h2><Link className="button light" to="/register">Find out now <ArrowRight size={18}/></Link></section>
  </> }

