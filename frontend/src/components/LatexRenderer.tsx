import 'katex/dist/katex.min.css'
import { InlineMath, BlockMath } from 'react-katex'

const tokenize = (input: string) => {
  const tokens: Array<{ type: 'text' | 'inline' | 'block'; value: string }> = []
  let cursor = 0
  while (cursor < input.length) {
    const blockStart = input.indexOf('$$', cursor)
    const inlineStart = input.indexOf('$', cursor)

    const nextStart = [blockStart, inlineStart]
      .filter((value) => value !== -1)
      .sort((a, b) => a - b)[0]

    if (nextStart === undefined) {
      tokens.push({ type: 'text', value: input.slice(cursor) })
      break
    }

    if (nextStart > cursor) {
      tokens.push({ type: 'text', value: input.slice(cursor, nextStart) })
      cursor = nextStart
    }

    if (input.startsWith('$$', cursor)) {
      const end = input.indexOf('$$', cursor + 2)
      if (end === -1) {
        tokens.push({ type: 'text', value: input.slice(cursor) })
        break
      }
      tokens.push({ type: 'block', value: input.slice(cursor + 2, end) })
      cursor = end + 2
      continue
    }

    if (input.startsWith('$', cursor)) {
      const end = input.indexOf('$', cursor + 1)
      if (end === -1) {
        tokens.push({ type: 'text', value: input.slice(cursor) })
        break
      }
      tokens.push({ type: 'inline', value: input.slice(cursor + 1, end) })
      cursor = end + 1
    }
  }
  return tokens
}

export const LatexRenderer = ({ content, className }: { content: string; className?: string }) => {
  const tokens = tokenize(content)
  return (
    <div className={className}>
      {tokens.map((token, index) => {
        if (token.type === 'text') {
          return <span key={index}>{token.value}</span>
        }
        if (token.type === 'block') {
          return <BlockMath key={index}>{token.value}</BlockMath>
        }
        return <InlineMath key={index}>{token.value}</InlineMath>
      })}
    </div>
  )
}
