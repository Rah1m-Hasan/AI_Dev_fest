// Keep local development requests on the frontend origin. Vite proxies `/api`
// to the backend, which also works when the frontend is opened through a
// remote/embedded preview where the browser cannot reach `localhost:8000`.
const BASE=import.meta.env.VITE_API_URL || '/api/v1';
export const token=()=>localStorage.getItem('upay_token');
export class ApiError extends Error{constructor(message:string,public readonly status:number){super(message)}}
export async function api<T=Record<string,unknown>>(path:string, init:RequestInit={}):Promise<T>{
  let response: Response;
  try {
    response=await fetch(BASE+path,{...init,headers:{'Content-Type':'application/json',...(token()?{Authorization:`Bearer ${token()}`}:{}) ,...(init.headers||{})}});
  } catch {
    throw new ApiError("We couldn't connect to AI Assist. Check that the API is running, then try again.",0);
  }
  if(!response.ok){
    const payload=await response.json().catch(()=>null) as {detail?:unknown}|null;
    const detail=typeof payload?.detail === 'string' ? payload.detail : `Request failed (${response.status})`;
    throw new ApiError(detail,response.status);
  }
  return response.json() as Promise<T>;
}
