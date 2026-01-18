export type ClassCard = {
  classID: string
  Name: string
  Professor: string
}

export type Question = {
  Content: string
  questionID: string
}

export type Feedback = {
  isCorrect: boolean
  correctAnswer: string
  whyIsWrong: string
}

type BackendClassCard = {
  classID: number | string
  name: string
  professor: string
}

type BackendTopic = {
  title: string
}

type BackendQuestion = {
  content: string
  questionId: string
}

type BackendSession = {
  sessionID: string
  name: string
  topics: string[]
}

type BackendSessionParams = {
  name?: string
  difficulty?: number
  classID?: string
  isCumulative?: boolean
  adaptive?: boolean
  selectedTopics?: string[]
  topics?: string[]
  topic?: string
  customRequests?: string
}

// const isDev = import.meta.env.DEV
const isDev = false
const devClassesKey = 'dev:classCards'

const loadDevClasses = (): ClassCard[] => {
  if (typeof localStorage === 'undefined') return []
  try {
    const raw = localStorage.getItem(devClassesKey)
    if (!raw) return []
    const parsed = JSON.parse(raw) as ClassCard[]
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

const saveDevClasses = (classes: ClassCard[]) => {
  if (typeof localStorage === 'undefined') return
  localStorage.setItem(devClassesKey, JSON.stringify(classes))
}

const devId = () => {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID()
  }
  return `class_${Date.now()}`
}

const resolveApiBase = () => {
  if (import.meta.env.VITE_API_BASE) return import.meta.env.VITE_API_BASE
  if (typeof window !== 'undefined') {
    if (import.meta.env.DEV) {
      return `${window.location.protocol}//${window.location.hostname}:8080`
    }
    return window.location.origin
  }
  return 'http://localhost'
}

async function request<T>(input: RequestInfo, init?: RequestInit): Promise<T> {
  const url =
    typeof input === 'string' && input.startsWith('/api/')
      ? `${resolveApiBase()}${input}`
      : input
  const response = await fetch(url, init)
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || 'Request failed')
  }
  if (response.status === 204) {
    return {} as T
  }
  const contentType = response.headers.get('content-type')
  if (contentType && contentType.includes('application/json')) {
    return response.json() as Promise<T>
  }
  return (await response.text()) as unknown as T
}

export const api = {
  getClassCards: () => {
    if (isDev) return Promise.resolve(loadDevClasses())
    return request<BackendClassCard[]>('/api/getClassCards').then((cards) =>
      cards.map((card) => ({
        classID: String(card.classID),
        Name: card.name,
        Professor: card.professor
      }))
    )
  },
  createClass: (formData: FormData) => {
    if (isDev) {
      const classID = devId()
      const Name = String(formData.get('Name') ?? formData.get('name') ?? 'Untitled class')
      const Professor = String(formData.get('Professor') ?? formData.get('professor') ?? 'Instructor')
      const next = [...loadDevClasses(), { classID, Name, Professor }]
      saveDevClasses(next)
      return Promise.resolve({ classID })
    }
    return request<{ classID: string }>('/api/createClass', {
      method: 'POST',
      body: formData
    })
  },
  editClassName: (payload: { classID: string; newName: string }) => {
    if (isDev) {
      const next = loadDevClasses().map((card) =>
        card.classID === payload.classID ? { ...card, Name: payload.newName } : card
      )
      saveDevClasses(next)
      return Promise.resolve({})
    }
    const formData = new FormData()
    formData.append('name', payload.newName)
    return request(`/api/editClassName/${encodeURIComponent(payload.classID)}`, {
      method: 'POST',
      body: formData
    })
  },
  editClassProf: (payload: { classID: string; newProf: string }) => {
    if (isDev) {
      const next = loadDevClasses().map((card) =>
        card.classID === payload.classID ? { ...card, Professor: payload.newProf } : card
      )
      saveDevClasses(next)
      return Promise.resolve({})
    }
    const formData = new FormData()
    formData.append('professor', payload.newProf)
    return request(`/api/editClassProf/${encodeURIComponent(payload.classID)}`, {
      method: 'POST',
      body: formData
    })
  },
  getClassTopics: (classID: string) =>
    request<BackendTopic[]>(`/api/getClassTopics/${encodeURIComponent(classID)}`).then((topics) =>
      topics.map((topic) => topic.title)
    ),
  getRecentSessions: (classID: string) =>
    request<BackendSession[]>(`/api/getRecentSessions/${encodeURIComponent(classID)}`),
  getSessionParams: (sessionID: string) =>
    request<BackendSessionParams>(`/api/getSessionParams/${encodeURIComponent(sessionID)}`).then((params) => {
      const topics =
        (Array.isArray(params.selectedTopics) && params.selectedTopics) ||
        (Array.isArray(params.topics) && params.topics) ||
        (params.topic ? [params.topic] : [])
      const legacy = params as { cumulative?: boolean }
      const cumulative =
        typeof params.isCumulative === 'boolean'
          ? params.isCumulative
          : typeof legacy.cumulative === 'boolean'
            ? legacy.cumulative
            : false
      return {
        name: params.name ?? 'New Session',
        difficulty: typeof params.difficulty === 'number' ? params.difficulty : 0.5,
        classID: params.classID ?? '',
        cumulative,
        adaptive: params.adaptive ?? false,
        topics,
        customRequests: params.customRequests ?? ''
      }
    }),
  createSession: (classID: string, formData: FormData) =>
    request<{ sessionID: string }>(`/api/createSession/${encodeURIComponent(classID)}`, {
      method: 'POST',
      body: formData
    }),
  deleteClass: (payload: { classID: string }) => {
    if (isDev) {
      const next = loadDevClasses().filter((card) => card.classID !== payload.classID)
      saveDevClasses(next)
      return Promise.resolve({})
    }
    return request(`/api/deleteClass/${encodeURIComponent(payload.classID)}`, {
      method: 'DELETE'
    })
  },
  replaceSyllabus: (classID: string, formData: FormData) =>
    request(`/api/replaceSyllabus/${encodeURIComponent(classID)}`, {
      method: 'POST',
      body: formData
    }),
  uploadStyleDocs: (classID: string, formData: FormData) =>
    request(`/api/uploadStyleDocs/${encodeURIComponent(classID)}`, {
      method: 'POST',
      body: formData
    }),
  deleteStyleDoc: (payload: { classID: string; docID: string }) =>
    request(
      `/api/deleteStyleDoc/${encodeURIComponent(payload.classID)}/${encodeURIComponent(payload.docID)}`,
      {
        method: 'DELETE'
      }
    ),
  getStyleDocs: (classID: string) =>
    request<Array<{ filename: string }>>(`/api/getStyleDocs/${encodeURIComponent(classID)}`),
  requestQuestion: (sessionID: string) =>
    request<BackendQuestion>(`/api/requestQuestion/${encodeURIComponent(sessionID)}`).then((question) => ({
      Content: question.content,
      questionID: question.questionId
    })),
  reportAnswer: (payload: { questionID: string; studentAnswer: string }) =>
    request<Feedback>(`/api/submitAnswer/${encodeURIComponent(payload.questionID)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ answer: payload.studentAnswer })
    }),
  requestHint: (payload: { questionID: string; hintRequest: string }) =>
    request<{ hint: string }>(`/api/requestHint/${encodeURIComponent(payload.questionID)}`),
  setAdaptive: (payload: { sessionID: string; active: boolean }) =>
    request(`/api/setAdaptive/${encodeURIComponent(payload.sessionID)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ active: payload.active })
    }),
  updateSessionParams: (payload: { sessionID: string; sessionParams: Record<string, unknown> }) => {
    const formData = new FormData()
    const params = payload.sessionParams as {
      name?: string
      difficulty?: number
      cumulative?: boolean
      topics?: string[]
      selectedTopics?: string[]
      customRequests?: string
    }
    if (params.name) formData.append('name', params.name)
    if (typeof params.difficulty === 'number') formData.append('difficulty', String(params.difficulty))
    if (typeof params.cumulative === 'boolean') formData.append('cumulative', String(params.cumulative))
    const topics = params.selectedTopics ?? params.topics ?? []
    topics.forEach((topic) => formData.append('selectedTopics', topic))
    if (typeof params.customRequests === 'string') formData.append('customRequests', params.customRequests)
    return request(`/api/updateSessionParams/${encodeURIComponent(payload.sessionID)}`, {
      method: 'POST',
      body: formData
    })
  },
  deleteSession: (payload: { sessionID: string }) =>
    request(`/api/deleteSession/${encodeURIComponent(payload.sessionID)}`, {
      method: 'DELETE'
    })
}
