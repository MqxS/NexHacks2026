import {useEffect, useLayoutEffect, useMemo, useRef, useState} from 'react'
import {useMutation, useQuery, useQueryClient} from '@tanstack/react-query'
import * as Dialog from '@radix-ui/react-dialog'
import {useNavigate, useParams} from 'react-router-dom'
import {toast} from 'sonner'
import {api, type Feedback, type Question} from '../api'
import {PaperCard} from '../components/PaperCard'
import {LatexRenderer} from '../components/LatexRenderer'
import {LoadingSkeleton} from '../components/LoadingSkeleton'
import {cn} from '../lib/utils'
import * as Switch from '@radix-ui/react-switch'
import * as DropdownMenu from '@radix-ui/react-dropdown-menu'
import * as Slider from '@radix-ui/react-slider'
import { ChevronDown, ChevronLeft, Lightbulb, Sliders, Check } from 'lucide-react'

type SessionParams = {
  difficulty: number
  topics: string[]
  cumulative: boolean
  customRequests: string
}

export const SessionPage = () => {
  const { sessionID } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [answer, setAnswer] = useState('')
  const [feedback, setFeedback] = useState<Feedback | null>(null)
  const [adaptive, setAdaptive] = useState(false)
  const [hintRequest, setHintRequest] = useState('')
  const [hints, setHints] = useState<string[]>([])
  const [hintPhoto, setHintPhoto] = useState<File | null>(null)
  const [panelOpen, setPanelOpen] = useState(false)
  const [exitOpen, setExitOpen] = useState(false)
  const [topicSearch, setTopicSearch] = useState('')
  const [questionFontSize, setQuestionFontSize] = useState(20)
  const questionRef = useRef<HTMLDivElement | null>(null)
  const [params, setParams] = useState<SessionParams>({
    difficulty: 0.5,
    topics: [],
    cumulative: false,
    customRequests: ''
  })
  const [savedParams, setSavedParams] = useState(params)

  const blendColor = (start: [number, number, number], end: [number, number, number], t: number) => {
    const mix = (a: number, b: number) => Math.round(a + (b - a) * t)
    return `rgb(${mix(start[0], end[0])}, ${mix(start[1], end[1])}, ${mix(start[2], end[2])})`
  }

  const cold = [156, 183, 213] as [number, number, number]
  const difficultyValue = Number.isFinite(params.difficulty) ? params.difficulty : 0
  const edge = Math.min(1, Math.max(0, difficultyValue))
  const coolT = Math.min(1, edge / 0.5)
  const cool = blendColor(cold, [200, 214, 232], coolT)
  const hotStart = Math.min(100, Math.max(0, ((edge - 0.5) / 0.5) * 100))
  const gradient =
    edge <= 0.5
      ? `linear-gradient(90deg, #9CB7D5 0%, ${cool} 100%)`
      : `linear-gradient(90deg, #9CB7D5 0%, #9CB7D5 ${100 - hotStart}%, #C98B6A 100%)`

  const classID = useMemo(() => {
    if (!sessionID) return null
    return localStorage.getItem(`session:${sessionID}`)
  }, [sessionID])

  const questionQuery = useQuery<Question>({
    queryKey: ['session', sessionID],
    queryFn: () => api.requestQuestion(sessionID ?? ''),
    enabled: Boolean(sessionID)
  })

  const sessionParamsQuery = useQuery({
    queryKey: ['sessionParams', sessionID],
    queryFn: () => api.getSessionParams(sessionID ?? ''),
    enabled: Boolean(sessionID)
  })

  useEffect(() => {
    if (sessionParamsQuery.status !== 'success') return
    const parsed = sessionParamsQuery.data as Partial<SessionParams> & {
      adaptive?: boolean
    }
    setParams((prev) => ({ ...prev, ...parsed }))
    setSavedParams((prev) => ({ ...prev, ...parsed }))
    if (typeof parsed.adaptive === 'boolean') {
      setAdaptive(parsed.adaptive)
    }
  }, [sessionParamsQuery.status, sessionParamsQuery.data])

  const topicsQuery = useQuery({
    queryKey: ['classTopics', classID],
    queryFn: () => api.getClassTopics(classID ?? ''),
    enabled: Boolean(classID)
  })

  useEffect(() => {
    setFeedback(null)
    setAnswer('')
  }, [questionQuery.data?.questionID])

  const answerMutation = useMutation({
    mutationFn: () => api.reportAnswer({ questionID: questionQuery.data?.questionID ?? '', studentAnswer: answer }),
    onSuccess: (data) => setFeedback(data),
    onError: (error: Error) => toast.error(error.message || 'Could not submit answer')
  })

  const nextQuestionMutation = useMutation({
    mutationFn: () => api.requestQuestion(sessionID ?? ''),
    onMutate: () => {
      setHints([])
      setHintRequest('')
      setFeedback(null)
      setAnswer('')
    },
    onSuccess: (data) => {
      queryClient.setQueryData(['session', sessionID], data)
    },
    onError: (error: Error) => toast.error(error.message || 'Could not load next question')
  })

  useLayoutEffect(() => {
    const element = questionRef.current
    if (!element) return

    const sizes = [30, 28, 26, 24, 22, 20, 18]

    const evaluate = () => {
      for (const size of sizes) {
        element.style.fontSize = `${size}px`
        if (element.scrollHeight <= element.clientHeight + 4) {
          setQuestionFontSize(size)
          return
        }
      }
      setQuestionFontSize(14)
    }

    const raf = requestAnimationFrame(evaluate)
    const observer = new ResizeObserver(() => {
      requestAnimationFrame(evaluate)
    })
    observer.observe(element)

    return () => {
      cancelAnimationFrame(raf)
      observer.disconnect()
    }
  }, [questionQuery.data?.Content, nextQuestionMutation.isPending])

  const adaptiveMutation = useMutation({
    mutationFn: (value: boolean) => api.setAdaptive({ sessionID: sessionID ?? '', active: value }),
    onError: (error: Error, value) => {
      setAdaptive(!value)
      toast.error(error.message || 'Could not update adaptive mode')
    }
  })

  const saveParams = useMutation({
    mutationFn: () => api.updateSessionParams({ sessionID: sessionID ?? '', sessionParams: params }),
    onSuccess: () => {
      setSavedParams(params)
      toast.success('Session updated')
    },
    onError: (error: Error) => toast.error(error.message || 'Could not update session')
  })

  const hintMutation = useMutation({
    mutationFn: () =>
      api.requestHint({ questionID: questionQuery.data?.questionID ?? '', hintRequest, photo: hintPhoto }),
    onSuccess: (data) => {
      setHints((prev) => [...prev, data.hint])
      setHintRequest('')
      setHintPhoto(null)
      toast.success('Hint delivered')
    },
    onError: (error: Error) => toast.error(error.message || 'Could not request hint')
  })

  const hasUnsaved = JSON.stringify(params) !== JSON.stringify(savedParams)

  return (
    <div className="grid gap-8 lg:grid-cols-[1fr,300px]">
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <button
            type="button"
            onClick={() => setExitOpen(true)}
            className="flex items-center gap-2 rounded-full border border-espresso/20 bg-paper px-3 py-1 text-sm text-espresso"
          >
            <ChevronLeft className="h-4 w-4" />
            Exit session
          </button>
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-espresso/70">Adaptive</span>
            <Switch.Root
              checked={adaptive}
              onCheckedChange={(value) => {
                setAdaptive(value)
                adaptiveMutation.mutate(value)
              }}
              className="relative h-6 w-11 rounded-full bg-espresso/20 data-[state=checked]:bg-sage"
            >
              <Switch.Thumb className="block h-5 w-5 translate-x-1 rounded-full bg-paper shadow transition data-[state=checked]:translate-x-5" />
            </Switch.Root>
          </div>
        </div>

        <PaperCard className="min-h-[220px]">
          {questionQuery.isLoading || nextQuestionMutation.isPending ? (
            <LoadingSkeleton className="h-40 w-full" />
          ) : questionQuery.isError ? (
            <div className="flex items-center justify-between">
              <p className="text-sm text-espresso/70">We could not load a question.</p>
              <button
                type="button"
                onClick={() => questionQuery.refetch()}
                className="rounded-full border border-espresso/20 px-3 py-1 text-sm"
              >
                Retry
              </button>
            </div>
          ) : (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-espresso/50">Question</p>
              <div className="mt-3 text-espresso">
                <div ref={questionRef} className="max-h-[240px] overflow-hidden" style={{ fontSize: questionFontSize }}>
                  <LatexRenderer content={questionQuery.data?.Content ?? ''} className="leading-relaxed" />
                </div>
              </div>
            </div>
          )}
        </PaperCard>

        <PaperCard>
          <p className="text-xs font-semibold uppercase tracking-wide text-espresso/50">Your answer</p>
          <textarea
            value={answer}
            onChange={(event) => setAnswer(event.target.value)}
            className="mt-3 h-28 w-full rounded-xl border border-espresso/20 bg-paper px-3 py-2 text-sm"
            placeholder="Type your answer here..."
          />
          <div className="mt-3 flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs text-espresso/60">
              <Lightbulb className="h-4 w-4" />
              Hint panel is on the right
            </div>
            <button
              type="button"
              onClick={() => answerMutation.mutate()}
              disabled={
                !questionQuery.data ||
                answer.trim().length === 0 ||
                answerMutation.isPending ||
                Boolean(feedback)
              }
              className={cn(
                'rounded-full border border-espresso/20 bg-espresso px-4 py-2 text-sm font-medium text-paper',
                'disabled:cursor-not-allowed disabled:bg-espresso/40 disabled:text-paper/70'
              )}
            >
              {answerMutation.isPending ? 'Submitting...' : 'Submit answer'}
            </button>
          </div>
        </PaperCard>

        {feedback ? (
          <PaperCard className={cn(feedback.isCorrect ? 'border-green-500/40 bg-green-50/40' : 'border-red-500/40')}>
            <div className="flex items-start justify-between">
              <div>
                <h3 className={cn('text-lg font-semibold', feedback.isCorrect ? 'text-green-800' : 'text-red-800')}>
                  {feedback.isCorrect ? 'Correct' : 'Not quite'}
                </h3>
                {feedback.isCorrect ? (
                  <p className="mt-2 text-sm text-espresso/70">Nice work. Keep the momentum going.</p>
                ) : (
                  <div className="mt-3 space-y-3 text-sm text-espresso">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-espresso/50">Correct answer</p>
                      <LatexRenderer content={feedback.correctAnswer} className="mt-2" />
                    </div>
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-espresso/50">Why your answer is wrong</p>
                      <LatexRenderer content={feedback.whyIsWrong} className="mt-2" />
                    </div>
                  </div>
                )}
              </div>
              <button
                type="button"
                onClick={() => nextQuestionMutation.mutate()}
                disabled={nextQuestionMutation.isPending}
                className="rounded-full bg-espresso px-3 py-1 text-xs font-medium text-paper"
              >
                {nextQuestionMutation.isPending ? 'Loading...' : 'Next question'}
              </button>
            </div>
          </PaperCard>
        ) : null}

      </div>

      <div className="space-y-4">
        <PaperCard className="pr-4 pb-6">
          <div>
            <p className="text-sm font-medium text-espresso">Session parameters</p>
            <p className="mt-1 text-xs text-espresso/60">Adjust without leaving the question.</p>
          </div>
          <div className="h-6" aria-hidden />
          <button
            type="button"
            onClick={() => setPanelOpen(true)}
            className="w-fit rounded-full border border-espresso/20 px-3 py-1 text-sm"
          >
            <span className="inline-flex items-center gap-2">
              <Sliders className="h-3 w-3" />
              Edit
            </span>
          </button>
        </PaperCard>

        {hasUnsaved ? (
          <PaperCard className="border border-sage/40 bg-sand/40">
            <p className="text-sm text-espresso">Unsaved changes</p>
            <p className="text-xs text-espresso/60">Open the panel to save updates.</p>
          </PaperCard>
        ) : null}

        <PaperCard>
          <p className="text-sm font-medium text-espresso">Ask for a hint</p>
          <p className="mt-1 text-xs text-espresso/60">Get the help you need.</p>
          <textarea
            value={hintRequest}
            onChange={(event) => setHintRequest(event.target.value)}
            className="mt-3 h-24 w-full rounded-xl border border-espresso/20 bg-paper px-3 py-2 text-sm"
            placeholder="Where are you stuck? What have you tried?"
          />
          <div className="mt-3 rounded-2xl border border-espresso/15 bg-sand/40 p-3">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-medium text-espresso">Upload photo of work</p>
                <p className="text-[11px] text-espresso/60">Optional. We will attach it to your hint request.</p>
              </div>
              <label className="cursor-pointer rounded-full border border-espresso/20 bg-paper px-3 py-1 text-xs text-espresso">
                Upload
                <input
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={(event) => {
                    const file = event.target.files?.[0] ?? null
                    setHintPhoto(file)
                    event.target.value = ''
                  }}
                />
              </label>
            </div>
            {hintPhoto ? (
              <div className="mt-2 flex items-center justify-between rounded-xl border border-espresso/10 bg-paper px-3 py-2">
                <span className="text-xs text-espresso">{hintPhoto.name}</span>
                <button
                  type="button"
                  onClick={() => setHintPhoto(null)}
                  className="text-[11px] text-espresso/60 hover:text-espresso"
                >
                  Remove
                </button>
              </div>
            ) : null}
          </div>
          <button
            type="button"
            onClick={() => hintMutation.mutate()}
            disabled={!questionQuery.data || hintRequest.trim().length === 0}
            className={cn(
              'mt-4 w-full rounded-full bg-sage px-4 py-2 text-sm font-medium text-paper',
              'disabled:cursor-not-allowed disabled:opacity-60'
            )}
          >
            {hintMutation.isPending ? 'Requesting...' : 'Get hint'}
          </button>
        </PaperCard>

        {hints.length > 0 ? (
          <PaperCard className="border border-sage/40 bg-sand/40">
            <p className="text-xs font-semibold uppercase tracking-wide text-espresso/50">Hints</p>
            <div className="mt-3 space-y-3 text-sm text-espresso">
              {hints.map((item, index) => (
                <div key={`${item}-${index}`} className="rounded-xl border border-espresso/10 bg-paper/70 p-3">
                  <LatexRenderer content={item} className="text-sm" />
                </div>
              ))}
            </div>
          </PaperCard>
        ) : null}
      </div>

      <Dialog.Root open={panelOpen} onOpenChange={setPanelOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-50 bg-espresso/40 backdrop-blur-[1px]" />
          <Dialog.Content className="fixed right-6 top-6 z-50 w-[90vw] max-w-md rounded-2xl border border-espresso/20 bg-paper p-6 shadow-lift">
            <Dialog.Title className="text-lg font-semibold text-espresso">Adjust session</Dialog.Title>
            <div className="mt-4 space-y-4">
              <div>
                <label className="text-sm font-medium text-espresso">Difficulty</label>
                <Slider.Root
                  className="relative mt-3 flex w-full touch-none select-none items-center"
                  value={[params.difficulty]}
                  max={1}
                  min={0}
                  step={0.01}
                  onValueChange={(value) => setParams({ ...params, difficulty: value[0] })}
                >
                  <Slider.Track className="relative h-2 w-full rounded-full bg-espresso/15 overflow-hidden">
                    <div
                      className="absolute inset-0 rounded-full"
                      style={{
                        background: gradient,
                        width: `${edge * 100}%`
                      }}
                    />
                  </Slider.Track>
                  <Slider.Thumb className="block h-5 w-5 rounded-full border border-espresso/30 bg-paper shadow-paper" />
                </Slider.Root>
              </div>
              <div>
                <label className="text-sm font-medium text-espresso">Topic</label>
                <DropdownMenu.Root>
                  <DropdownMenu.Trigger asChild>
                    <button
                      type="button"
                      className="mt-2 flex w-full items-center justify-between rounded-xl border border-espresso/20 bg-paper px-3 py-2 text-sm"
                    >
                      {params.topics.length === 0
                        ? 'Select topics'
                        : params.topics.length === 1
                          ? params.topics[0]
                          : `${params.topics.length} topics`}
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
                      {(topicsQuery.data ?? [])
                        .filter((item: string) => item.toLowerCase().includes(topicSearch.toLowerCase()))
                        .map((item: string) => {
                          const active = params.topics.includes(item)
                          return (
                            <DropdownMenu.Item
                              key={item}
                              className={cn(
                                'flex cursor-pointer items-center justify-between px-3 py-2 text-sm outline-none hover:bg-espresso/10',
                                active ? 'bg-sand text-espresso' : 'text-espresso'
                              )}
                              onSelect={(event) => {
                                event.preventDefault()
                                setParams((prev) => ({
                                  ...prev,
                                  topics: prev.topics.includes(item)
                                    ? prev.topics.filter((topicItem) => topicItem !== item)
                                    : [...prev.topics, item]
                                }))
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
                    {topicsQuery.data && topicsQuery.data.length === 0 ? (
                      <div className="px-3 py-2 text-xs text-espresso/60">No topics available</div>
                    ) : null}
                  </DropdownMenu.Content>
                </DropdownMenu.Root>
                {params.topics.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {params.topics.map((item) => (
                      <button
                        key={item}
                        type="button"
                        onClick={() =>
                          setParams((prev) => ({
                            ...prev,
                            topics: prev.topics.filter((topicItem) => topicItem !== item)
                          }))
                        }
                      className="rounded-full border border-sage/40 bg-sage/20 px-3 py-1 text-xs text-espresso"
                      >
                        {item}
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
                    onClick={() => setParams({ ...params, cumulative: false })}
                    className={cn(
                      'flex-1 rounded-full border border-espresso/20 px-3 py-2 text-sm',
                      !params.cumulative ? 'bg-espresso text-paper' : 'bg-paper text-espresso'
                    )}
                  >
                    Isolated
                  </button>
                  <button
                    type="button"
                    onClick={() => setParams({ ...params, cumulative: true })}
                    className={cn(
                      'flex-1 rounded-full border border-espresso/20 px-3 py-2 text-sm',
                      params.cumulative ? 'bg-espresso text-paper' : 'bg-paper text-espresso'
                    )}
                  >
                    Cumulative
                  </button>
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-espresso">Custom requests</label>
                <textarea
                  value={params.customRequests}
                  onChange={(event) => setParams({ ...params, customRequests: event.target.value })}
                  className="mt-2 w-full rounded-xl border border-espresso/20 bg-paper px-3 py-2 text-sm"
                  rows={3}
                />
              </div>
              <button
                type="button"
                disabled={!hasUnsaved}
                onClick={() => saveParams.mutate()}
                className={cn(
                  'w-full rounded-full bg-sage px-4 py-2 text-sm font-medium text-paper',
                  'disabled:cursor-not-allowed disabled:opacity-60'
                )}
              >
                {saveParams.isPending ? 'Saving...' : 'Save changes'}
              </button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>

      <Dialog.Root open={exitOpen} onOpenChange={setExitOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-50 bg-espresso/40 backdrop-blur-[2px]" />
          <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[90vw] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-espresso/20 bg-paper p-6 shadow-lift">
            <Dialog.Title className="text-lg font-semibold text-espresso">Leave session?</Dialog.Title>
            <Dialog.Description className="mt-1 text-sm text-espresso/70">
              Your progress is saved. You can return later.
            </Dialog.Description>
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setExitOpen(false)}
                className="rounded-full border border-espresso/20 px-3 py-2 text-sm"
              >
                Stay
              </button>
              <button
                type="button"
                onClick={() => navigate(classID ? `/class/${classID}/session` : '/')}
                className="rounded-full bg-espresso px-3 py-2 text-sm font-medium text-paper"
              >
                Leave
              </button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  )
}
