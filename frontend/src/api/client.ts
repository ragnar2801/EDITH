import createClient from 'openapi-fetch'

import type { components, paths } from './schema'

/**
 * Typed API client generated from the backend's OpenAPI schema (D-035).
 * Regenerate the types with `just api` after changing backend endpoints.
 */
export const api = createClient<paths>({
  baseUrl: globalThis.location?.origin ?? '',
  // Look up fetch per call, so tests can replace it.
  fetch: (request) => globalThis.fetch(request),
})

export type Schemas = components['schemas']
export type ProblemDetails = Schemas['ProblemDetails']
