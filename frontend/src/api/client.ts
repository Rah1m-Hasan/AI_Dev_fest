// Use one origin in every environment. During local development Vite proxies
// `/api` to FastAPI; Vercel Services routes it to the backend service.
import type {
  LearningResponse, LessonDetail, LessonCard, LessonProgressSummary,
  OfferCard, OfferDetail, OfferPreferences, OffersResponse, LessonCompleteResult,
} from '../types';

const BASE='/api/v1';
export const token=()=>localStorage.getItem('upay_token');
export class ApiError extends Error{constructor(message:string,public readonly status:number){super(message)}}
export async function api<T=Record<string,unknown>>(path:string, init:RequestInit={}):Promise<T>{
  let response: Response;
  const url = BASE+path;
  try {
    response=await fetch(url,{...init,headers:{'Content-Type':'application/json',...(token()?{Authorization:`Bearer ${token()}`}:{}) ,...(init.headers||{})}});
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    throw new ApiError(`Cannot connect to AI Assist: ${msg}`,0);
  }
  if(!response.ok){
    const payload=await response.json().catch(()=>null) as {detail?:unknown}|null;
    const detail=typeof payload?.detail === 'string' ? payload.detail : `Request failed (${response.status})`;
    throw new ApiError(detail,response.status);
  }
  return response.json() as Promise<T>;
}

// --- Learning API ---
export const learningAPI = {
  recommendations: () => api<LearningResponse>('/learning/recommendations'),
  lessons: (category?: string) => api<{ lessons: LessonCard[] }>(`/learning/lessons${category ? `?category=${encodeURIComponent(category)}` : ''}`),
  lessonDetail: (id: number) => api<LessonDetail>(`/learning/lessons/${id}`),
  startLesson: (id: number) => api(`/learning/${id}/start`, { method: 'POST' }),
  completeLesson: (id: number, quizAnswer?: string) =>
    api<LessonCompleteResult>(`/learning/${id}/complete`, {
      method: 'POST',
      body: JSON.stringify(quizAnswer ? { quiz_answer: quizAnswer } : {}),
    }),
  progress: () => api<{ categories: LessonProgressSummary[] }>('/learning/progress'),
};

// --- Offers API ---
export const offersAPI = {
  list: (category?: string, state = 'active') => {
    const params = new URLSearchParams({ state });
    if (category) params.set('category', category);
    return api<OffersResponse>(`/offers?${params.toString()}`);
  },
  detail: (id: number) => api<OfferDetail>(`/offers/${id}`),
  save: (id: number) => api(`/offers/${id}/save`, { method: 'POST' }),
  unsave: (id: number) => api(`/offers/${id}/save`, { method: 'DELETE' }),
  saved: () => api<{ offers: OfferCard[] }>('/offers/saved'),
  preferences: () => api<OfferPreferences>('/offers/preferences'),
  updatePreferences: (enabled: boolean) =>
    api<OfferPreferences>('/offers/preferences', { method: 'PUT', body: JSON.stringify({ enabled }) }),
};
