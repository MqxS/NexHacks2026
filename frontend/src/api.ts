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
  id: number | string
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
    return `${window.location.protocol}//${window.location.hostname}:8080`
  }
  return 'http://localhost:8080'
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
        classID: String(card.id),
        Name: card.name,
        Professor: card.professor
      }))
    )
  },
  createClass: (formData: FormData) => {
    if (isDev) {
      const classID = devId()
      const Name = String(formData.get('Name') ?? 'Untitled class')
      const Professor = String(formData.get('Professor') ?? 'Instructor')
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
    return request('/api/editClassName', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
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
    return request('/api/editClassProf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
  },
  getClassTopics: (classID: string) =>
    request<BackendTopic[]>(`/api/getClassTopics/${encodeURIComponent(classID)}`).then((topics) =>
      topics.map((topic) => topic.title)
    ),
  createSession: () => request<{ sessionID: string }>(`/api/createSession`),
  deleteClass: (payload: { classID: string }) => {
    if (isDev) {
      const next = loadDevClasses().filter((card) => card.classID !== payload.classID)
      saveDevClasses(next)
      return Promise.resolve({})
    }
    return request('/api/deleteClass', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
  },
  replaceSyllabus: (formData: FormData) =>
    request('/api/replaceSyllabus', {
      method: 'POST',
      body: formData
    }),
  uploadStyleDocs: (formData: FormData) =>
    request('/api/uploadStyleDocs', {
      method: 'POST',
      body: formData
    }),
  deleteStyleDoc: (payload: { classID: string; docID: string }) =>
    request('/api/deleteStyleDoc', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }),
  requestQuestion: (sessionID: string) =>
    request<BackendQuestion>(`/api/requestQuestion/${encodeURIComponent(sessionID)}`).then((question) => ({
      Content: question.content,
      questionID: question.questionId
    })),
  reportAnswer: (payload: { questionID: string; studentAnswer: string }) =>
    request<Feedback>(`/api/submitAnswer/${encodeURIComponent(payload.questionID)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ studentAnswer: payload.studentAnswer })
    }),
  requestHint: (payload: { questionID: string; hintRequest: string }) =>
    request<{ hint: string }>(`/api/requestHint/${encodeURIComponent(payload.questionID)}`),
  setAdaptive: (payload: { sessionID: string; active: boolean }) =>
    request(`/api/setAdaptive/${encodeURIComponent(payload.sessionID)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ active: payload.active })
    }),
  updateSessionParams: (payload: { sessionID: string; sessionParams: Record<string, unknown> }) =>
    request(`/api/updateSessionParams/${encodeURIComponent(payload.sessionID)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload.sessionParams)
    })
}
