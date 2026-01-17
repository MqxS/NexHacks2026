import { useEffect, useRef, useState } from 'react'
import { cn } from '../lib/utils'

export const CenteredCarousel = <T,>({
  items,
  renderItem,
  onSelect,
  initialIndex = 0
}: {
  items: T[]
  renderItem: (item: T, index: number, selected: boolean) => React.ReactNode
  onSelect?: (item: T, index: number) => void
  initialIndex?: number
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const [selectedIndex, setSelectedIndex] = useState(initialIndex)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const children = Array.from(container.children) as HTMLElement[]
    const target = children[initialIndex]
    if (target) {
      const left = target.offsetLeft - container.clientWidth / 2 + target.clientWidth / 2
      container.scrollTo({ left, behavior: 'auto' })
    }
  }, [initialIndex, items.length])

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    let timeout: number | undefined

    const handle = () => {
      if (timeout) window.clearTimeout(timeout)
      timeout = window.setTimeout(() => {
        const children = Array.from(container.children) as HTMLElement[]
        const center = container.scrollLeft + container.clientWidth / 2
        let nearestIndex = 0
        let minDistance = Number.POSITIVE_INFINITY
        children.forEach((child, index) => {
          const childCenter = child.offsetLeft + child.clientWidth / 2
          const distance = Math.abs(center - childCenter)
          if (distance < minDistance) {
            minDistance = distance
            nearestIndex = index
          }
        })
        setSelectedIndex(nearestIndex)
        const item = items[nearestIndex]
        if (item && onSelect) onSelect(item, nearestIndex)
      }, 120)
    }

    container.addEventListener('scroll', handle, { passive: true })
    return () => {
      container.removeEventListener('scroll', handle)
      if (timeout) window.clearTimeout(timeout)
    }
  }, [items, onSelect])

  return (
    <div
      ref={containerRef}
      className="scrollbar-hide flex snap-x snap-mandatory gap-6 overflow-x-auto pb-8 pt-4"
    >
      {items.map((item, index) => (
        <div
          key={index}
          className={cn(
            'snap-center transition-transform duration-200',
            index === selectedIndex ? 'scale-[1.05]' : 'scale-95'
          )}
        >
          {renderItem(item, index, index === selectedIndex)}
        </div>
      ))}
    </div>
  )
}
