import os, json, time, sqlite3, secrets, hmac, hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

DB="accessvoice.db"
USER=os.getenv("ACCESSVOICE_ADMIN_USER","admin")
PASSWORD=os.getenv("ACCESSVOICE_ADMIN_PASSWORD","CHANGE_ME")
SECRET=os.getenv("ACCESSVOICE_SECRET","CHANGE_ME_SECRET")
HTML='<!doctype html>\n<html><head><meta name="viewport" content="width=device-width,initial-scale=1">\n<title>AccessVoice</title>\n<style>\nbody{font-family:Arial;margin:0;background:#f3f5f7;color:#17202a}header{background:#17202a;color:white;padding:18px;display:flex;justify-content:space-between}nav{padding:10px;background:white}button,input,select{font-size:17px;padding:11px;margin:4px;border-radius:8px;border:1px solid #bbb}.box{background:white;margin:15px auto;padding:20px;border-radius:15px;max-width:1000px}.grid{display:grid;grid-template-columns:1fr 1fr}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.card{background:white;padding:18px;border-radius:12px}.card b{font-size:28px;display:block}.row{display:flex;justify-content:space-between;padding:12px;border-bottom:1px solid #eee}.hide{display:none}@media(max-width:700px){.cards,.grid{grid-template-columns:1fr 1fr}}\n</style></head>\n<body>\n<div id="login" class="box" style="max-width:430px;margin-top:80px">\n<h1>♿ AccessVoice</h1><p>Hospital + Market Management</p>\n<input id="u" placeholder="Username" value="admin"><input id="pw" type="password" placeholder="Password">\n<button onclick="login()">Login</button><b id="msg"></b></div>\n<div id="app" class="hide">\n<header><h1>♿ AccessVoice</h1><div><select id="lang"><option value="en">English</option><option value="ku">کوردی</option><option value="ar">العربية</option><option value="tr">Türkçe</option></select><button onclick="logout()">Logout</button></div></header>\n<nav><button onclick="page(\'home\')">🏠 Dashboard</button><button onclick="page(\'market\')">🏪 Market</button><button onclick="page(\'hospital\')">🏥 Hospital</button></nav>\n<section id="home" class="box"><h2>Welcome</h2><div class="cards"><div class="card"><b id="pc">0</b>Products</div><div class="card"><b id="sc">0</b>Stock</div><div class="card"><b id="ptc">0</b>Patients</div><div class="card"><b id="sales">0</b>Sales today</div></div></section>\n<section id="market" class="box hide"><h2>🏪 Market</h2><h3>Add Product</h3><div class="grid">\n<input id="en" placeholder="English name"><input id="ku" placeholder="Kurdish name"><input id="ar" placeholder="Arabic name"><input id="tr" placeholder="Turkish name"><input id="bar" placeholder="Barcode"><input id="stock" type="number" placeholder="Stock"><input id="buy" type="number" placeholder="Buy price"><input id="sell" type="number" placeholder="Sell price"></div><button onclick="addProduct()">Add Product</button><h3>Inventory</h3><div id="products"></div></section>\n<section id="hospital" class="box hide"><h2>🏥 Hospital</h2><h3>Register Patient</h3><div class="grid"><input id="pn" placeholder="Patient name"><input id="phone" placeholder="Phone"><input id="doctor" placeholder="Doctor"><input id="appt" placeholder="Appointment"><input id="notes" placeholder="Notes"></div><button onclick="addPatient()">Register</button><h3>Patients</h3><div id="patients"></div></section>\n<script>\nlet tok=localStorage.av||"";\nconst $=id=>document.getElementById(id);\nasync function api(url,opt={}){opt.headers=Object.assign({"Content-Type":"application/json"},opt.headers||{});if(tok)opt.headers.Authorization="Bearer "+tok;let r=await fetch(url,opt);if(r.status==401)logout();return r}\nasync function login(){let r=await fetch("/login",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({u:$("u").value,p:$("pw").value})});if(!r.ok){$("msg").textContent="Wrong login";return}tok=(await r.json()).token;localStorage.av=tok;$("login").className="hide";$("app").className="";load()}\nfunction logout(){localStorage.removeItem("av");location.reload()}\nfunction page(id){["home","market","hospital"].forEach(x=>$(x).className=x==id?"box":"box hide");if(id=="market")products();if(id=="hospital")patients()}\nasync function load(){let a=await api("/products").then(r=>r.json()),b=await api("/patients").then(r=>r.json()),c=await api("/sales").then(r=>r.json());$("pc").textContent=a.length;$("sc").textContent=a.reduce((s,x)=>s+x.stock,0);$("ptc").textContent=b.length;$("sales").textContent=c}\nasync function products(){let d=await api("/products").then(r=>r.json());$("products").innerHTML=d.map(x=>"<div class=row><span><b>"+(x.name_en||"Product")+"</b><br>Stock: "+x.stock+" · "+x.sell+"</span><button onclick=\'sell("+x.id+")\'>Sell 1</button></div>").join("")||"No products"}\nasync function addProduct(){let b={name_en:$("en").value,name_ku:$("ku").value,name_ar:$("ar").value,name_tr:$("tr").value,barcode:$("bar").value,stock:+$("stock").value||0,buy:+$("buy").value||0,sell:+$("sell").value||0};await api("/products",{method:"POST",body:JSON.stringify(b)});products();load()}\nasync function sell(id){await api("/sell",{method:"POST",body:JSON.stringify({id:id})});products();load()}\nasync function patients(){let d=await api("/patients").then(r=>r.json());$("patients").innerHTML=d.map(x=>"<div class=row><span><b>"+x.name+"</b><br>Doctor: "+x.doctor+" · "+x.appointment+"</span></div>").join("")||"No patients"}\nasync function addPatient(){let b={name:$("pn").value,phone:$("phone").value,doctor:$("doctor").value,appointment:$("appt").value,notes:$("notes").value};await api("/patients",{method:"POST",body:JSON.stringify(b)});patients();load()}\nif(tok){$("login").className="hide";$("app").className="";load()}\n</script></body></html>'

def db():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row
 c.execute("CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY,name_en TEXT,name_ku TEXT,name_ar TEXT,name_tr TEXT,barcode TEXT,stock INTEGER,buy REAL,sell REAL)")
 c.execute("CREATE TABLE IF NOT EXISTS patients(id INTEGER PRIMARY KEY,name TEXT,phone TEXT,doctor TEXT,appointment TEXT,notes TEXT)")
 c.execute("CREATE TABLE IF NOT EXISTS sales(id INTEGER PRIMARY KEY,product_id INTEGER,qty INTEGER,total REAL,created INTEGER)")
 c.commit(); return c
def make_token():
 x=secrets.token_urlsafe(32); s=hmac.new(SECRET.encode(),x.encode(),hashlib.sha256).hexdigest(); return x+"."+s
def ok(t):
 if not t or "." not in t:return False
 x,s=t.rsplit(".",1); return hmac.compare_digest(hmac.new(SECRET.encode(),x.encode(),hashlib.sha256).hexdigest(),s)
class H(BaseHTTPRequestHandler):
 def out(self,code,data,typ="application/json"):
  self.send_response(code);self.send_header("Content-Type",typ);self.end_headers();self.wfile.write(data.encode() if isinstance(data,str) else data)
 def body(self):
  n=int(self.headers.get("Content-Length","0")); return json.loads(self.rfile.read(n) or b"{}")
 def auth(self): return ok(self.headers.get("Authorization","").replace("Bearer ",""))
 def do_GET(self):
  p=urlparse(self.path).path
  if p=="/": self.out(200,HTML,"text/html"); return
  if not self.auth(): self.out(401,"{}"); return
  c=db()
  if p=="/products": d=[dict(x) for x in c.execute("select * from products")]
  elif p=="/patients": d=[dict(x) for x in c.execute("select * from patients")]
  elif p=="/sales": d=c.execute("select coalesce(sum(total),0) from sales where created>?",(int(time.time())-86400,)).fetchone()[0]
  else: self.out(404,"{}");c.close();return
  self.out(200,json.dumps(d));c.close()
 def do_POST(self):
  p=urlparse(self.path).path;b=self.body()
  if p=="/login":
   if hmac.compare_digest(b.get("u",""),USER) and hmac.compare_digest(b.get("p",""),PASSWORD): self.out(200,json.dumps({"token":make_token()}))
   else:self.out(401,"{}")
   return
  if not self.auth():self.out(401,"{}");return
  c=db()
  if p=="/products":
   c.execute("insert into products(name_en,name_ku,name_ar,name_tr,barcode,stock,buy,sell) values(?,?,?,?,?,?,?,?)",(b.get("name_en",""),b.get("name_ku",""),b.get("name_ar",""),b.get("name_tr",""),b.get("barcode",""),b.get("stock",0),b.get("buy",0),b.get("sell",0)))
  elif p=="/sell":
   x=c.execute("select * from products where id=?",(b.get("id"),)).fetchone()
   if not x or x["stock"]<1:self.out(400,"{}");c.close();return
   c.execute("update products set stock=stock-1 where id=?",(x["id"],));c.execute("insert into sales(product_id,qty,total,created) values(?,?,?,?)",(x["id"],1,x["sell"],int(time.time())))
  elif p=="/patients":
   c.execute("insert into patients(name,phone,doctor,appointment,notes) values(?,?,?,?,?)",(b.get("name",""),b.get("phone",""),b.get("doctor",""),b.get("appointment",""),b.get("notes","")))
  else:self.out(404,"{}");c.close();return
  c.commit();c.close();self.out(200,"{}")
db()
ThreadingHTTPServer(("0.0.0.0",int(os.getenv("PORT","8000"))),H).serve_forever()
