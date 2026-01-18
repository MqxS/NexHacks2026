import type {ReactNode} from 'react'
import {Route, Routes, useLocation, useNavigate, useParams} from 'react-router-dom'
import {Home} from './routes/Home'
import {ClassSessionSetup} from './routes/ClassSessionSetup'
import {ClassSettings} from './routes/ClassSettings'
import {SessionPage} from './routes/SessionPage'
import {InstructorInsights} from './routes/InstructorInsights'
import {cn} from './lib/utils'
import { Home as HomeIcon, Settings } from 'lucide-react'
import { AnimatePresence, motion } from 'framer-motion'
import appIcon from './assets/icons/icon-nobg.png'
import geminiLogo from './assets/logos/gemini.svg'
import wolframLogo from './assets/logos/wolframalpha.svg'
import tokenLogo from './assets/logos/the-token-company.ico'
import traeLogo from './assets/logos/trae.png'

const Breadcrumbs = () => {
  const location = useLocation()
  const params = useParams()
  const navigate = useNavigate()
  const segments = location.pathname.split('/').filter(Boolean)

  const crumbs: { label: string; path?: string }[] = [{ label: 'Home', path: '/' }]

  if (segments[0] === 'class' && params.classID) {
    crumbs.push({ label: 'Class', path: `/class/${params.classID}/session` })
    if (segments[2] === 'settings') {
      crumbs.push({ label: 'Settings' })
    } else {
      crumbs.push({ label: 'Session' })
    }
  }

  if (segments[0] === 'session' && params.sessionID) {
    crumbs.push({ label: 'Session' })
  }

  return (
    <div className="flex items-center gap-2 text-sm text-espresso/70">
      {crumbs.slice(1).map((crumb, index) => (
        <button
          key={`${crumb.label}-${index}`}
          type="button"
          className={cn('transition hover:text-espresso', !crumb.path && 'cursor-default')}
          onClick={() => crumb.path && navigate(crumb.path)}
          disabled={!crumb.path}
        >
          {crumb.label}
          {index < crumbs.length - 2 ? <span className="mx-2 text-espresso/40">/</span> : null}
        </button>
      ))}
    </div>
  )
}

const SettingsButton = () => {
  const location = useLocation()
  const params = useParams()
  const navigate = useNavigate()
  const isClassScoped = location.pathname.startsWith('/class/')
  if (!isClassScoped || !params.classID) return null

  return (
    <button
      type="button"
      className="flex items-center gap-2 rounded-full border border-espresso/20 bg-paper px-3 py-1 text-sm text-espresso shadow-paper transition hover:-translate-y-0.5"
      onClick={() => navigate(`/class/${params.classID}/settings`)}
    >
      <Settings className="h-4 w-4" />
      Settings
    </button>
  )
}

const HomeButton = () => {
  const navigate = useNavigate()
  return (
    <button
      type="button"
      className="flex h-11 w-11 items-center justify-center rounded-full border border-espresso/20 bg-paper text-espresso shadow-paper transition hover:-translate-y-0.5"
      onClick={() => navigate('/')}
      aria-label="Home"
    >
      <HomeIcon className="h-5 w-5" />
    </button>
  )
}

const Shell = ({ children }: { children: ReactNode }) => {
  return (
    <div className="app-shell relative flex min-h-screen flex-col">
      <div className="noise-overlay" />
      <header className="sticky top-0 z-20 border-b border-espresso/10 bg-paper/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-2">
          <div className="flex items-center gap-4">
            <div className="h-16 w-24 overflow-hidden rounded-3xl">
              <img
                src={appIcon}
                alt="Sophi"
                className="h-full w-full object-cover object-[center_50%] shadow-paper"
              />
            </div>
            <Breadcrumbs />
          </div>
          <div className="flex items-center gap-3">
            <SettingsButton />
            <HomeButton />
          </div>
        </div>
      </header>
      <main className="relative mx-auto w-full max-w-6xl flex-1 px-6 pb-16 pt-10">{children}</main>
      <footer className="border-t border-espresso/10 bg-paper/80 backdrop-blur">
        <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center justify-between gap-4 px-6 py-4 text-xs text-espresso/70">
          <div>
            Made with ❤️ at{' '}
            <a
              href="https://nexhacks.com"
              className="font-medium text-espresso underline underline-offset-4"
              target="_blank"
              rel="noreferrer"
            >
              NexHacks
            </a>
            .
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-espresso/60">Powered by</span>
            <a
              href="https://deepmind.google/technologies/gemini/"
              className="flex items-center gap-2 rounded-full border border-espresso/15 bg-paper px-3 py-1 transition hover:-translate-y-0.5"
              target="_blank"
              rel="noreferrer"
            >
              <img src={geminiLogo} alt="Google Gemini" className="h-5 w-5" />
              <span className="text-espresso">Google Gemini</span>
            </a>
            <a
              href="https://www.wolframalpha.com/"
              className="flex items-center gap-2 rounded-full border border-espresso/15 bg-paper px-3 py-1 transition hover:-translate-y-0.5"
              target="_blank"
              rel="noreferrer"
            >
              <img src={wolframLogo} alt="WolframAlpha" className="h-5 w-5" />
              <span className="text-espresso">WolframAlpha</span>
            </a>
            <a
              href="https://thetokencompany.com/"
              className="flex items-center gap-2 rounded-full border border-espresso/15 bg-paper px-3 py-1 transition hover:-translate-y-0.5"
              target="_blank"
              rel="noreferrer"
            >
              <img src={tokenLogo} alt="The Token Company" className="h-5 w-5" />
              <span className="text-espresso">The Token Company</span>
            </a>
            <a
              href="https://www.trae.ai/"
              className="flex items-center gap-2 rounded-full border border-espresso/15 bg-paper px-3 py-1 transition hover:-translate-y-0.5"
              target="_blank"
              rel="noreferrer"
            >
              <img src={traeLogo} alt="TRAE" className="h-5 w-5" />
              <span className="text-espresso">TRAE</span>
            </a>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default function App() {
  const location = useLocation()
  return (
    <Shell>
      <AnimatePresence mode="wait">
        <Routes location={location} key={location.pathname}>
          <Route path="/" element={<Page><Home /></Page>} />
          <Route path="/instructor" element={<Page><InstructorInsights /></Page>} />
          <Route path="/class/:classID/session" element={<Page><ClassSessionSetup /></Page>} />
          <Route path="/class/:classID/settings" element={<Page><ClassSettings /></Page>} />
          <Route path="/session/:sessionID" element={<Page><SessionPage /></Page>} />
        </Routes>
      </AnimatePresence>
    </Shell>
  )
}

const Page = ({ children }: { children: ReactNode }) => (
  <motion.div
    initial={{ opacity: 0, y: 12 }}
    animate={{ opacity: 1, y: 0 }}
    exit={{ opacity: 0, y: -12 }}
    transition={{ duration: 0.2, ease: 'easeOut' }}
  >
    {children}
  </motion.div>
)
