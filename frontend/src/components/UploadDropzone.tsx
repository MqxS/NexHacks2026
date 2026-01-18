import {useDropzone} from 'react-dropzone'
import {UploadCloud, X} from 'lucide-react'
import {cn} from '../lib/utils'

export const UploadDropzone = ({
  onFiles,
  files,
  accept,
  multiple = false,
  helper
}: {
  onFiles: (files: File[]) => void
  files: File[]
  accept?: Record<string, string[]>
  multiple?: boolean
  helper?: string
}) => {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop: (accepted) => onFiles(accepted),
    accept,
    multiple
  })

  return (
    <div>
      <div
        {...getRootProps()}
        className={cn(
          'flex cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed border-espresso/30 bg-paper/70 px-6 py-6 text-center transition',
          isDragActive && 'border-espresso/60 bg-sand'
        )}
      >
        <input {...getInputProps()} />
        <UploadCloud className="mb-2 h-6 w-6 text-espresso/70" />
        <p className="text-sm font-medium text-espresso">Drop files or click to upload</p>
        {helper ? <p className="mt-1 text-xs text-espresso/60">{helper}</p> : null}
      </div>
      {files.length > 0 ? (
        <div className="mt-3 space-y-2">
          {files.map((file) => (
            <div
              key={`${file.name}-${file.size}`}
              className="flex items-center justify-between rounded-xl border border-espresso/15 bg-sand px-3 py-2 text-xs text-espresso"
            >
              <span className="truncate">{file.name}</span>
              <button type="button" onClick={() => onFiles(files.filter((f) => f !== file))}>
                <X className="h-3 w-3" />
              </button>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  )
}
