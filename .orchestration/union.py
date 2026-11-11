import pathlib,re,sys
p=pathlib.Path(sys.argv[1]); s=p.read_text(encoding="utf-8")
s=re.sub(r"^<<<<<<< [^\n]*\n(.*?)^=======\n(.*?)^>>>>>>> [^\n]*\n", lambda m: m.group(2)+m.group(1), s, flags=re.S|re.M)
p.write_text(s,encoding="utf-8")
