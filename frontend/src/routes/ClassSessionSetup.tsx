import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'
import { api } from '../api'
import { PaperCard } from '../components/PaperCard'
import { LoadingSkeleton } from '../components/LoadingSkeleton'
import { UploadDropzone } from '../components/UploadDropzone'
import { SessionCard } from '../components/SessionCard'
import { cn } from '../lib/utils'
import * as Slider from '@radix-ui/react-slider'
import * as Switch from '@radix-ui/react-switch'
import * as DropdownMenu from '@radix-ui/react-dropdown-menu'
import { ChevronDown, Flame, Snowflake, Clock, Settings, Check, X } from 'lucide-react'

export const ClassSessionSetup = () => {
  const navigate = useNavigate()
  const { classID } = useParams()
  const [sessionName, setSessionName] = useState('')
  const [difficulty, setDifficulty] = useState(0.5)
  const [topicsSelected, setTopicsSelected] = useState<string[]>([])
  const [cumulative, setCumulative] = useState(false)
  const [adaptive, setAdaptive] = useState(false)
  const [custom, setCustom] = useState('')
  const [file, setFile] = useState<File[]>([])
  const [topicSearch, setTopicSearch] = useState('')

  const { data: topics, isLoading, isError } = useQuery({
    queryKey: ['classTopics', classID],
    queryFn: () => api.getClassTopics(classID ?? ''),
    enabled: Boolean(classID)
  })

  const sessionsQuery = useQuery({
    queryKey: ['recentSessions', classID],
    queryFn: () => api.getRecentSessions(classID ?? ''),
    enabled: Boolean(classID)
  })

  const deleteSession = useMutation({
    mutationFn: (sessionID: string) => api.deleteSession({ sessionID }),
    onSuccess: () => {
      toast.success('Session deleted')
      sessionsQuery.refetch()
    },
    onError: (error: Error) => toast.error(error.message || 'Could not delete session')
  })

  const createSession = useMutation({
    mutationFn: async () => {
      if (!classID) {
        throw new Error('Missing class ID')
      }
      const formData = new FormData()
      formData.append('name', sessionName || 'New Session')
      formData.append('difficulty', String(difficulty))
      formData.append('adaptive', String(adaptive))
      formData.append('cumulative', String(cumulative))
      formData.append('customRequests', custom)
      topicsSelected.forEach((topic) => formData.append('selectedTopics', topic))
      if (file[0]) formData.append('file', file[0])
      return api.createSession(classID, formData)
    },
    onSuccess: (data) => {
      if (classID) {
        localStorage.setItem(`session:${data.sessionID}`, classID)
      }
      navigate(`/session/${data.sessionID}`)
    },
    onError: (error: Error) => toast.error(error.message || 'Could not start session')
  })

  const sessions = sessionsQuery.data ?? []

  const resumeSession = useMutation({
    mutationFn: async (sessionID: string) => {
      const params = await api.getSessionParams(sessionID)
      localStorage.setItem(`sessionParams:${sessionID}`, JSON.stringify(params))
      if (classID) {
        localStorage.setItem(`session:${sessionID}`, classID)
      }
      return sessionID
    },
    onSuccess: (sessionID) => {
      navigate(`/session/${sessionID}`)
    },
    onError: (error: Error) => toast.error(error.message || 'Could not resume session')
  })

  const processingMessage = createSession.isPending
    ? {
        title: 'Preparing your session...',
        subtitle: 'Setting up topics and pacing'
      }
    : null

  const blendColor = (start: [number, number, number], end: [number, number, number], t: number) => {
    const mix = (a: number, b: number) => Math.round(a + (b - a) * t)
    return `rgb(${mix(start[0], end[0])}, ${mix(start[1], end[1])}, ${mix(start[2], end[2])})`
  }

  const cold = [156, 183, 213] as [number, number, number]
  const edge = Math.min(1, Math.max(0, difficulty))
  const coolT = Math.min(1, edge / 0.5)
  const cool = blendColor(cold, [200, 214, 232], coolT)
  const hotStart = Math.min(100, Math.max(0, ((edge - 0.5) / 0.5) * 100))
  const gradient =
    edge <= 0.5
      ? `linear-gradient(90deg, #9CB7D5 0%, ${cool} 100%)`
      : `linear-gradient(90deg, #9CB7D5 0%, #9CB7D5 ${100 - hotStart}%, #C98B6A 100%)`

  return (
    <>
      <ProcessingOverlay active={Boolean(processingMessage)} title={processingMessage?.title} subtitle={processingMessage?.subtitle} />
      <div className="grid gap-10 lg:grid-cols-[2fr,1fr]">
      <div className="space-y-8">
        <PaperCard className="p-8">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-2xl font-semibold text-espresso">Session setup</h1>
              <p className="mt-2 text-sm text-espresso/70">Tune the session and jump right in.</p>
            </div>
          </div>

          <div className="mt-8 space-y-6">
            <div>
              <label className="text-sm font-medium text-espresso">Session name</label>
              <input
                value={sessionName}
                onChange={(event) => setSessionName(event.target.value)}
                className="mt-2 w-full rounded-xl border border-espresso/20 bg-paper px-3 py-2 text-sm placeholder:text-espresso/50"
                placeholder="Midterm review"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-espresso">Difficulty</label>
              <div className="mt-3 flex items-center gap-3">
                <Snowflake className="h-4 w-4 text-sage" />
                <Slider.Root
                  className="relative flex w-full touch-none select-none items-center"
                  value={[difficulty]}
                  max={1}
                  min={0}
                  step={0.01}
                  onValueChange={(value) => setDifficulty(value[0])}
                >
                  <Slider.Track className="relative h-2 w-full rounded-full bg-espresso/15 overflow-hidden">
                    <div
                      className="absolute inset-0 rounded-full"
                      style={{
                        background: gradient,
                        width: `${Math.max(0, Math.min(1, difficulty)) * 100}%`
                      }}
                    />
                  </Slider.Track>
                  <Slider.Thumb className="block h-5 w-5 rounded-full border border-espresso/30 bg-paper shadow-paper" />
                </Slider.Root>
                <Flame className="h-4 w-4 text-espresso" />
              </div>
            </div>

            <div>
              <label className="text-sm font-medium text-espresso">Topic focus</label>
              {isLoading ? (
                <LoadingSkeleton className="mt-3 h-10 w-full" />
              ) : isError ? (
                <p className="mt-2 text-sm text-red-600">Could not load topics.</p>
              ) : (
                <DropdownMenu.Root>
                  <DropdownMenu.Trigger asChild>
                    <button
                      type="button"
                      className="mt-2 flex w-full items-center justify-between rounded-xl border border-espresso/20 bg-paper px-3 py-2 text-sm"
                    >
                      {topicsSelected.length === 0
                        ? 'Select topics'
                        : topicsSelected.length === 1
                          ? topicsSelected[0]
                          : `${topicsSelected.length} topics`}
                      <ChevronDown className="h-4 w-4" />
                    </button>
                  </DropdownMenu.Trigger>
                  <DropdownMenu.Content
                    align="start"
                    sideOffset={8}
                    className="mt-2 w-[var(--radix-dropdown-menu-trigger-width)] rounded-xl border border-espresso/20 bg-paper p-2 shadow-paper z-50"
                  >
                    <div className="mb-2 text-[11px] text-espresso/60">Select as many as you'd like</div>
                    <input
                      value={topicSearch}
                      onChange={(event) => setTopicSearch(event.target.value)}
                      onKeyDown={(event) => event.stopPropagation()}
                      className="mb-2 w-full rounded-lg border border-espresso/20 bg-paper px-2 py-1 text-xs"
                      placeholder="Search topics"
                    />
                    <div className="max-h-56 overflow-y-auto pr-1">
                      {(topics ?? [])
                        .filter((item) => item.toLowerCase().includes(topicSearch.toLowerCase()))
                        .map((item) => {
                          const active = topicsSelected.includes(item)
                          return (
                            <DropdownMenu.Item
                              key={item}
                              className={cn(
                                'flex cursor-pointer items-center justify-between px-3 py-2 text-sm outline-none hover:bg-espresso/10',
                                active ? 'bg-sand text-espresso' : 'text-espresso'
                              )}
                              onSelect={(event) => {
                                event.preventDefault()
                                setTopicsSelected((prev) =>
                                  prev.includes(item) ? prev.filter((topicItem) => topicItem !== item) : [...prev, item]
                                )
                              }}
                            >
                              <span>{item}</span>
                              <span className="flex h-4 w-4 items-center justify-center rounded border border-espresso/20 bg-paper">
                                {active ? <Check className="h-3 w-3 text-espresso" /> : null}
                              </span>
                            </DropdownMenu.Item>
                          )
                        })}
                    </div>
                  </DropdownMenu.Content>
                </DropdownMenu.Root>
              )}
              {topicsSelected.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {topicsSelected.map((item) => (
                    <button
                      key={item}
                      type="button"
                      onClick={() => setTopicsSelected((prev) => prev.filter((topicItem) => topicItem !== item))}
                      className="group relative inline-flex items-center rounded-full border border-sage/40 bg-sage/20 px-3 py-1 text-xs text-espresso"
                    >
                      <span>{item}</span>
                      <span className="pointer-events-none absolute right-2 opacity-0 transition group-hover:opacity-100">
                        <X className="h-3 w-3 text-espresso/70" />
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div>
              <label className="text-sm font-medium text-espresso">Session style</label>
              <div className="mt-2 flex gap-2">
                <button
                  type="button"
                  onClick={() => setCumulative(false)}
                  className={cn(
                    'flex-1 rounded-full border border-espresso/20 px-3 py-2 text-sm',
                    !cumulative ? 'bg-espresso text-paper' : 'bg-paper text-espresso'
                  )}
                >
                  Isolated
                </button>
                <button
                  type="button"
                  onClick={() => setCumulative(true)}
                  className={cn(
                    'flex-1 rounded-full border border-espresso/20 px-3 py-2 text-sm',
                    cumulative ? 'bg-espresso text-paper' : 'bg-paper text-espresso'
                  )}
                >
                  Cumulative
                </button>
              </div>
              <p className="mt-2 text-xs text-espresso/60">
                Isolated uses only the selected topic. Cumulative includes prerequisite topics too.
              </p>
            </div>

            <div className="flex items-center justify-between rounded-2xl border border-espresso/15 bg-sand/50 p-4">
              <div>
                <p className="text-sm font-medium text-espresso">Adaptive mode</p>
                <p className="text-xs text-espresso/60">Adjust difficulty based on your responses.</p>
              </div>
              <Switch.Root
                checked={adaptive}
                onCheckedChange={(value) => setAdaptive(value)}
                className="relative h-6 w-11 rounded-full bg-espresso/20 data-[state=checked]:bg-sage"
              >
                <Switch.Thumb className="block h-5 w-5 translate-x-1 rounded-full bg-paper shadow transition data-[state=checked]:translate-x-5" />
              </Switch.Root>
            </div>

            <div>
              <label className="text-sm font-medium text-espresso">Custom requests</label>
              <textarea
                value={custom}
                onChange={(event) => setCustom(event.target.value)}
                className="mt-2 w-full rounded-xl border border-espresso/20 bg-paper px-3 py-2 text-sm placeholder:text-espresso/50"
                rows={3}
                placeholder="Only word problems, focus on proofs, etc."
              />
            </div>

            <div>
              <label className="text-sm font-medium text-espresso">Optional file</label>
              <UploadDropzone files={file} onFiles={setFile} multiple={false} />
            </div>

            <button
              type="button"
              onClick={() => createSession.mutate()}
              className={cn(
                'mt-4 w-full rounded-full bg-sage px-4 py-3 text-sm font-medium text-paper transition hover:-translate-y-0.5',
                'hover:-translate-y-0.5'
              )}
            >
              {createSession.isPending ? 'Starting session...' : 'Start session'}
            </button>
          </div>
        </PaperCard>

        <div>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-espresso">Recent sessions</h2>
            <span className="text-xs text-espresso/60">Keep momentum going</span>
          </div>
          {sessionsQuery.isLoading ? (
            <div className="flex gap-4 overflow-hidden">
              {[0, 1, 2].map((index) => (
                <LoadingSkeleton key={index} className="h-[160px] w-[220px]" />
              ))}
            </div>
          ) : sessionsQuery.isError || sessions.length === 0 ? (
            <PaperCard className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <span className="rounded-full bg-sand p-2 text-espresso">
                  <Clock className="h-4 w-4" />
                </span>
                <p className="text-sm text-espresso/70">No sessions yet - start one above.</p>
              </div>
            </PaperCard>
          ) : (
            <div className="scrollbar-hide flex gap-4 overflow-x-auto pb-4">
              {sessions.map((session) => (
                <SessionCard
                  key={session.sessionID}
                  title={session.name || 'Session'}
                  tags={session.topics}
                  onResume={() => resumeSession.mutate(session.sessionID)}
                  onDelete={() => deleteSession.mutate(session.sessionID)}
                />
              ))}
            </div>
          )}
        </div>
      </div>
      <div className="sticky top-28 space-y-6">
        <PaperCard>
          <h3 className="text-lg font-semibold text-espresso">Setup notes</h3>
          <p className="mt-2 text-sm text-espresso/70">
            We will remember these choices for this class. You can adjust difficulty and topics at any time during the
            session.
          </p>
        </PaperCard>
        <button
          type="button"
          onClick={() => navigate(`/class/${classID}/settings`)}
          className="flex items-center justify-between rounded-2xl border border-espresso/20 bg-paper px-4 py-3 text-sm font-medium text-espresso shadow-paper transition hover:-translate-y-0.5"
        >
          <span>Class files & settings</span>
          <span className="ml-1 flex items-center">
            <Settings className="h-4 w-4" />
          </span>
        </button>
        <PaperCard>
          <h3 className="text-lg font-semibold text-espresso">Topic metrics</h3>
          <p className="mt-2 text-sm text-espresso/70">
            Visualize your progress and optimize your study topics.
          </p>
          <button
            type="button"
            onClick={() => navigate(`/class/${classID}/metrics`)}
            className="mt-4 w-full rounded-full border border-espresso/20 bg-paper px-4 py-2 text-sm font-medium text-espresso transition hover:-translate-y-0.5"
          >
            Open
          </button>
        </PaperCard>
      </div>
      </div>
    </>
  )
}

const ProcessingOverlay = ({
  active,
  title,
  subtitle
}: {
  active: boolean
  title?: string
  subtitle?: string
}) => {
  if (!active) return null
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-espresso/30 backdrop-blur-[2px]">
      <div className="rounded-3xl border border-espresso/20 bg-paper/90 px-10 py-8 text-center shadow-lift">
        <div className="mx-auto mb-4 orbit-loader">
          <div className="orbit-ring" />
          <div className="orbit-dot" />
        </div>
        <p className="text-sm font-medium text-espresso">{title}</p>
        {subtitle ? <p className="mt-1 text-xs text-espresso/60">{subtitle}</p> : null}
      </div>
    </div>
  )
}
