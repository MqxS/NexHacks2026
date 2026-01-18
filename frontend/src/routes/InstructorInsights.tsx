import {useEffect, useMemo, useRef, useState} from 'react'
import {useQuery} from '@tanstack/react-query'
import {api} from '../api'
import {PaperCard} from '../components/PaperCard'
import {ChevronDown} from 'lucide-react'
import {cn} from '../lib/utils'

type RawMastery = {
  topic: string
  questions: number
  correct: number
}

type NormalizedMastery = RawMastery & {
  questionsNorm: number
  correctNorm: number
}

type Bubble = NormalizedMastery & {
  radius: number
  color: string
  x: number
  y: number
}

const splitTopic = (label: string) => {
  if (label.length <= 12) return [label]
  if (label.length <= 20 && label.includes(' ')) {
    const parts = label.split(' ')
    const mid = Math.ceil(parts.length / 2)
    return [parts.slice(0, mid).join(' '), parts.slice(mid).join(' ')]
  }
  return [label]
}

const randomInt = (min: number, max: number) =>
  Math.floor(Math.random() * (max - min + 1)) + min

const shuffle = <T,>(items: T[]) => {
  const next = [...items]
  for (let i = next.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[next[i], next[j]] = [next[j], next[i]]
  }
  return next
}

const chooseRandomSubset = (topics: string[], ratio = 0.5) => {
  if (topics.length === 0) return []
  const count = Math.max(1, Math.round(topics.length * ratio))
  return shuffle(topics).slice(0, count)
}

const createMockMastery = (topics: string[]) =>
  topics.map((topic) => ({
    topic,
    questions: randomInt(6, 36),
    correct: randomInt(35, 96)
  }))

const normalizeMastery = (items: RawMastery[]): NormalizedMastery[] => {
  if (items.length === 0) return []
  const questions = items.map((item) => item.questions)
  const correct = items.map((item) => item.correct)
  const minQuestions = Math.min(...questions)
  const maxQuestions = Math.max(...questions)
  const minCorrect = Math.min(...correct)
  const maxCorrect = Math.max(...correct)
  const normalize = (value: number, min: number, max: number) =>
    max === min ? 0.5 : (value - min) / (max - min)

  return items.map((item) => ({
    ...item,
    questionsNorm: normalize(item.questions, minQuestions, maxQuestions),
    correctNorm: normalize(item.correct, minCorrect, maxCorrect)
  }))
}

const interpolateColor = (from: number[], to: number[], amount: number) => {
  const clamped = Math.min(1, Math.max(0, amount))
  const mix = (index: number) => Math.round(from[index] + (to[index] - from[index]) * clamped)
  return `rgb(${mix(0)}, ${mix(1)}, ${mix(2)})`
}

const computeLayout = (bubbles: Omit<Bubble, 'x' | 'y'>[], width: number, height: number) => {
  const placed: Bubble[] = []
  const padding = 6
  const center = { x: width / 2, y: height / 2 }
  const sorted = [...bubbles].sort((a, b) => b.radius - a.radius)

  const isOpen = (x: number, y: number, radius: number) =>
    placed.every((bubble) => {
      const dx = bubble.x - x
      const dy = bubble.y - y
      return Math.sqrt(dx * dx + dy * dy) >= bubble.radius + radius + padding
    })

  sorted.forEach((bubble) => {
    let placedBubble: Bubble | null = null
    let angle = 0
    let spiral = 0
    for (let i = 0; i < 1600; i += 1) {
      const x = center.x + Math.cos(angle) * spiral
      const y = center.y + Math.sin(angle) * spiral
      const withinBounds =
        x - bubble.radius > padding &&
        x + bubble.radius < width - padding &&
        y - bubble.radius > padding &&
        y + bubble.radius < height - padding
      if (withinBounds && isOpen(x, y, bubble.radius)) {
        placedBubble = { ...bubble, x, y }
        break
      }
      angle += 0.35
      spiral += 0.7
    }

    if (!placedBubble) {
      const clampedX = Math.min(width - bubble.radius - padding, Math.max(bubble.radius + padding, center.x))
      const clampedY = Math.min(height - bubble.radius - padding, Math.max(bubble.radius + padding, center.y))
      placedBubble = { ...bubble, x: clampedX, y: clampedY }
    }

    placed.push(placedBubble)
  })

  return placed
}

const useElementSize = () => {
  const ref = useRef<HTMLDivElement>(null)
  const [size, setSize] = useState({ width: 720, height: 420 })

  useEffect(() => {
    if (!ref.current) return
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0]
      if (!entry) return
      const { width, height } = entry.contentRect
      setSize({ width, height })
    })
    observer.observe(ref.current)
    return () => observer.disconnect()
  }, [])

  return { ref, size }
}

export const InstructorInsights = () => {
  const { data: classes, isLoading, isError } = useQuery({
    queryKey: ['classCards'],
    queryFn: api.getClassCards
  })
  const [selectedClassId, setSelectedClassId] = useState<string>('')
  const [hovered, setHovered] = useState<{
    bubble: Bubble
    x: number
    y: number
  } | null>(null)
  const hoverTimeoutRef = useRef<number | null>(null)
  const { ref, size } = useElementSize()

  useEffect(() => {
    if (!selectedClassId && classes && classes.length > 0) {
      setSelectedClassId(classes[0].classID)
    }
  }, [classes, selectedClassId])

  const {
    data: topics,
    isLoading: topicsLoading,
    isError: topicsError
  } = useQuery({
    queryKey: ['classTopics', selectedClassId],
    queryFn: () => api.getClassTopics(selectedClassId),
    enabled: Boolean(selectedClassId)
  })

  const masteryData = useMemo(() => {
    if (!topics || topics.length === 0) return []
    const subset = chooseRandomSubset(topics, 0.5)
    const raw = createMockMastery(subset)
    return normalizeMastery(raw)
  }, [topics, selectedClassId])

  const bubbles = useMemo(() => {
    if (masteryData.length === 0) return []
    const minRadius = 18
    const densityFactor = masteryData.length > 12 ? 0.08 : 0.1
    const maxRadius = Math.min(92, Math.max(44, size.width * densityFactor))
    const mutedGreen = [130, 165, 132]
    const mutedOrange = [210, 152, 98]
    const bubbleData = masteryData.map((item) => ({
      ...item,
      radius: minRadius + (maxRadius - minRadius) * item.questionsNorm,
      color: interpolateColor(mutedOrange, mutedGreen, item.correctNorm)
    }))
    return computeLayout(bubbleData, size.width, size.height)
  }, [masteryData, size.height, size.width])

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-3">
        <h1 className="text-3xl font-semibold text-espresso">Instructor mastery map</h1>
        <p className="text-sm text-espresso/70">
          Explore concept mastery across your class.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[320px_1fr] items-stretch">
        <PaperCard className="relative min-h-[420px]">
          <div className="space-y-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-espresso/60">Class selection</p>
              <p className="mt-2 text-sm text-espresso/70">
                Choose a class to generate a mastery snapshot.
              </p>
            </div>
            <div className="relative">
              <select
                value={selectedClassId}
                onChange={(event) => setSelectedClassId(event.target.value)}
                className="w-full appearance-none rounded-xl border border-espresso/20 bg-paper px-3 py-2 text-sm text-espresso"
              >
                <option value="" disabled>
                  {isLoading ? 'Loading classes...' : 'Select a class'}
                </option>
                {(classes ?? []).map((classItem) => (
                  <option key={classItem.classID} value={classItem.classID}>
                    {classItem.Name}
                  </option>
                ))}
              </select>
              <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-xs text-espresso/50">
                <ChevronDown className="h-4 w-4" />
              </span>
            </div>
            {isError ? <p className="text-xs text-red-600">We could not load classes.</p> : null}
          </div>
          <div className="absolute bottom-6 left-0 right-0 space-y-3 pt-2 text-xs text-espresso/70">
            <div className="flex items-center justify-between pb-2">
              <span>Bubble size</span>
              <span className="font-medium text-espresso">Question Volume</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Bubble color</span>
              <span className="font-medium text-espresso">Recall Rate</span>
            </div>
            <div className="h-2 w-full rounded-full bg-gradient-to-r from-[#d29862] to-[#82a584]" />
            <div className="flex items-center justify-between text-[11px] text-espresso/60">
              <span>Lower mastery</span>
              <span>Higher mastery</span>
            </div>
          </div>
        </PaperCard>

        <PaperCard className="min-h-[420px]">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-espresso/60">Concept mastery</p>
              <h2 className="mt-1 text-lg font-semibold text-espresso">
                {selectedClassId
                  ? (classes ?? []).find((item) => item.classID === selectedClassId)?.Name ?? 'Class overview'
                  : 'Select a class'}
              </h2>
            </div>
            <div className="text-xs text-espresso/70">
              {topicsLoading ? 'Fetching topics...' : topicsError ? 'Topics unavailable' : `${bubbles.length} topics`}
            </div>
          </div>

          <div
            ref={ref}
            className={cn(
              'relative mt-6 h-[420px] w-full rounded-2xl border border-espresso/10 bg-paper/70',
              'overflow-hidden'
            )}
          >
            {bubbles.length === 0 ? (
              <div className="flex h-full items-center justify-center text-sm text-espresso/60">
                {topicsLoading
                  ? 'Loading mastery data...'
                  : selectedClassId
                    ? 'No topics available yet.'
                    : 'Select a class to view mastery.'}
              </div>
            ) : (
              <svg width="100%" height="100%" viewBox={`0 0 ${size.width} ${size.height}`}>
                {bubbles.map((bubble) => (
                  <g key={bubble.topic}>
                    <circle
                      cx={bubble.x}
                      cy={bubble.y}
                      r={hovered?.bubble.topic === bubble.topic ? bubble.radius * 1.06 : bubble.radius}
                      fill={bubble.color}
                      fillOpacity={0.85}
                      stroke="rgba(82, 56, 44, 0.2)"
                      strokeWidth={1}
                      style={{ transition: 'r 180ms ease-out' }}
                      onMouseEnter={() => {
                        if (hoverTimeoutRef.current) {
                          window.clearTimeout(hoverTimeoutRef.current)
                          hoverTimeoutRef.current = null
                        }
                        setHovered({
                          bubble,
                          x: bubble.x,
                          y: bubble.y
                        })
                      }}
                      onMouseMove={() =>
                        setHovered({
                          bubble,
                          x: bubble.x,
                          y: bubble.y
                        })
                      }
                      onMouseLeave={() => {
                        if (hoverTimeoutRef.current) window.clearTimeout(hoverTimeoutRef.current)
                        hoverTimeoutRef.current = window.setTimeout(() => setHovered(null), 160)
                      }}
                    >
                    </circle>
                    {bubble.radius > 40 ? (
                      (() => {
                        const lines = splitTopic(bubble.topic)
                        const fontSize = Math.max(9, Math.min(13, bubble.radius * 0.18))
                        const lineHeight = fontSize + 2
                        const fits = lines.length * lineHeight <= bubble.radius * 1.2
                        if (!fits && bubble.topic.length > 18) return null
                        return (
                          <text
                            x={bubble.x}
                            y={bubble.y - ((lines.length - 1) * lineHeight) / 2}
                            textAnchor="middle"
                            dominantBaseline="middle"
                            fontSize={fontSize}
                            fill="rgba(255, 255, 255, 0.92)"
                            fontWeight={600}
                          >
                            {lines.map((line, index) => (
                              <tspan key={`${bubble.topic}-${index}`} x={bubble.x} dy={index === 0 ? 0 : lineHeight}>
                                {line}
                              </tspan>
                            ))}
                          </text>
                        )
                      })()
                    ) : null}
                  </g>
                ))}
              </svg>
            )}
            {hovered ? (
              <div
                className="pointer-events-none absolute z-10 min-w-[180px] -translate-x-1/2 -translate-y-[120%] rounded-2xl border border-espresso/15 bg-paper/95 px-4 py-3 text-xs text-espresso shadow-lift"
                style={{
                  left: `${(hovered.x / size.width) * 100}%`,
                  top: `${(hovered.y / size.height) * 100}%`
                }}
              >
                <p className="text-sm font-semibold text-espresso">{hovered.bubble.topic}</p>
                <div className="mt-2 space-y-1 text-espresso/70">
                  <div className="flex items-center justify-between">
                    <span>Questions answered</span>
                    <span className="font-medium text-espresso">{hovered.bubble.questions}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Mastery</span>
                    <span className="font-medium text-espresso">{hovered.bubble.correct}%</span>
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        </PaperCard>
      </div>
    </div>
  )
}
