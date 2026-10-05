"""Small structured-output provider boundary using only the standard library."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any,Protocol
import json,os,urllib.error,urllib.request,uuid
from pathlib import Path

class ProviderError(RuntimeError):
 def __init__(self,message,diagnostics=None):
  super().__init__(message);self.diagnostics=diagnostics or {}
class ProviderTimeout(ProviderError):pass
class ProviderRateLimit(ProviderError):pass
class ProviderResponseError(ProviderError):pass
class ProviderUnavailable(ProviderError):pass

@dataclass(frozen=True)
class ProviderResponse:
 content:str
 provider:str
 model:str
 request_id:str|None=None
 input_tokens:int|None=None
 output_tokens:int|None=None
 http_status:int|None=200
 selected_model:str|None=None
 selected_provider:str|None=None
 finish_reason:str|None=None
 response_received:bool=True

class LLMProvider(Protocol):
 provider_name:str
 model:str
 def generate_structured_plan(self,*,system_prompt:str,input_json:str,schema:dict[str,Any])->ProviderResponse:...

class OpenAICompatibleProvider:
 """OpenAI Chat Completions structured JSON Schema client; secrets are never logged."""
 def __init__(self,api_key:str,model:str='gpt-4o-mini',base_url:str='https://api.openai.com/v1',temperature:float=0.0,timeout:float=20.0,max_output_tokens:int=700,provider_name:str='openai-compatible'):
  if not api_key:raise ValueError('LLM API key is required')
  if not model or len(model)>120:raise ValueError('invalid LLM model')
  if not 0<=temperature<=2 or not 1<=timeout<=120 or not 64<=max_output_tokens<=8192:raise ValueError('invalid LLM provider settings')
  self.api_key=api_key;self.model=model;self.base_url=base_url.rstrip('/');self.temperature=temperature;self.timeout=timeout;self.max_output_tokens=max_output_tokens;self.provider_name=provider_name
 def generate_structured_plan(self,*,system_prompt,input_json,schema):
  payload={'model':self.model,'temperature':self.temperature,'max_completion_tokens':self.max_output_tokens,'messages':[{'role':'system','content':system_prompt},{'role':'user','content':input_json}],'response_format':{'type':'json_schema','json_schema':{'name':'support_action_plan','strict':True,'schema':schema}}}
  request=urllib.request.Request(self.base_url+'/chat/completions',data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+self.api_key,'Content-Type':'application/json','X-Client-Request-Id':uuid.uuid4().hex},method='POST')
  try:
   with urllib.request.urlopen(request,timeout=self.timeout) as response:
    request_id=response.headers.get('x-request-id');body=json.loads(response.read(100_000));http_status=getattr(response,'status',200)
  except urllib.error.HTTPError as e:
   safe_headers={k:v[:200] for k,v in e.headers.items() if k.lower() in {'x-request-id','x-openrouter-route','content-type','retry-after'}}
   try:
    error_body=json.loads(e.read(20_000));err=error_body.get('error') or {};message=str(err.get('message',''))[:500]
    message=message.replace(self.api_key,'[REDACTED]')
    diagnostics={'http_status':e.code,'request_id':safe_headers.get('x-request-id'),'provider_error_code':err.get('code'),'provider_error_message':message or None,'response_received':False,'safe_headers':safe_headers}
   except Exception:diagnostics={'http_status':e.code,'response_received':False,'safe_headers':safe_headers}
   if e.code==429:raise ProviderRateLimit('provider rate limited request',diagnostics) from None
   if e.code in {401,403}:raise ProviderError('provider authentication rejected',diagnostics) from None
   raise ProviderError('provider rejected request',diagnostics) from None
  except (TimeoutError,urllib.error.URLError) as e:
   if isinstance(e,TimeoutError) or isinstance(getattr(e,'reason',None),TimeoutError):raise ProviderTimeout('provider request timed out') from None
   raise ProviderUnavailable('provider is unavailable') from None
  except OSError:raise ProviderUnavailable('provider is unavailable') from None
  except (json.JSONDecodeError,ValueError) as e:raise ProviderResponseError('provider returned invalid response JSON') from None
  try:
   choice=body['choices'][0];message=choice['message'];content=message.get('content')
   usage=body.get('usage') or {}
   response_meta={'http_status':http_status,'request_id':request_id,'selected_model':body.get('model'),'selected_provider':body.get('provider'),'finish_reason':choice.get('finish_reason'),'response_received':True,'input_tokens':usage.get('prompt_tokens'),'output_tokens':usage.get('completion_tokens'),'total_tokens':usage.get('total_tokens')}
   if message.get('refusal'):raise ProviderResponseError('provider refused planner request',response_meta)
   if not isinstance(content,str) or not content:raise ProviderResponseError('provider response omitted structured content',response_meta)
   return ProviderResponse(content,self.provider_name,self.model,request_id,usage.get('prompt_tokens'),usage.get('completion_tokens'),http_status,body.get('model'),body.get('provider'),choice.get('finish_reason'),True)
  except ProviderError:raise
  except (KeyError,IndexError,TypeError):raise ProviderResponseError('provider response omitted structured content') from None

def load_local_env():
 # Load the project-local .env without a third-party dependency. Existing
 # process environment wins, and values are never printed or logged.
 env_path=Path('.env')
 if env_path.is_file():
  try:
   for line in env_path.read_text(encoding='utf-8').splitlines():
    stripped=line.strip()
    if not stripped or stripped.startswith('#') or '=' not in stripped:continue
    name,value=stripped.split('=',1);name=name.strip();value=value.strip()
    if value[:1] in {'"',"'"} and len(value)>=2 and value[-1:]==value[:1]:value=value[1:-1]
    if name and name.replace('_','').isalnum() and name not in os.environ:os.environ[name]=value
  except OSError:
   pass

def provider_from_env():
 load_local_env()
 provider=os.getenv('LLM_PROVIDER','openai').strip().lower()
 if provider not in {'openai','openrouter'}:raise ValueError('LLM_PROVIDER must be openai or openrouter')
 key_name='OPENROUTER_API_KEY' if provider=='openrouter' else 'OPENAI_API_KEY'
 key=os.getenv(key_name,'').strip()
 if not key:return None
 base_url=os.getenv('LLM_BASE_URL','https://openrouter.ai/api/v1' if provider=='openrouter' else 'https://api.openai.com/v1')
 model=os.getenv('LLM_MODEL','openrouter/free' if provider=='openrouter' else 'gpt-4o-mini')
 return OpenAICompatibleProvider(key,model=model,base_url=base_url,temperature=float(os.getenv('LLM_TEMPERATURE','0')),timeout=float(os.getenv('LLM_TIMEOUT_SECONDS','20')),max_output_tokens=int(os.getenv('LLM_MAX_OUTPUT_TOKENS','700')),provider_name=provider)
