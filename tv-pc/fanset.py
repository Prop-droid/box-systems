import json,base64,http.cookiejar,urllib.request,sys
B="https://tv-pc.tailb74909.ts.net"; NCT="00a4da18625f56275c89e2fcd25a83c08c5ad3326452fa7e252fcc8a89c92493"
pw=open("/home/tomas/.config/coolercontrol/tv-pc.pass").read().strip()
op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
def req(m,p,body=None,auth=None):
    r=urllib.request.Request(B+p,method=m,data=json.dumps(body).encode() if body is not None else None)
    r.add_header("Content-Type","application/json")
    if auth: r.add_header("Authorization","Basic "+base64.b64encode(auth.encode()).decode())
    return op.open(r,timeout=10).read()
req("POST","/login",auth="CCAdmin:"+pw)
ch,mode=sys.argv[1],sys.argv[2]
if mode=="off": req("PUT",f"/devices/{NCT}/settings/{ch}/manual",{"speed_fixed":0})
else: req("PUT",f"/devices/{NCT}/settings/{ch}/profile",{"profile_uid":f"tvpc-{ch}-quiet"})
print(ch,mode,"ok")
