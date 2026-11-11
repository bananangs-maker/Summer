import json, os, mimetypes
from pathlib import Path
from wsgiref.simple_server import make_server
from engine import validate, analyze
from storage import Store, Conflict
from weather import get_weather
ROOT=Path(__file__).parent
store = Store()

def application(env,start):
    path=env.get('PATH_INFO','/'); method=env['REQUEST_METHOD']
    def reply(status,obj,typ='application/json; charset=utf-8'):
        body=json.dumps(obj,ensure_ascii=False).encode() if isinstance(obj,(dict,list)) else obj
        start(status,[('Content-Type',typ),('Content-Length',str(len(body))),('Cache-Control','no-store'),('X-Content-Type-Options','nosniff'),('X-Frame-Options','DENY'),('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'")]); return [body]
    try:
        if path=='/health':
            store.read()
            return reply('200 OK',{'ok':True,'storage':'supabase-postgres' if store.url else 'local-sqlite'})
        if path in ('/api/state','/api/export'):
            if method=='GET':
                rev,s = store.read()
                weather = get_weather(store,s['profile']['start']) if s.get('profile') else {}
                return reply('200 OK',{'revision':rev,'state':s,'summary':analyze(s,weather=weather), 'weather':weather})
            if method=='PUT' and path=='/api/state':
                origin=env.get('HTTP_ORIGIN'); host=env.get('HTTP_HOST')
                if origin and origin.split('://',1)[-1]!=host: return reply('403 Forbidden',{'error':'다른 사이트에서 보낸 저장 요청입니다.'})
                length=int(env.get('CONTENT_LENGTH') or 0)
                if not 0<length<=4_000_000: return reply('413 Payload Too Large',{'error':'백업 파일 또는 요청이 너무 큽니다.'})
                obj=json.loads(env['wsgi.input'].read(length)); s=validate(obj['state'])
                try:
                    rev = store.write(obj.get('revision'), s)
                except Conflict:
                    return reply('409 Conflict',{'error':'다른 기기에서 기록이 변경됐습니다. 새로고침한 뒤 다시 입력해주세요.'})
                weather = get_weather(store,s['profile']['start']) if s.get('profile') else {}
                return reply('200 OK',{'revision':rev,'state':s,'summary':analyze(s,weather=weather), 'weather':weather})
            return reply('405 Method Not Allowed',{'error':'지원하지 않는 요청입니다.'})
        if path.startswith('/api/'): return reply('404 Not Found',{'error':'없는 API입니다.'})
        file=ROOT/'static'/('index.html' if path=='/' else path.lstrip('/'))
        if not file.resolve().is_relative_to((ROOT/'static').resolve()) or not file.is_file(): return reply('404 Not Found',b'Not found','text/plain')
        return reply('200 OK',file.read_bytes(),(mimetypes.guess_type(file.name)[0] or 'application/octet-stream')+'; charset=utf-8')
    except (ValueError,KeyError,TypeError) as e: return reply('400 Bad Request',{'error':str(e)})
    except Exception:
        import sys; print('Request failed: database or server unavailable', file=sys.stderr)
        return reply('500 Internal Server Error',{'error':'저장에 실패했습니다. 잠시 후 다시 시도해주세요.'})
if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(); parser.add_argument('--port',type=int,default=int(os.environ.get('PORT','8000'))); parser.add_argument('--host',default='0.0.0.0')
    args,_=parser.parse_known_args()
    with make_server(args.host,args.port,application) as httpd: httpd.serve_forever()
