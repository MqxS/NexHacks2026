import {useEffect, useLayoutEffect, useRef, useState} from 'react'
import {cn} from '../lib/utils'

export const CenteredCarousel = <T,>({
  items,
  renderItem,
  onSelect,
  initialIndex = 0,
  className
}: {
  items: T[]
  renderItem: (item: T, index: number, selected: boolean) => React.ReactNode
  onSelect?: (item: T, index: number) => void
  initialIndex?: number
  className?: string
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const [selectedIndex, setSelectedIndex] = useState(initialIndex)

  const scrollToIndex = (index: number, behavior: ScrollBehavior = 'smooth') => {
    const container = containerRef.current
    if (!container) return
    const children = Array.from(container.children) as HTMLElement[]
    const target = children[index]
    if (!target) return
    const left = target.offsetLeft - container.clientWidth / 2 + target.clientWidth / 2
    container.scrollTo({ left, behavior })
  }

  useLayoutEffect(() => {
    const container = containerRef.current
    if (!container) return

    const children = Array.from(container.children) as HTMLElement[]
    const target = children[initialIndex]
    if (target) {
      requestAnimationFrame(() => {
        scrollToIndex(initialIndex, 'auto')
      })
    }
  }, [initialIndex, items.length])

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    let raf = 0

    const handle = () => {
      if (raf) cancelAnimationFrame(raf)
      raf = requestAnimationFrame(() => {
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
      })
    }

    container.addEventListener('scroll', handle, { passive: true })
    return () => {
      container.removeEventListener('scroll', handle)
      if (raf) cancelAnimationFrame(raf)
    }
  }, [items, onSelect])

  return (
    <div
      ref={containerRef}
      className={cn(
        'scrollbar-hide flex w-full snap-x snap-mandatory gap-10 overflow-x-auto overflow-y-visible px-[calc(50%-210px)] pb-10 pt-6',
        className
      )}
    >
      {items.map((item, index) => (
        <div
          key={index}
          className={cn(
            'shrink-0 snap-center transition-transform duration-200',
            index === selectedIndex ? 'scale-[1.10]' : 'scale-95'
          )}
          onClick={() => {
            if (index !== selectedIndex) scrollToIndex(index)
          }}
        >
          {renderItem(item, index, index === selectedIndex)}
        </div>
      ))}
    </div>
  )
}
