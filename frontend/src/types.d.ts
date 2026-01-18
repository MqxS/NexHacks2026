declare module 'react-katex' {
    import type {ComponentType} from 'react'

    export const InlineMath: ComponentType<{ children?: string }>
  export const BlockMath: ComponentType<{ children?: string }>
}
