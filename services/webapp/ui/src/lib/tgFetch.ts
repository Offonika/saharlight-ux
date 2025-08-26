// file: services/webapp/ui/src/lib/tgFetch.ts
// Добавил фолбэк: если Telegram.WebApp.initData ещё не готов,
// берём raw-строку initData из location.hash (?tgWebAppData=...).
export const TG_INIT_DATA_HEADER = 'X-Telegram-Init-Data'
export const REQUEST_TIMEOUT_MESSAGE = 'Превышено время ожидания запроса'
const REQUEST_TIMEOUT = 10_000 // 10 seconds

interface TelegramWebApp { initData?: string }
interface TelegramWindow extends Window { Telegram?: { WebApp?: TelegramWebApp } }

// ──► новый helper: достаём initData либо из Telegram.WebApp, либо из #tgWebAppData=...
function getInitData(): string {
  const tg = (window as TelegramWindow).Telegram?.WebApp
  if (tg?.initData) return tg.initData

  // Фолбэк для случаев, когда скрипт сработал раньше telegram-init:
  // URL вида: #tgWebAppData=<URL-ENCODED-QUERY>&tgWebAppVersion=...
  const hash = window.location.hash.startsWith('#')
    ? window.location.hash.slice(1)
    : window.location.hash
  if (!hash) return ''
  const params = new URLSearchParams(hash)
  const raw = params.get('tgWebAppData') // это и есть initData (URL-encoded query string)
  return raw ?? ''
}

export async function tgFetch(input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers || {})
  const initData = getInitData()
  if (initData) headers.set(TG_INIT_DATA_HEADER, initData)

  const controller = new AbortController()
  let didTimeout = false
  const timeoutId = setTimeout(() => { didTimeout = true; controller.abort() }, REQUEST_TIMEOUT)

  let signal: AbortSignal = controller.signal
  if (init.signal) {
    if (typeof AbortSignal.any === 'function') {
      signal = (AbortSignal as any).any([controller.signal, init.signal])
    } else {
      if (init.signal.aborted) controller.abort()
      else init.signal.addEventListener('abort', () => controller.abort(), { once: true })
      signal = controller.signal
    }
  }

  try {
    const response = await fetch(input, {
      ...init,
      headers,
      credentials: init.credentials ?? 'include',
      signal,
    })
    if (!response.ok) {
      let errorMessage = response.statusText || `HTTP error ${response.status}`
      try {
        const data: unknown = await response.json()
        if (typeof data === 'object' && data !== null) {
          const err = data as { detail?: string; message?: string }
          errorMessage = err.detail ?? err.message ?? errorMessage
        }
      } catch { /* ignore JSON parse errors */ }
      throw new Error(errorMessage)
    }
    return response
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      if (didTimeout) throw new Error(REQUEST_TIMEOUT_MESSAGE)
      throw error
    }
    if (error instanceof TypeError || error instanceof DOMException) {
      throw new Error('Проблема с сетью. Проверьте подключение')
    }
    throw error
  } finally {
    clearTimeout(timeoutId)
  }
}
