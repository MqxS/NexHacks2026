import {useMemo, useState} from 'react'
import {useQuery} from '@tanstack/react-query'
import {useNavigate, useParams} from 'react-router-dom'
import {api, type TopicMetric} from '../api'
import {PaperCard} from '../components/PaperCard'
import {LoadingSkeleton} from '../components/LoadingSkeleton'
import {CenteredCarousel} from '../components/CenteredCarousel'
import {cn} from '../lib/utils'

export const StudentTopicMetrics = () => {
  const navigate = useNavigate()
  const { classID } = useParams()
  const [search, setSearch] = useState('')
  const metricsQuery = useQuery({
    queryKey: ['classMetrics', classID],
    queryFn: () => api.getMetrics(classID ?? ''),
    enabled: Boolean(classID)
  })

  const metrics = metricsQuery.data ?? []

  const filteredMetrics = useMemo(() => {
    if (!search.trim()) return metrics
    return metrics.filter((metric) => metric.topic.toLowerCase().includes(search.toLowerCase()))
  }, [metrics, search])

  const buildProgress = (metric: TopicMetric) => {
    if (metric.totalAnswers <= 0) return 0
    return Math.round((metric.rightAnswers / metric.totalAnswers) * 100)
  }

  const buildProgressGradient = (progress: number) => {
    if (progress <= 50) {
      return 'linear-gradient(to top, #d29862 0%, #d29862 100%)'
    }
    const orangeStop = Math.max(0, Math.min(100, (50 / progress) * 100))
    return `linear-gradient(to top, #d29862 0%, #d29862 ${orangeStop}%, #82a584 100%)`
  }

  return (
    <div className="space-y-6 min-h-[70vh] flex flex-col justify-center">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold text-espresso">Topic metrics</h1>
          <p className="mt-2 text-sm text-espresso/70">
            Track how each topic is trending as you practice.
          </p>
        </div>
        <button
          type="button"
          onClick={() => navigate(classID ? `/class/${classID}/session` : '/')}
          className="rounded-full border border-espresso/20 bg-paper px-4 py-2 text-sm font-medium text-espresso transition hover:-translate-y-0.5"
        >
          Back to session setup
        </button>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <label className="text-sm font-medium text-espresso">Search topics</label>
        <input
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          className="w-full max-w-sm rounded-xl border border-espresso/20 bg-paper px-3 py-2 text-sm"
          placeholder="Search by topic name"
        />
      </div>

      {metricsQuery.isLoading ? (
        <div className="flex gap-4 overflow-hidden">
          {[0, 1, 2].map((index) => (
            <LoadingSkeleton key={index} className="h-[320px] w-[220px]" />
          ))}
        </div>
      ) : filteredMetrics.length === 0 ? (
        <PaperCard className="flex items-center justify-between">
          <p className="text-sm text-espresso/70">
            {metrics.length === 0
              ? 'Start studying to see your topic metrics populate here.'
              : 'No topics match that search yet.'}
          </p>
        </PaperCard>
      ) : (
        <CenteredCarousel
          items={filteredMetrics}
          initialIndex={filteredMetrics.length === 1 ? 0 : 1}
          className="pt-10 pb-14"
          renderItem={(metric, _index, selected) => {
            const progress = buildProgress(metric)
            return (
            <PaperCard
              className={cn(
                'flex h-[380px] w-[240px] flex-col transition-transform duration-200',
                selected ? 'scale-[1.06]' : 'scale-95'
              )}
            >
              <div className="h-[64px]">
                <p className="line-clamp-2 text-sm font-semibold text-espresso">{metric.topic}</p>
                <p className="mt-1 text-xs text-espresso/60">{metric.totalAnswers} questions answered</p>
              </div>

              <div className="mt-auto flex flex-col items-center pb-6">
                <div className="relative h-[220px] w-10 overflow-hidden rounded-full border border-espresso/15 bg-paper">
                  <div
                    className="absolute bottom-0 left-0 right-0 rounded-full"
                    style={{
                      height: `${progress}%`,
                      background: buildProgressGradient(progress)
                    }}
                  />
                </div>
                <p className="mt-4 text-sm font-semibold text-espresso">{progress}% mastery</p>
              </div>
            </PaperCard>
          )}}
        />
      )}
    </div>
  )
}
