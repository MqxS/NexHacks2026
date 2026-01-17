import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as Dialog from '@radix-ui/react-dialog'
import { z } from 'zod'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { toast } from 'sonner'
import { api, type ClassCard } from '../api'
import { CenteredCarousel } from '../components/CenteredCarousel'
import { ClassCard as ClassCardUI } from '../components/ClassCard'
import { LoadingSkeleton } from '../components/LoadingSkeleton'
import { UploadDropzone } from '../components/UploadDropzone'
import { PaperCard } from '../components/PaperCard'
import { cn } from '../lib/utils'
import { useNavigate } from 'react-router-dom'

const createSchema = z.object({
  name: z.string().min(1, 'Class name is required'),
  professor: z.string().min(1, 'Professor is required'),
  recommendations: z.string().optional()
})

type CreateValues = z.infer<typeof createSchema>

export const Home = () => {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [createOpen, setCreateOpen] = useState(false)
  const [editing, setEditing] = useState<ClassCard | null>(null)
  const [syllabus, setSyllabus] = useState<File[]>([])
  const [attachments, setAttachments] = useState<File[]>([])

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['classCards'],
    queryFn: api.getClassCards
  })

  const createForm = useForm<CreateValues>({
    resolver: zodResolver(createSchema),
    defaultValues: {
      name: '',
      professor: '',
      recommendations: ''
    }
  })

  const createMutation = useMutation({
    mutationFn: async (payload: CreateValues) => {
      const formData = new FormData()
      formData.append('Name', payload.name)
      formData.append('Professor', payload.professor)
      formData.append('recommended', payload.recommendations ?? '')
      if (syllabus[0]) formData.append('syllabus', syllabus[0])
      attachments.forEach((file) => formData.append('files', file))
      return api.createClass(formData)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['classCards'] })
      toast.success('Class created')
      setCreateOpen(false)
      createForm.reset()
      setSyllabus([])
      setAttachments([])
    },
    onError: (error: Error) => toast.error(error.message || 'Could not create class')
  })

  const editNameMutation = useMutation({
    mutationFn: api.editClassName,
    onMutate: async (payload) => {
      await queryClient.cancelQueries({ queryKey: ['classCards'] })
      const previous = queryClient.getQueryData<ClassCard[]>(['classCards'])
      queryClient.setQueryData<ClassCard[]>(['classCards'], (old) =>
        (old ?? []).map((card) =>
          card.classID === payload.classID ? { ...card, Name: payload.newName } : card
        )
      )
      return { previous }
    },
    onError: (error: Error, _, context) => {
      if (context?.previous) queryClient.setQueryData(['classCards'], context.previous)
      toast.error(error.message || 'Could not update class')
    },
    onSuccess: () => toast.success('Class updated'),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ['classCards'] })
  })

  const editProfMutation = useMutation({
    mutationFn: api.editClassProf,
    onMutate: async (payload) => {
      await queryClient.cancelQueries({ queryKey: ['classCards'] })
      const previous = queryClient.getQueryData<ClassCard[]>(['classCards'])
      queryClient.setQueryData<ClassCard[]>(['classCards'], (old) =>
        (old ?? []).map((card) =>
          card.classID === payload.classID ? { ...card, Professor: payload.newProf } : card
        )
      )
      return { previous }
    },
    onError: (error: Error, _, context) => {
      if (context?.previous) queryClient.setQueryData(['classCards'], context.previous)
      toast.error(error.message || 'Could not update professor')
    },
    onSuccess: () => toast.success('Professor updated'),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ['classCards'] })
  })

  const cards = useMemo(() => data ?? [], [data])
  const carouselItems = [...cards, { classID: 'create', Name: 'Create class', Professor: 'Start a fresh study space' }]
  const initialIndex = cards.length >= 3 ? 1 : cards.length === 0 ? carouselItems.length - 1 : 0

  return (
    <div className="space-y-10 min-h-[70vh] flex flex-col justify-center">
      <div>
        <h1 className="text-3xl font-semibold text-espresso">Your classes</h1>
        <p className="mt-2 text-sm text-espresso/70">
          Pick a class to start a new session or keep your materials organized.
        </p>
      </div>

      {isLoading ? (
        <div className="flex gap-6 overflow-hidden">
          {[0, 1, 2].map((index) => (
            <LoadingSkeleton key={index} className="h-[240px] w-[280px]" />
          ))}
        </div>
      ) : isError ? (
        <PaperCard className="flex items-center justify-between">
          <p className="text-sm text-espresso/80">We could not load your classes.</p>
          <button
            type="button"
            onClick={() => refetch()}
            className="rounded-full border border-espresso/20 px-4 py-2 text-sm font-medium text-espresso"
          >
            Retry
          </button>
        </PaperCard>
      ) : (
        <CenteredCarousel
          items={carouselItems}
          initialIndex={initialIndex}
          renderItem={(item, _index, selected) => {
            if (item.classID === 'create') {
              return (
                <ClassCardUI
                  name="Create class"
                  professor="Upload a syllabus to begin"
                  selected={selected}
                  onOpen={() => setCreateOpen(true)}
                  variant="create"
                />
              )
            }
            return (
              <ClassCardUI
                name={item.Name}
                professor={item.Professor}
                selected={selected}
                onOpen={() => navigate(`/class/${item.classID}/session`)}
                onEdit={() => setEditing(item)}
              />
            )
          }}
        />
      )}


      <Dialog.Root open={createOpen} onOpenChange={setCreateOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-50 bg-espresso/40 backdrop-blur-sm" />
          <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[90vw] max-w-2xl -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-espresso/20 bg-paper p-6 shadow-lift max-h-[85vh] overflow-y-auto">
            <Dialog.Title className="text-xl font-semibold text-espresso">Create new class</Dialog.Title>
            <Dialog.Description className="mt-1 text-sm text-espresso/70">
              Upload a syllabus and any helpful materials to prepare the course space.
            </Dialog.Description>
            <form
              onSubmit={createForm.handleSubmit((values) => createMutation.mutate(values))}
              className="mt-6 space-y-4"
            >
              <div>
                <label className="text-sm font-medium text-espresso">Class name</label>
                <input
                  {...createForm.register('name')}
                  className="mt-2 w-full rounded-xl border border-espresso/20 bg-paper px-3 py-2 text-sm"
                  placeholder="Linear Algebra"
                />
                {createForm.formState.errors.name ? (
                  <p className="mt-1 text-xs text-red-600">{createForm.formState.errors.name.message}</p>
                ) : null}
              </div>
              <div>
                <label className="text-sm font-medium text-espresso">Professor</label>
                <input
                  {...createForm.register('professor')}
                  className="mt-2 w-full rounded-xl border border-espresso/20 bg-paper px-3 py-2 text-sm"
                  placeholder="Dr. Gomez"
                />
                {createForm.formState.errors.professor ? (
                  <p className="mt-1 text-xs text-red-600">{createForm.formState.errors.professor.message}</p>
                ) : null}
              </div>
              <div>
                <label className="text-sm font-medium text-espresso">Syllabus PDF</label>
                <UploadDropzone
                  files={syllabus}
                  onFiles={(files) => setSyllabus(files.filter((file) => file.type === 'application/pdf'))}
                  accept={{ 'application/pdf': ['.pdf'] }}
                  helper="PDF only"
                />
                {syllabus.length === 0 ? (
                  <p className="mt-1 text-xs text-espresso/60">Please upload your syllabus PDF.</p>
                ) : null}
              </div>
              <div>
                <label className="text-sm font-medium text-espresso">Additional files (optional)</label>
                <UploadDropzone
                  files={attachments}
                  onFiles={setAttachments}
                  multiple
                  helper="Dont worry - you can upload more later."
                />
              </div>
              <div>
                <label className="text-sm font-medium text-espresso">Recommended homework or guides (optional)</label>
                <textarea
                  {...createForm.register('recommendations')}
                  className="mt-2 w-full rounded-xl border border-espresso/20 bg-paper px-3 py-2 text-sm"
                  rows={3}
                  placeholder="Chapter 1 review, problem set 2, study guide"
                />
              </div>
              <button
                type="submit"
                disabled={createMutation.isPending || syllabus.length === 0}
                className={cn(
                  'w-full rounded-full bg-espresso px-4 py-2 text-sm font-medium text-paper transition',
                  'disabled:cursor-not-allowed disabled:opacity-60'
                )}
              >
                {createMutation.isPending ? 'Creating...' : 'Create class'}
              </button>
            </form>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>

      <Dialog.Root open={Boolean(editing)} onOpenChange={(open) => !open && setEditing(null)}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 z-50 bg-espresso/40 backdrop-blur-sm" />
          <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[90vw] max-w-lg -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-espresso/20 bg-paper p-6 shadow-lift max-h-[85vh] overflow-y-auto">
            <Dialog.Title className="text-xl font-semibold text-espresso">Edit class</Dialog.Title>
            {editing ? (
              <div className="mt-4 space-y-4">
                <InlineEditField
                  label="Class name"
                  value={editing.Name}
                  onSave={(value) => editNameMutation.mutate({ classID: editing.classID, newName: value })}
                />
                <InlineEditField
                  label="Professor"
                  value={editing.Professor}
                  onSave={(value) => editProfMutation.mutate({ classID: editing.classID, newProf: value })}
                />
              </div>
            ) : null}
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  )
}

const InlineEditField = ({
  label,
  value,
  onSave
}: {
  label: string
  value: string
  onSave: (value: string) => void
}) => {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(value)

  useEffect(() => {
    setDraft(value)
  }, [value])

  return (
    <div className="rounded-2xl border border-espresso/15 bg-sand/50 p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-espresso/60">{label}</p>
      {editing ? (
        <div className="mt-2 flex items-center gap-2">
          <input
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            className="w-full rounded-xl border border-espresso/20 bg-paper px-3 py-2 text-sm"
          />
          <button
            type="button"
            onClick={() => {
              onSave(draft)
              setEditing(false)
            }}
            className="rounded-full bg-espresso px-3 py-1 text-xs font-medium text-paper"
          >
            Save
          </button>
          <button
            type="button"
            onClick={() => {
              setDraft(value)
              setEditing(false)
            }}
            className="rounded-full border border-espresso/20 px-3 py-1 text-xs"
          >
            Cancel
          </button>
        </div>
      ) : (
        <div className="mt-2 flex items-center justify-between">
          <p className="text-sm text-espresso">{value}</p>
          <button
            type="button"
            onClick={() => setEditing(true)}
            className="rounded-full border border-espresso/20 px-3 py-1 text-xs"
          >
            Edit
          </button>
        </div>
      )}
    </div>
  )
}
