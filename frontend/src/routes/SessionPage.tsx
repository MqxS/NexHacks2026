import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import * as Dialog from '@radix-ui/react-dialog'
import { useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'
import { api, type Feedback, type Question } from '../api'
import { PaperCard } from '../components/PaperCard'
import { LatexRenderer } from '../components/LatexRenderer'
import { LoadingSkeleton } from '../components/LoadingSkeleton'
import { cn } from '../lib/utils'
import * as Switch from '@radix-ui/react-switch'
import { ChevronLeft, Lightbulb, Sliders } from 'lucide-react'

type SessionParams = {
  difficulty: number
  topic: string
  cumulative: boolean
  customRequests: string
}

export const SessionPage = () => {
  const { sessionID } = useParams()
  const navigate = useNavigate()
  const [answer, setAnswer] = useState('')
  const [feedback, setFeedback] = useState<Feedback | null>(null)
  const [adaptive, setAdaptive] = useState(false)
  const [hintOpen, setHintOpen] = useState(false)
  const [hintRequest, setHintRequest] = useState('')
  const [hint, setHint] = useState<string | null>(null)
  const [panelOpen, setPanelOpen] = useState(false)
  const [exitOpen, setExitOpen] = useState(false)
  const [params, setParams] = useState<SessionParams>({
    difficulty: 0.5,
    topic: 'All topics',
    cumulative: false,
    customRequests: ''
  })
  const [savedParams, setSavedParams] = useState(params)

  const classID = useMemo(() => {
    if (!sessionID) return null
    return localStorage.getItem(`session:${sessionID}`)
  }, [sessionID])

  const questionQuery = useQuery<Question>({
    queryKey: ['session', sessionID],
    queryFn: () => api.requestQuestion(sessionID ?? ''),
    enabled: Boolean(sessionID)
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

  const nextQuestion = () => {
    setHint(null)
    setHintRequest('')
    questionQuery.refetch()
  }

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
    mutationFn: () => api.requestHint({ questionID: questionQuery.data?.questionID ?? '', hintRequest }),
    onSuccess: (data) => {
      setHint(data.hint)
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
              className="relative h-6 w-11 rounded-full bg-espresso/20 data-[state=checked]:bg-espresso"
            >
              <Switch.Thumb className="block h-5 w-5 translate-x-1 rounded-full bg-paper shadow transition data-[state=checked]:translate-x-5" />
            </Switch.Root>
          </div>
        </div>

        <PaperCard className="min-h-[220px]">
          {questionQuery.isLoading ? (
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
              <div className="mt-3 text-base text-espresso">
                <LatexRenderer content={questionQuery.data?.Content ?? ''} />
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
            <button
              type="button"
              onClick={() => setHintOpen(true)}
              disabled={!questionQuery.data}
              className="flex items-center gap-2 rounded-full border border-espresso/20 px-3 py-1 text-sm disabled:opacity-60"
            >
              <Lightbulb className="h-4 w-4" />
              Ask for hint
            </button>
            <button
              type="button"
              onClick={() => answerMutation.mutate()}
              disabled={!questionQuery.data || answer.trim().length === 0 || answerMutation.isPending}
              className={cn(
                'rounded-full bg-espresso px-4 py-2 text-sm font-medium text-paper',
                'disabled:cursor-not-allowed disabled:opacity-60'
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
                onClick={nextQuestion}
                className="rounded-full bg-espresso px-3 py-1 text-xs font-medium text-paper"
              >
                Next question
              </button>
            </div>
          </PaperCard>
        ) : null}

        {hint ? (
          <PaperCard className="border border-sage/40 bg-sand/40">
            <p className="text-xs font-semibold uppercase tracking-wide text-espresso/50">Hint</p>
            <LatexRenderer content={hint} className="mt-2 text-sm" />
          </PaperCard>
        ) : null}
      </div>

      <div className="space-y-4">
        <PaperCard className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-espresso">Session parameters</p>
            <p className="text-xs text-espresso/60">Adjust without leaving the question.</p>
          </div>
          <button
            type="button"
            onClick={() => setPanelOpen(true)}
            className="rounded-full border border-espresso/20 px-3 py-1 text-xs"
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
      </div>

      <Dialog.Root open={panelOpen} onOpenChange={setPanelOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-espresso/40 backdrop-blur-sm" />
          <Dialog.Content className="fixed right-6 top-6 w-[90vw] max-w-md rounded-2xl border border-espresso/20 bg-paper p-6 shadow-lift">
            <Dialog.Title className="text-lg font-semibold text-espresso">Adjust session</Dialog.Title>
            <div className="mt-4 space-y-4">
              <div>
                <label className="text-sm font-medium text-espresso">Difficulty</label>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.01}
                  value={params.difficulty}
                  onChange={(event) => setParams({ ...params, difficulty: Number(event.target.value) })}
                  className="mt-2 w-full"
                />
              </div>
              <div>
                <label className="text-sm font-medium text-espresso">Topic</label>
                <input
                  value={params.topic}
                  onChange={(event) => setParams({ ...params, topic: event.target.value })}
                  className="mt-2 w-full rounded-xl border border-espresso/20 bg-paper px-3 py-2 text-sm"
                />
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={params.cumulative}
                  onChange={(event) => setParams({ ...params, cumulative: event.target.checked })}
                />
                <span className="text-sm text-espresso">Cumulative</span>
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
                  'w-full rounded-full bg-espresso px-4 py-2 text-sm font-medium text-paper',
                  'disabled:cursor-not-allowed disabled:opacity-60'
                )}
              >
                {saveParams.isPending ? 'Saving...' : 'Save changes'}
              </button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>

      <Dialog.Root open={hintOpen} onOpenChange={setHintOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-espresso/40 backdrop-blur-sm" />
          <Dialog.Content className="fixed left-1/2 top-1/2 w-[90vw] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-espresso/20 bg-paper p-6 shadow-lift">
            <Dialog.Title className="text-lg font-semibold text-espresso">Request a hint</Dialog.Title>
            <Dialog.Description className="mt-1 text-sm text-espresso/70">
              Where are you stuck? What have you tried?
            </Dialog.Description>
            <textarea
              value={hintRequest}
              onChange={(event) => setHintRequest(event.target.value)}
              className="mt-3 h-24 w-full rounded-xl border border-espresso/20 bg-paper px-3 py-2 text-sm"
              placeholder="Explain your approach so far"
            />
            <button
              type="button"
              className="mt-3 w-full rounded-full border border-espresso/20 px-4 py-2 text-sm text-espresso"
            >
              Upload photo of work (coming soon)
            </button>
            <button
              type="button"
              onClick={() => hintMutation.mutate()}
              disabled={hintRequest.trim().length === 0}
              className={cn(
                'mt-4 w-full rounded-full bg-espresso px-4 py-2 text-sm font-medium text-paper',
                'disabled:cursor-not-allowed disabled:opacity-60'
              )}
            >
              {hintMutation.isPending ? 'Requesting...' : 'Get hint'}
            </button>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>

      <Dialog.Root open={exitOpen} onOpenChange={setExitOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-espresso/40 backdrop-blur-sm" />
          <Dialog.Content className="fixed left-1/2 top-1/2 w-[90vw] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-espresso/20 bg-paper p-6 shadow-lift">
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
