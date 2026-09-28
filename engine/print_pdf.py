"""SVG -> PDF at true size, by printing it with headless Firefox over Marionette (no other PDF tool on
debnuc). Usage: print_pdf.py in.svg out.pdf [width_mm height_mm]"""
import sys,os,json,socket,subprocess,tempfile,time,base64,shutil,random
src,dst=os.path.abspath(sys.argv[1]),sys.argv[2]
wmm,hmm=(float(sys.argv[3]),float(sys.argv[4])) if len(sys.argv)>4 else (297,420)
prof=tempfile.mkdtemp(); port=random.randint(28000,28999)
open(f'{prof}/user.js','w').write(f'user_pref("marionette.port",{port});\n')
html=f'{prof}/sheet.html'
open(html,'w').write(f'<!doctype html><meta charset="utf-8"><style>@page{{size:{wmm}mm {hmm}mm;margin:0}}html,body{{margin:0}}'
                     f'svg{{display:block;width:{wmm}mm;height:{hmm}mm}}</style>'+open(src).read())
ff=subprocess.Popen(['firefox','--headless','--marionette','--no-remote','--profile',prof],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
try:
    for _ in range(100):
        try: s=socket.create_connection(('127.0.0.1',port)); break
        except OSError: time.sleep(0.2)
    f=s.makefile('rb')
    def recv():
        n=b''
        while (c:=f.read(1))!=b':': n+=c
        return json.loads(f.read(int(n)))
    recv(); mid=0
    def cmd(name,params):
        global mid; mid+=1; b=json.dumps([0,mid,name,params]).encode(); s.sendall(str(len(b)).encode()+b':'+b)
        r=recv()
        if r[2]: raise SystemExit(f'{name}: {r[2]}')
        return r[3]
    cmd('WebDriver:NewSession',{'capabilities':{}})
    cmd('WebDriver:Navigate',{'url':'file://'+html})
    r=cmd('WebDriver:Print',{'page':{'width':wmm/10,'height':hmm/10},'margin':{'top':0,'bottom':0,'left':0,'right':0},
                              'background':True,'shrinkToFit':False,'scale':1,'orientation':'portrait'})
    open(dst,'wb').write(base64.b64decode(r['value']))
finally:
    ff.terminate(); ff.wait(); shutil.rmtree(prof,ignore_errors=True)
