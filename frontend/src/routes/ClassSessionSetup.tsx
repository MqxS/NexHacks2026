import { useMemo, useState } from 'react'
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
import { ChevronDown, Flame, Snowflake, Clock } from 'lucide-react'

export const ClassSessionSetup = () => {
  const navigate = useNavigate()
  const { classID } = useParams()
  const [difficulty, setDifficulty] = useState(0.5)
  const [topic, setTopic] = useState<string | null>(null)
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

  const createSession = useMutation({
    mutationFn: async () => {
      const formData = new FormData()
      const sessionParams = {
        classID,
        difficulty,
        topic,
        cumulative,
        adaptive,
        customRequests: custom
      }
      formData.append('sessionParams', JSON.stringify(sessionParams))
      if (file[0]) formData.append('file', file[0])
      return api.createSession(formData)
    },
    onSuccess: (data) => {
      if (classID) {
        localStorage.setItem(`session:${data.sessionID}`, classID)
      }
      navigate(`/session/${data.sessionID}`)
    },
    onError: (error: Error) => toast.error(error.message || 'Could not start session')
  })

  const sessions = useMemo(
    () =>
      [] as Array<{
        title: string
        tags: string[]
        onResume?: () => void
      }>,
    []
  )

  return (
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
                  <Slider.Track className="relative h-2 w-full rounded-full bg-sand">
                    <Slider.Range className="absolute h-full rounded-full bg-sage" />
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
                      {topic ?? 'Select a topic'}
                      <ChevronDown className="h-4 w-4" />
                    </button>
                  </DropdownMenu.Trigger>
                  <DropdownMenu.Content className="mt-2 w-64 rounded-xl border border-espresso/20 bg-paper p-2 shadow-paper">
                    <input
                      value={topicSearch}
                      onChange={(event) => setTopicSearch(event.target.value)}
                      className="mb-2 w-full rounded-lg border border-espresso/20 bg-paper px-2 py-1 text-xs"
                      placeholder="Search topics"
                    />
                    {(topics ?? [])
                      .filter((item) => item.toLowerCase().includes(topicSearch.toLowerCase()))
                      .map((item) => (
                      <DropdownMenu.Item
                        key={item}
                        className="cursor-pointer rounded-lg px-3 py-2 text-sm text-espresso outline-none hover:bg-sand"
                        onSelect={() => setTopic(item)}
                      >
                        {item}
                      </DropdownMenu.Item>
                    ))}
                  </DropdownMenu.Content>
                </DropdownMenu.Root>
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
            </div>

            <div className="flex items-center justify-between rounded-2xl border border-espresso/15 bg-sand/50 p-4">
              <div>
                <p className="text-sm font-medium text-espresso">Adaptive mode</p>
                <p className="text-xs text-espresso/60">Adjust difficulty based on your responses.</p>
              </div>
              <Switch.Root
                checked={adaptive}
                onCheckedChange={(value) => setAdaptive(value)}
                className="relative h-6 w-11 rounded-full bg-espresso/20 data-[state=checked]:bg-espresso"
              >
                <Switch.Thumb className="block h-5 w-5 translate-x-1 rounded-full bg-paper shadow transition data-[state=checked]:translate-x-5" />
              </Switch.Root>
            </div>

            <div>
              <label className="text-sm font-medium text-espresso">Custom requests</label>
              <textarea
                value={custom}
                onChange={(event) => setCustom(event.target.value)}
                className="mt-2 w-full rounded-xl border border-espresso/20 bg-paper px-3 py-2 text-sm"
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
                'mt-4 w-full rounded-full bg-espresso px-4 py-3 text-sm font-medium text-paper transition',
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
          {sessions.length === 0 ? (
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
                <SessionCard key={session.title} title={session.title} tags={session.tags} onResume={session.onResume} />
              ))}
            </div>
          )}
        </div>
      </div>
      <div className="space-y-6">
        <PaperCard className="sticky top-28">
          <h3 className="text-lg font-semibold text-espresso">Setup notes</h3>
          <p className="mt-2 text-sm text-espresso/70">
            We will remember these choices for this class. You can adjust difficulty and topics at any time during the
            session.
          </p>
        </PaperCard>
      </div>
    </div>
  )
}
