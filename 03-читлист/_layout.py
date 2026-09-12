"""Парсит читлист, при необходимости вставляет новый бокс, переразбивает на 3 колонки оптимально."""
import re, sys, json
from playwright.sync_api import sync_playwright
HTML='/home/user/finuch/03-читлист/читлист-v2.html'

def parse():
    s=open(HTML,encoding='utf-8').read()
    head=s[:s.index('<body>')+6]
    pages=[]
    for pm in re.finditer(r'<div class="page">(.*?)</div>\s*(?=<div class="page">|</body>)', s, re.S):
        chunk=pm.group(1)
        h1=re.search(r'<h1>.*?</h1>',chunk,re.S).group(0)
        boxes=[];depth=0;start=None
        for m in re.finditer(r'<div class="box[^"]*">|<div\b|</div>',chunk):
            t=m.group(0)
            if t.startswith('<div class="box'):
                if depth==0: start=m.start()
                depth+=1
            elif t=='</div>':
                if depth>0:
                    depth-=1
                    if depth==0: boxes.append(chunk[start:m.end()])
            elif depth>0: depth+=1
        pages.append({'h1':h1,'boxes':boxes})
    return head,pages

def write(head,pages,layouts=None):
    out=head+'\n'
    for pi,p in enumerate(pages):
        lay = layouts[pi] if layouts else [list(range(len(p['boxes'])))]
        cols=''.join('<div class="col">'+''.join(p['boxes'][i] for i in c)+'</div>' for c in lay)
        out+=f'<div class="page">{p["h1"]}<div class="cols">{cols}</div></div>\n'
    out+='</body>\n</html>\n'
    open(HTML,'w',encoding='utf-8').write(out)

def measure():
    with sync_playwright() as pw:
        b=pw.chromium.launch(executable_path='/opt/pw-browsers/chromium-1194/chrome-linux/chrome',args=['--no-sandbox'])
        pg=b.new_page(); pg.goto('file://'+HTML)
        r=pg.evaluate("""() => [...document.querySelectorAll('.page')].map(p => ({
            h1:p.querySelector('h1').getBoundingClientRect().height,
            b:[...p.querySelectorAll('.col')].flatMap(c=>[...c.children].map(x=>x.getBoundingClientRect().height))}))""")
        b.close(); return r

def best_split(hs, gap=3.8):
    n=len(hs); bv=None
    for i in range(1,n-1):
        for j in range(i+1,n):
            cols=[hs[:i],hs[i:j],hs[j:]]
            tot=[sum(c)+gap*(len(c)-1) for c in cols]
            v=max(tot)
            if bv is None or v<bv[0]: bv=(v,(i,j),tot)
    return bv

if __name__=='__main__':
    head,pages=parse()
    if len(sys.argv)>2 and sys.argv[1]=='insert':
        pi=int(sys.argv[2]); idx=int(sys.argv[3])
        pages[pi]['boxes'].insert(idx, open(sys.argv[4],encoding='utf-8').read())
    # стартовая раскладка — поровну по числу боксов, дальше итерируем:
    # высоты боксов зависят от ширины колонки, поэтому мерить надо уже в 3 колонках
    layouts=[]
    for p in pages:
        n=len(p['boxes']); k=n//3
        layouts.append([list(range(0,k)),list(range(k,2*k)),list(range(2*k,n))])
    for it in range(4):
        write(head,pages,layouts)
        r=measure(); new=[]; report=[]
        for pi,pm in enumerate(r):
            cap=1035-pm['h1']; v,(i,j),tot=best_split(pm['b']); n=len(pm['b'])
            new.append([list(range(0,i)),list(range(i,j)),list(range(j,n))])
            report.append(f"стр{pi+1}: {[round(t) for t in tot]} / {cap:.0f} → {v/cap*100:.0f}%")
        stable = new==layouts
        layouts=new
        print(f"итерация {it+1}: "+" | ".join(report))
        if stable: break
    write(head,pages,layouts)
