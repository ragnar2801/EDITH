import { Link } from 'react-router'

export function NotFoundPage() {
  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-2xl font-semibold tracking-tight">Page not found</h1>
      <p className="text-muted-foreground mt-1">
        <Link to="/" className="underline underline-offset-4">
          Back to the dashboard
        </Link>
      </p>
    </div>
  )
}
