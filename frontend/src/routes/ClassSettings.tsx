import {useMemo, useState} from 'react'
import {useMutation, useQuery} from '@tanstack/react-query'
import * as Dialog from '@radix-ui/react-dialog'
import {useNavigate, useParams} from 'react-router-dom'
import {toast} from 'sonner'
import {api} from '../api'
import {PaperCard} from '../components/PaperCard'
import {UploadDropzone} from '../components/UploadDropzone'
import {cn} from '../lib/utils'

export const ClassSettings = () => {
  const { classID } = useParams()
  const navigate = useNavigate()
  const [syllabus, setSyllabus] = useState<File[]>([])
  const [styleDocs, setStyleDocs] = useState<File[]>([])
  const [uploadedDocs, setUploadedDocs] = useState<string[]>([])
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [confirmName, setConfirmName] = useState('')

  const { data: classes } = useQuery({
    queryKey: ['classCards'],
    queryFn: api.getClassCards
  })

  const className = useMemo(() => {
    return classes?.find((item) => item.classID === classID)?.Name ?? ''
  }, [classes, classID])

  const replaceSyllabus = useMutation({
    mutationFn: async () => {
      const formData = new FormData()
      if (classID) formData.append('classID', classID)
      if (syllabus[0]) formData.append('syllabus', syllabus[0])
      return api.replaceSyllabus(formData)
    },
    onSuccess: () => {
      toast.success('Syllabus updated')
      setSyllabus([])
    },
    onError: (error: Error) => toast.error(error.message || 'Could not update syllabus')
  })

  const uploadDocs = useMutation({
    mutationFn: async () => {
      const formData = new FormData()
      if (classID) formData.append('classID', classID)
      styleDocs.forEach((file) => formData.append('files', file))
      return api.uploadStyleDocs(formData)
    },
    onSuccess: () => {
      toast.success('Style docs updated')
      setUploadedDocs((prev) => [...prev, ...styleDocs.map((file) => file.name)])
      setStyleDocs([])
    },
    onError: (error: Error) => toast.error(error.message || 'Could not upload style docs')
  })

  const deleteDoc = useMutation({
    mutationFn: (docID: string) => api.deleteStyleDoc({ classID: classID ?? '', docID }),
    onSuccess: (_, docID) => {
      toast.success('Style doc removed')
      setUploadedDocs((prev) => prev.filter((item) => item !== docID))
    },
    onError: (error: Error) => toast.error(error.message || 'Could not delete doc')
  })

  const deleteClass = useMutation({
    mutationFn: () => api.deleteClass({ classID: classID ?? '' }),
    onSuccess: () => {
      toast.success('Class deleted')
      navigate('/')
    },
    onError: (error: Error) => toast.error(error.message || 'Could not delete class')
  })

  return (
    <div className="grid gap-8 lg:grid-cols-[260px,1fr]">
      <aside className="space-y-3">
        {['Syllabus', 'Style Docs', 'Danger Zone'].map((item) => (
          <button
            key={item}
            type="button"
            className="w-full rounded-full border border-espresso/20 bg-paper px-4 py-2 text-left text-sm font-medium text-espresso"
          >
            {item}
          </button>
        ))}
      </aside>

      <div className="space-y-6">
        <PaperCard>
          <h2 className="text-lg font-semibold text-espresso">Syllabus</h2>
          <p className="mt-1 text-sm text-espresso/70">Replace the core syllabus PDF for this class.</p>
          <div className="mt-4">
            <UploadDropzone files={syllabus} onFiles={setSyllabus} accept={{ 'application/pdf': ['.pdf'] }} />
            <button
              type="button"
              onClick={() => replaceSyllabus.mutate()}
              disabled={syllabus.length === 0}
              className={cn(
                'mt-3 rounded-full bg-espresso px-4 py-2 text-sm font-medium text-paper',
                'disabled:cursor-not-allowed disabled:opacity-60'
              )}
            >
              {replaceSyllabus.isPending ? 'Updating...' : 'Replace syllabus'}
            </button>
            <p className="mt-2 text-xs text-espresso/60">Updating class index...</p>
          </div>
        </PaperCard>

        <PaperCard>
          <h2 className="text-lg font-semibold text-espresso">Style documents</h2>
          <p className="mt-1 text-sm text-espresso/70">Upload or remove style docs to guide question tone.</p>
          <div className="mt-4">
            <UploadDropzone files={styleDocs} onFiles={setStyleDocs} multiple />
            <button
              type="button"
              onClick={() => uploadDocs.mutate()}
              disabled={styleDocs.length === 0}
              className={cn(
                'mt-3 rounded-full bg-espresso px-4 py-2 text-sm font-medium text-paper',
                'disabled:cursor-not-allowed disabled:opacity-60'
              )}
            >
              {uploadDocs.isPending ? 'Uploading...' : 'Upload style docs'}
            </button>
            <p className="mt-2 text-xs text-espresso/60">Regenerating class-file...</p>
            {uploadedDocs.length === 0 ? (
              <p className="mt-3 text-sm text-espresso/70">No style docs yet.</p>
            ) : (
              <div className="mt-3 space-y-2">
                {uploadedDocs.map((doc) => (
                  <div
                    key={doc}
                    className="flex items-center justify-between rounded-xl border border-espresso/15 bg-sand px-3 py-2 text-xs text-espresso"
                  >
                    <span className="truncate">{doc}</span>
                    <button
                      type="button"
                      onClick={() => deleteDoc.mutate(doc)}
                      className="rounded-full border border-espresso/20 px-2 py-1 text-[10px]"
                    >
                      Delete
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </PaperCard>

        <PaperCard className="border border-red-500/40 bg-red-50/40">
          <h2 className="text-lg font-semibold text-red-800">Danger zone</h2>
          <p className="mt-1 text-sm text-red-700/80">
            Deleting this class removes the syllabus and all session context. This cannot be undone.
          </p>
          <button
            type="button"
            onClick={() => setDeleteOpen(true)}
            className="mt-4 rounded-full border border-red-500/40 px-4 py-2 text-sm font-medium text-red-800"
          >
            Delete class
          </button>
        </PaperCard>
      </div>

      <Dialog.Root open={deleteOpen} onOpenChange={setDeleteOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-espresso/40 backdrop-blur-sm" />
          <Dialog.Content className="fixed left-1/2 top-1/2 w-[90vw] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-espresso/20 bg-paper p-6 shadow-lift">
            <Dialog.Title className="text-lg font-semibold text-espresso">Confirm deletion</Dialog.Title>
            <Dialog.Description className="mt-1 text-sm text-espresso/70">
              Type <span className="font-semibold text-espresso">{className || classID}</span> to confirm.
            </Dialog.Description>
            <input
              value={confirmName}
              onChange={(event) => setConfirmName(event.target.value)}
              className="mt-4 w-full rounded-xl border border-espresso/20 bg-paper px-3 py-2 text-sm"
              placeholder="Type class name"
            />
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setDeleteOpen(false)}
                className="rounded-full border border-espresso/20 px-3 py-2 text-sm"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={confirmName !== (className || classID)}
                onClick={() => deleteClass.mutate()}
                className={cn(
                  'rounded-full bg-red-600 px-3 py-2 text-sm font-medium text-white',
                  'disabled:cursor-not-allowed disabled:opacity-60'
                )}
              >
                {deleteClass.isPending ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  )
}
