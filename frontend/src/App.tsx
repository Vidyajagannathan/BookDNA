import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { NavLink, Route, Routes } from 'react-router-dom'
import { Compass, Dna, Library, Moon, Search, Sun, UserRound } from 'lucide-react'
import { useUI } from './store'
import { Home } from './pages/Home'
import { Discover } from './pages/Discover'
import { LibraryPage } from './pages/LibraryPage'
import { DnaPage } from './pages/DnaPage'
import { AuthPage } from './pages/AuthPage'
import { LegalPage } from './pages/LegalPage'
import { AccountPage } from './pages/AccountPage'
import { AdminPage } from './pages/AdminPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { api } from './lib/api'

export function App() {
  const { theme, toggleTheme } = useUI()
  const session = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: api.me,
    retry: false,
    staleTime: 5 * 60_000,
  })
  useEffect(() => { document.documentElement.dataset.theme = theme }, [theme])
  return <div className="app-shell">
    <header className="topbar"><NavLink to="/" className="brand" aria-label="BookDNA home"><span>BOOK</span><i>DNA</i></NavLink><nav aria-label="Primary navigation">
      <NavLink to="/discover"><Compass size={18}/>Discover</NavLink><NavLink to="/library"><Library size={18}/>Library</NavLink><NavLink to="/dna"><Dna size={18}/>My DNA</NavLink>
    </nav><div className="header-actions"><NavLink to="/discover" className="icon-button" aria-label="Search"><Search size={19}/></NavLink><button className="icon-button" onClick={toggleTheme} aria-label={`Use ${theme === 'light' ? 'dark' : 'light'} mode`}>{theme === 'light' ? <Moon size={19}/> : <Sun size={19}/>}</button>{session.data?<NavLink to="/account" className="profile-button" aria-label={`${session.data.username}'s account`}><UserRound size={18}/>{session.data.username}</NavLink>:<NavLink to="/login" className="profile-button"><UserRound size={18}/>Sign in</NavLink>}</div></header>
    <main><Routes><Route path="/" element={<Home/>}/><Route path="/discover" element={<Discover/>}/><Route path="/search" element={<Discover/>}/><Route path="/library/*" element={<LibraryPage/>}/><Route path="/dna" element={<DnaPage/>}/><Route path="/login" element={<AuthPage mode="login"/>}/><Route path="/register" element={<AuthPage mode="register"/>}/><Route path="/account" element={<AccountPage/>}/><Route path="/admin" element={<AdminPage/>}/><Route path="/privacy" element={<LegalPage kind="privacy"/>}/><Route path="/terms" element={<LegalPage kind="terms"/>}/><Route path="*" element={<NotFoundPage/>}/></Routes></main>
    <footer><span className="brand small"><span>BOOK</span><i>DNA</i></span><p>Every book leaves a trace.</p><p><NavLink to="/privacy">Privacy</NavLink> · <NavLink to="/terms">Terms</NavLink></p></footer>
  </div>
}
