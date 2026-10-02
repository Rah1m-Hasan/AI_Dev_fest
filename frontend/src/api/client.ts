const BASE=import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
export const token=()=>localStorage.getItem('upay_token');
export async function api<T=any>(path:string, init:RequestInit={}):Promise<T>{const r=await fetch(BASE+path,{...init,headers:{'Content-Type':'application/json',...(token()?{Authorization:`Bearer ${token()}`}:{}) ,...(init.headers||{})}});if(!r.ok) throw new Error((await r.json().catch(()=>({}))).detail||`Request failed (${r.status})`);return r.json()}
