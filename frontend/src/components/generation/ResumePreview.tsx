import ReactMarkdown from 'react-markdown'
import { Skeleton } from '../ui/Skeleton'

interface ResumePreviewProps {
  content: string | null
  isLoading: boolean
}

export function ResumePreview({ content, isLoading }: ResumePreviewProps) {
  if (isLoading) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton lines={3} />
        <Skeleton lines={5} />
        <Skeleton lines={4} />
      </div>
    )
  }

  if (!content) {
    return (
      <div className="flex items-center justify-center h-full text-text-tertiary text-sm">
        Resume will appear here after generation
      </div>
    )
  }

  return (
    <div className="p-6 overflow-auto h-full markdown-content">
      <ReactMarkdown>{content}</ReactMarkdown>
    </div>
  )
}
