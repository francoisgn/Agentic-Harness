import json,copy,pathlib,sys
base=json.load(open("docs/diagrams/ai-layers.json"))
by={e.get("id"):e for e in base}
T=by["l1"]; A=by["l1a"]; TITLE=by["title"]; SUB=by["subtitle"]; G=by["obo"]
COL={1:("#fff3bf","#f08c00"),2:("#a5d8ff","#1971c2"),3:("#b2f2bb","#2f9e44"),4:("#c3fae8","#0c8599")}
def rect(i,x,y,w,h,text,layer=None,fs=17):
    e=copy.deepcopy(T if layer else G); e.update(id=i,x=x,y=y,width=w,height=h)
    if layer: e["backgroundColor"],e["strokeColor"]=COL[layer]
    e["label"]={"text":text,"fontSize":fs}; return e
def arrow(i,x,y,layer):
    e=copy.deepcopy(A); e.update(id=i,x=x,y=y,strokeColor=COL[layer][1]); return e
def text(i,x,y,t,fs,tmpl=SUB,color=None):
    e=copy.deepcopy(tmpl); e.update(id=i,x=x,y=y,text=t,fontSize=fs)
    if color: e["strokeColor"]=color
    return e
X=[400,690,980]; W=270; SPAN2=X[2]+W-X[1]; SPAN3=X[2]+W-X[0]
rows=[(1,170,110,"1. Presentation\nwhere do I talk to it?"),(2,300,110,"2. Agent\nwhat decides and acts?"),
      (3,430,150,"3. Execution\nwhere does it act?"),(4,600,110,"4. Inference\nwhich model answers?")]
els=[by[None] if None in by else base[0]]
els=[base[0]]
els[0]=dict(base[0],width=1300,height=900)
els+=[text("title",40,20,"The four layers of an AI product",TITLE["fontSize"],TITLE),
      text("subtitle",40,64,"one question per layer; a chatbot answers, an agent acts on your behalf (OBO), in a cloud or on your machine",18),
      text("h1",X[0],120,"Chatbot",20,TITLE), text("h2",X[1],108,"Agent on your behalf,\nin a vendor's cloud",20,TITLE),
      text("h3",X[2],108,"Agent on your behalf,\non your machine",20,TITLE)]
for n,y,h,lab in rows:
    els.append(rect(f"l{n}",40,y,330,h,lab,n,20)); els.append(arrow(f"l{n}a",370,y+h/2,n))
# 1 presentation
els+=[rect("c1",X[0],170,W,110,"chat app: web,\ndesktop, phone",1),
      rect("k1",X[1],170,W,110,"web or mobile app,\na mention in GitHub",1),
      rect("m1",X[2],170,W,110,"terminal (CLI), IDE\nextension, desktop app",1)]
# 2 agent
els+=[rect("c2",X[0],300,W,110,"no action loop:\nit only answers"),
      rect("a2",X[1],300,SPAN2,110,"the same loop in both: the model asks,\na tool acts, the result goes back, again",2,18)]
# 3 execution: the split
els+=[rect("c3",X[0],430,W,150,"its vendor's cloud:\nnone of your files,\nonly what you paste;\nat most a sandbox\nof its own"),
      rect("k3",X[1],430,W,150,"a vendor's container:\na copy of the repository,\nits own build and test\ntools, and only what\nit was given",3),
      rect("m3",X[2],430,W,150,"your machine:\nyour files, repositories,\nbuild and test tools,\nyour network, and every\ncredential already there",3)]
# 4 inference
els+=[rect("i4",X[0],600,SPAN3,110,"the same in all three: the model usually runs on a provider's servers;\nwho sells and operates the inference sets the contract on your data",4,18)]
els+=[rect("foot",40,740,X[2]+W-40,80,"On your machine the agent acts as you: same credentials, same network; permissions are the only guardrail.\nIn a vendor's cloud it has a copy of the repository and only what it was given; it works while you are away.",None,18)]
pathlib.Path(sys.argv[1]).write_text(json.dumps(els,ensure_ascii=False,indent=1)+"\n",encoding="utf-8")
