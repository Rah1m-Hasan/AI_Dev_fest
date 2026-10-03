// Use one origin in every environment. During local development Vite proxies
// `/api` to FastAPI; Vercel Services routes it to the backend service.
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
    const errMsg = `[API] Fetch failed: ${msg} | URL: ${url} | Token exists: ${!!token()}`;
    console.error(errMsg);
    if (err instanceof Error && err.stack) {
      console.error('[API] Stack:', err.stack);
    }
    throw new ApiError(`Cannot connect to AI Assist: ${msg}`,0);
  }
  if(!response.ok){
    const payload=await response.json().catch(()=>null) as {detail?:unknown}|null;
    const detail=typeof payload?.detail === 'string' ? payload.detail : `Request failed (${response.status})`;
    throw new ApiError(detail,response.status);
  }
  return response.json() as Promise<T>;
}
