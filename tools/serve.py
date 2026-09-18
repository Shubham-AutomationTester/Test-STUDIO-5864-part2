#!/usr/bin/env python3
"""Serve static QA fixtures with real HTTP headers and identifiable JSONL request logs.

No third-party dependencies. Not a production web server or a replacement crawler.
"""
import argparse
import json
import mimetypes
import os
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT=Path(__file__).resolve().parents[1]
PUBLIC=(ROOT/'docs').resolve()
LOCK=threading.Lock()

class Handler(BaseHTTPRequestHandler):
    server_version='Studio5864FixtureServer/1.0'
    def log_message(self, format, *args):
        pass
    def do_GET(self):
        self.serve(head=False)
    def do_HEAD(self):
        self.serve(head=True)
    def serve(self, head):
        parsed=urlsplit(self.path)
        raw_path=unquote(parsed.path)
        config=json.loads((ROOT/'config.json').read_text())
        prefix=config.get('base_path','').rstrip('/')
        local_path=raw_path
        status=200;redirect=None;content=b'';content_type='text/html; charset=utf-8';pairs=[]
        if prefix and raw_path=='/':
            status=302;redirect=prefix+'/'
        elif prefix and raw_path!='/robots.txt':
            if raw_path==prefix:
                status=301;redirect=prefix+'/'
            elif raw_path.startswith(prefix+'/'):
                local_path=raw_path[len(prefix):]
            else:
                status=404
        if status==200:
            candidate=(PUBLIC/local_path.lstrip('/')).resolve()
            try:
                candidate.relative_to(PUBLIC)
            except ValueError:
                status=403
            if status==200:
                if candidate.is_dir():
                    if not local_path.endswith('/'):
                        status=301;redirect=raw_path+'/' + (('?'+parsed.query) if parsed.query else '')
                    else:
                        candidate=candidate/'index.html'
                if status==200:
                    if not candidate.is_file():
                        status=404
                    else:
                        content=candidate.read_bytes()
                        content_type=mimetypes.guess_type(str(candidate))[0] or 'application/octet-stream'
                        if content_type.startswith('text/') or content_type in ('application/javascript','application/json'):
                            content_type+='; charset=utf-8'
                        pairs=json.loads((ROOT/'qa/http-headers.json').read_text()).get(local_path,[])
        if status in (403,404):
            content=(PUBLIC/'404.html').read_bytes()
        self.send_response(status)
        self.send_header('Content-Type',content_type)
        self.send_header('Content-Length',str(len(content)))
        self.send_header('Cache-Control','no-store, max-age=0')
        if redirect:self.send_header('Location',redirect)
        for name,value in pairs:
            # send_header is intentionally called once per entry, preserving H07's two lines.
            self.send_header(name,value)
        self.end_headers()
        try:
            if not head and content:self.wfile.write(content)
        except (BrokenPipeError,ConnectionResetError):
            pass
        event={'event':'qa.fixture.request','timestamp':datetime.now(timezone.utc).isoformat(),
               'method':self.command,'path':self.path,'status':status,
               'user_agent':self.headers.get('User-Agent',''),'referer':self.headers.get('Referer',''),
               'note':'A fixture-server access event, NOT a SearchStax pipeline event.'}
        with LOCK:
            with self.server.log_path.open('a',encoding='utf-8') as f:f.write(json.dumps(event)+'\n')
        if not self.server.quiet:
            print(f'{self.command} {self.path} {status} UA={event["user_agent"]}',flush=True)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--port',type=int,default=int(os.environ.get('PORT','8000')))
    p.add_argument('--bind',default='127.0.0.1')
    p.add_argument('--log',default=str(ROOT/'qa/requests.jsonl'))
    p.add_argument('--quiet',action='store_true')
    args=p.parse_args()
    if not 1<=args.port<=65535:p.error('Port must be between 1 and 65535.')
    if not (PUBLIC/'index.html').is_file():p.error('Static site not found; run python3 tools/build.py.')
    server=ThreadingHTTPServer((args.bind,args.port),Handler)
    server.log_path=Path(args.log).resolve();server.log_path.parent.mkdir(parents=True,exist_ok=True)
    server.quiet=args.quiet
    prefix=json.loads((ROOT/'config.json').read_text()).get('base_path','')
    print(f'Fixture server: http://{args.bind}:{args.port}{prefix}/',flush=True)
    print(f'Access log: {server.log_path}. This server does not run SearchStax.',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:print('\nStopping fixture server.')
    finally:server.server_close()

if __name__=='__main__':main()
