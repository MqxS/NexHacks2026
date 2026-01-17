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

const isDev = import.meta.env.DEV
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

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8080'

async function request<T>(input: RequestInfo, init?: RequestInit): Promise<T> {
  const url =
    typeof input === 'string' && input.startsWith('/api/')
      ? `${API_BASE}${input}`
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
    return request<ClassCard[]>('/api/getClassCards')
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
    request<string[]>(`/api/getClassTopics(${encodeURIComponent(classID)})`),
  createSession: (formData: FormData) =>
    request<{ sessionID: string; classID?: string }>(`/api/createSession`, {
      method: 'POST',
      body: formData
    }),
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
    request<Question>(`/api/requestQuestion(${encodeURIComponent(sessionID)})`),
  reportAnswer: (payload: { questionID: string; studentAnswer: string }) =>
    request<Feedback>(
      `/api/reportAnswer(${payload.questionID},${encodeURIComponent(payload.studentAnswer)})`,
      { method: 'POST' }
    ),
  requestHint: (payload: { questionID: string; hintRequest: string }) =>
    request<{ hint: string }>(
      `/api/requestHint(${payload.questionID},${encodeURIComponent(payload.hintRequest)})`,
      { method: 'POST' }
    ),
  setAdaptive: (payload: { sessionID: string; active: boolean }) =>
    request(`/api/setAdaptive(${encodeURIComponent(payload.sessionID)},${payload.active})`, { method: 'POST' }),
  updateSessionParams: (payload: { sessionID: string; sessionParams: Record<string, unknown> }) =>
    request(`/api/updateSessionParams(${encodeURIComponent(payload.sessionID)})`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload.sessionParams)
    })
}
