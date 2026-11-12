import asyncio, sys
from playwright.async_api import async_playwright
OUT="/tmp/claude-0/-home-claude/6aad4c76-dd60-593b-862f-e20aa51cf482/scratchpad/"
S=[("g1",1400,"light","/",0),("g2",1400,"light","/",900),("g3",1400,"dark","/runout/","#decoder"),("g4",390,"light","/",0),("g5",1400,"light","/cutting/","#sidetime"),("g6",390,"dark","/history/",0)]
async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch()
        for n,w,sc,path,y in S:
            pg=await b.new_page(viewport={"width":w,"height":950},color_scheme=sc); errs=[]
            pg.on("pageerror",lambda e: errs.append(str(e)))
            await pg.goto("http://127.0.0.1:8795"+path); await pg.wait_for_timeout(600)
            if isinstance(y,str): await pg.evaluate(f"(()=>{{const e=document.querySelector('{y}'); if(e) window.scrollTo(0,e.getBoundingClientRect().top+scrollY-20)}})()")
            else: await pg.evaluate(f"window.scrollTo(0,{y})")
            await pg.wait_for_timeout(250); await pg.screenshot(path=OUT+n+".png"); print(n,errs,await pg.evaluate("document.documentElement.scrollWidth"))
        await b.close()
asyncio.run(main())
