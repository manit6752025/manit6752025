(function(){
var rm=matchMedia("(prefers-reduced-motion: reduce)").matches;
var $=function(s,r){return Array.prototype.slice.call((r||document).querySelectorAll(s))};
var b=document.querySelector(".burger"),n=document.querySelector(".nav nav");
b.onclick=function(){var o=n.classList.toggle("open");b.setAttribute("aria-expanded",o)};
var bar=document.querySelector(".bar");
addEventListener("scroll",function(){var h=document.documentElement;bar.style.width=(scrollY/(h.scrollHeight-innerHeight||1)*100)+"%"},{passive:true});
var g=document.querySelector(".glow");
if(!rm)addEventListener("mousemove",function(e){g.style.transform="translate("+e.clientX+"px,"+e.clientY+"px)"},{passive:true});
var cv=document.getElementById("bg"),cx=cv.getContext("2d"),pts=[],W,H;
function col(v){return getComputedStyle(document.body).getPropertyValue(v).trim()}
function size(){W=cv.width=innerWidth;H=cv.height=innerHeight;pts=[];for(var i=0;i<Math.min(70,W*H/16000);i++)pts.push({x:Math.random()*W,y:Math.random()*H,vx:(Math.random()-.5)*.35,vy:(Math.random()-.5)*.35})}
function draw(){cx.clearRect(0,0,W,H);var a=col("--acc"),c=col("--a2");
for(var i=0;i<pts.length;i++){var p=pts[i];p.x+=p.vx;p.y+=p.vy;if(p.x<0||p.x>W)p.vx*=-1;if(p.y<0||p.y>H)p.vy*=-1;
cx.fillStyle=c;cx.globalAlpha=.7;cx.beginPath();cx.arc(p.x,p.y,1.6,0,6.3);cx.fill();
for(var j=i+1;j<pts.length;j++){var q=pts[j],d=Math.hypot(p.x-q.x,p.y-q.y);if(d<130){cx.strokeStyle=a;cx.globalAlpha=(1-d/130)*.35;cx.beginPath();cx.moveTo(p.x,p.y);cx.lineTo(q.x,q.y);cx.stroke()}}}
if(!rm)requestAnimationFrame(draw)}
size();draw();addEventListener("resize",size);
var t=document.getElementById("type");
if(t){var L=t.dataset.lines.split("|"),l=0,c=0,d=false;
if(rm)t.textContent=L[0];else(function k(){var s=L[l];
if(!d){c++;t.textContent=s.slice(0,c);if(c===s.length){d=true;return setTimeout(k,1700)}}
else{c--;t.textContent=s.slice(0,c);if(c===0){d=false;l=(l+1)%L.length}}
setTimeout(k,d?22:50)})()}
function typeTerm(el){var L=el.dataset.term.split("|"),o=el.firstChild,i=0,j=0,out="";
if(rm){o.textContent=L.join("\n");return}
(function k(){if(i>=L.length)return;var s=L[i];if(j<s.length){out+=s[j++];o.textContent=out;setTimeout(k,16)}else{out+="\n";i++;j=0;setTimeout(k,160)}})()}
function count(el){var to=+el.dataset.count,s=performance.now();
(function k(now){var p=Math.min((now-s)/1200,1);el.textContent=Math.round(to*p);if(p<1)requestAnimationFrame(k)})(s)}
var io=new IntersectionObserver(function(es){es.forEach(function(e){if(!e.isIntersecting)return;var el=e.target;el.classList.add("in");
if(el.dataset.term&&!el.dataset.done){el.dataset.done=1;typeTerm(el)}
$("[data-count]",el).forEach(count);io.unobserve(el)})},{threshold:.15});
$(".card,.feat,.stat,.sec h2,.sec p,.chips,.term,.code,.bd,.imgs img,.panel,table,.groups>div,.pn").forEach(function(el,i){el.classList.add("rv");el.style.setProperty("--d",(i%4)*.08+"s");io.observe(el)});
$("[data-count]").forEach(function(el){var o=new IntersectionObserver(function(es){if(es[0].isIntersecting){count(el);o.disconnect()}});o.observe(el)});
if(!rm)$(".tilt").forEach(function(el){el.addEventListener("mousemove",function(e){var r=el.getBoundingClientRect(),x=(e.clientX-r.left)/r.width-.5,y=(e.clientY-r.top)/r.height-.5;el.style.transform="perspective(700px) rotateX("+(-y*8)+"deg) rotateY("+(x*8)+"deg) translateY(-3px)"});el.addEventListener("mouseleave",function(){el.style.transform=""})});
function put(k,v){$('[data-live="'+k+'"]').forEach(function(e){e.textContent=v})}
function load(u){return fetch("https://api.github.com/users/"+u).then(function(r){return r.json()}).then(function(a){return fetch("https://api.github.com/users/"+u+"/repos?per_page=100").then(function(r){return r.json()}).then(function(r){return{f:a.followers||0,n:a.public_repos||0,s:r.reduce?r.reduce(function(m,x){return m+(x.stargazers_count||0)},0):0}})})}
if($("[data-live]").length){var K="ma-live",c0=null;try{c0=JSON.parse(sessionStorage.getItem(K))}catch(e){}
function show(v){put("repos",v.n);put("stars",v.s);put("followers",v.f)}
if(c0)show(c0);else Promise.all([load("manit6752025"),load("NetCore-Technologies")]).then(function(r){var v={f:r[0].f+r[1].f,n:r[0].n+r[1].n,s:r[0].s+r[1].s};show(v);try{sessionStorage.setItem(K,JSON.stringify(v))}catch(e){}}).catch(function(){})}
})();
(function(){
document.querySelectorAll("[data-copy]").forEach(function(b){
var s=b.querySelector("small"),o=s.textContent;
b.addEventListener("click",function(){
var v=b.dataset.copy;
function ok(){s.textContent="copied";setTimeout(function(){s.textContent=o},1600)}
if(navigator.clipboard)navigator.clipboard.writeText(v).then(ok,function(){s.textContent=v});else s.textContent=v})})})();
(function(){
var rm=matchMedia("(prefers-reduced-motion: reduce)").matches;
if(!("IntersectionObserver" in window))document.querySelectorAll(".rv").forEach(function(e){e.classList.add("in")});
var J=[["Why did the router go to therapy?","Too many unresolved connections."],["Why do programmers prefer dark mode?","Because light attracts bugs."],["I’d tell you a UDP joke…","but you might not get it."],["I’d tell you a TCP joke…","but I’d keep repeating it until you got it."],["Why did the creeper cross the road?","To get to the other ssssside."],["Why does my Bedwars bed never sleep well?","It’s always feeling a bit exposed."],["How do you comfort a JavaScript bug?","You console it."],["It’s not DNS.","There’s no way it’s DNS. It was DNS."],["What do you call a fake noodle?","An impasta."],["Why was the container so calm?","It knew how to isolate its feelings."],["Why did the 5G tower get promoted?","Great reception."],["I’m reading a book about anti-gravity.","It’s impossible to put down."],["Why did the developer go broke?","He used up all his cache."],["Why did the Wi-Fi signal break up with the laptop?","It felt like they had no connection."],["What’s a Rust developer’s favourite game?","Borrow and Seek. Everything must be returned."]];
function spark(x,y){if(rm)return;var c=["#6C3BFF","#00D4FF","#ffffff"];for(var i=0;i<12;i++){var s=document.createElement("i");s.className="spark";var a=Math.random()*6.28,d=40+Math.random()*60;s.style.left=x+"px";s.style.top=y+"px";s.style.background=c[i%3];s.style.setProperty("--dx",Math.cos(a)*d+"px");s.style.setProperty("--dy",Math.sin(a)*d+"px");document.body.appendChild(s);setTimeout(function(el){el.remove()},900,s)}}
addEventListener("click",function(e){spark(e.clientX,e.clientY)});
document.querySelectorAll("[data-joke]").forEach(function(b){
var s=b.querySelector(".js"),p=b.querySelector(".jp"),btn=b.querySelector("button"),i=Math.floor(Math.random()*J.length),open=false;
function show(){s.textContent=J[i][0];p.textContent=J[i][1];p.classList.remove("show");btn.textContent="Punchline!";open=false}
show();
btn.addEventListener("click",function(e){
if(!open){p.classList.add("show");btn.textContent="Another one";open=true;var r=p.getBoundingClientRect();spark(r.left+r.width/2,r.top)}
else{i=(i+1+Math.floor(Math.random()*(J.length-1)))%J.length;show()}})});
if(!rm)document.querySelectorAll(".btn,.copy").forEach(function(b){
b.addEventListener("mousemove",function(e){var r=b.getBoundingClientRect();b.style.transform="translate("+((e.clientX-r.left-r.width/2)*.18)+"px,"+((e.clientY-r.top-r.height/2)*.3)+"px)"});
b.addEventListener("mouseleave",function(){b.style.transform=""})});
})();
