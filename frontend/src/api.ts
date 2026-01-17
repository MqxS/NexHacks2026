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

async function request<T>(input: RequestInfo, init?: RequestInit): Promise<T> {
  const response = await fetch(input, init)
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
  getClassCards: () => request<ClassCard[]>('/api/getClassCards'),
  createClass: (formData: FormData) =>
    request<{ classID: string }>('/api/createClass', {
      method: 'POST',
      body: formData
    }),
  editClassName: (payload: { classID: string; newName: string }) =>
    request('/api/editClassName', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }),
  editClassProf: (payload: { classID: string; newProf: string }) =>
    request('/api/editClassProf', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }),
  getClassTopics: (classID: string) =>
    request<string[]>(`/api/getClassTopics(${encodeURIComponent(classID)})`),
  createSession: (formData: FormData) =>
    request<{ sessionID: string; classID?: string }>(`/api/createSession`, {
      method: 'POST',
      body: formData
    }),
  deleteClass: (payload: { classID: string }) =>
    request('/api/deleteClass', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }),
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
