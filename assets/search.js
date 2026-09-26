/* USA Salaries search.
 * Understands three intents: an occupation ("nurse"), an occupation in a state ("nurse texas",
 * "texas nurse", "nurse TX") and a state on its own ("texas"). There are no state overview pages,
 * so a state on its own lists that state's occupation pages and never opens one by itself.
 * The index (/search-index.json, built by build.py) holds only indexable destinations.
 * The matching core below is shared with tests/search.test.js. */
(function(root){
var ABBR_WORDS={IN:1,OR:1,ME:1,OK:1,HI:1,OH:1,PA:1,AL:1,DE:1,CO:1,MA:1,LA:1,ID:1,MD:1,MS:1,MO:1,NE:1,WA:1,GA:1,SC:1,VA:1,AR:1,UT:1,NY:0};
function norm(s){return s.toLowerCase().replace(/[^a-z0-9 ]+/g,' ').replace(/\s+/g,' ').trim()}
function stem(w){return w.replace(/(ies)$/,'y').replace(/(ers|ors|ists|ians|ants|ents|ics|s)$/,function(m){return m==='ies'?'y':m.slice(0,-1)})}
function prep(idx){
  idx.states=idx.s.map(function(s,i){return {i:i,name:s[0],slug:s[1],abbr:s[2],n:norm(s[0])}})
    .sort(function(a,b){return b.n.length-a.n.length});
  idx.jobs=idx.j.map(function(j){var n=norm(j[0]);return {title:j[0],slug:j[1],cat:j[2],avg:j[3],emp:j[4],missing:j[5],n:n,
    words:n.split(' ').map(stem),catn:norm(j[2])}});
  return idx;
}
// Pull a state out of the query: full names (longest first) anywhere; 2-letter codes only when typed in capitals
// and not an ordinary word, or when they are the whole second token (e.g. "nurse tx").
var STOP={'in':1,salary:1,salaries:1,pay:1,wage:1,wages:1,average:1,avg:1,the:1,jobs:1,job:1,for:1,how:1,much:1,does:1,a:1,make:1,makes:1,per:1,year:1,annual:1};
function findState(idx,raw){
  var q=' '+norm(raw)+' ';
  for(var k=0;k<idx.states.length;k++){var s=idx.states[k];var p=' '+s.n+' ';var at=q.indexOf(p);
    if(at>=0)return {state:s,rest:(q.slice(0,at)+' '+q.slice(at+p.length)).trim()};}
  var toks=raw.trim().split(/\s+/);
  for(var t=0;t<toks.length;t++){var tok=toks[t].replace(/[^A-Za-z]/g,'');if(tok.length!==2)continue;
    var up=tok.toUpperCase();var ok=(tok===up&&!ABBR_WORDS[up])||(toks.length>1&&t===toks.length-1&&!ABBR_WORDS[up]);
    if(!ok)continue;
    for(var m=0;m<idx.states.length;m++)if(idx.states[m].abbr===up){var r=toks.slice();r.splice(t,1);return {state:idx.states[m],rest:norm(r.join(' '))};}}
  return {state:null,rest:norm(raw)};
}
function scoreJob(j,terms,phrase){
  if(!terms.length)return 0;var s=0;
  for(var i=0;i<terms.length;i++){var t=stem(terms[i]),hit=0;
    for(var w=0;w<j.words.length;w++){if(j.words[w]===t){hit=3;break}if(j.words[w].indexOf(t)===0)hit=Math.max(hit,2)}
    if(!hit&&j.catn.indexOf(terms[i])===0)hit=1;
    if(!hit)return 0;s+=hit;
    if(j.words[j.words.length-1]===t)s+=0.75;} // head noun: "nurse" prefers Registered Nurses over Nurse Practitioners
  if(j.n===phrase||stem(j.n)===stem(phrase))s+=10;
  if(j.avg)s+=1; // BLS-backed first
  return s+Math.log10(1+j.emp)/4; // popularity orders equally good matches
}
function search(idx,raw,limit){
  limit=limit||8;var f=findState(idx,raw),st=f.state,terms=f.rest?f.rest.split(' ').filter(function(t){return !STOP[t]}):[];f.rest=terms.join(' ');
  var jobs=idx.jobs.map(function(j){return {j:j,sc:scoreJob(j,terms,f.rest)}}).filter(function(x){return x.sc>0})
    .sort(function(a,b){return b.sc-a.sc});
  var out={state:st?{name:st.name,slug:st.slug}:null,mode:'',groups:[]};
  function stateOk(j){return j.missing!==-1&&j.missing.indexOf(st.i)<0}
  if(st&&!terms.length){ // State context only: no state hub exists, so list real occupation/state pages
    out.mode='state';
    var top=idx.jobs.filter(stateOk).sort(function(a,b){return b.emp-a.emp}).slice(0,limit);
    out.groups.push({label:'Largest occupations in '+st.name,kind:'occupation+state',items:top.map(function(j){
      return {title:j.title+' in '+st.name,url:'/salary/'+j.slug+'/'+st.slug+'/',kind:'occupation+state'}})});
    return out;}
  if(st){ // Occupation + state: link straight to the existing state URL when BLS has that pair
    out.mode='occupation+state';
    out.groups.push({label:'In '+st.name,kind:'occupation+state',items:jobs.slice(0,limit).map(function(x){var j=x.j;
      return stateOk(j)?{title:j.title+' in '+st.name,url:'/salary/'+j.slug+'/'+st.slug+'/',kind:'occupation+state'}
        :{title:j.title,url:'/salary/'+j.slug+'/',kind:'occupation',note:'No BLS figure for '+st.name+' · U.S. page'}})});
    return out;}
  out.mode=jobs.length?'occupation':'none';
  out.groups.push({label:'Occupations',kind:'occupation',items:jobs.slice(0,limit).map(function(x){var j=x.j;
    return {title:j.title,url:'/salary/'+j.slug+'/',kind:'occupation',note:j.avg?'':'No BLS annual figure'}})});
  return out;
}
// Enter may only open a result the user intended: never in state-context mode, where the list is a menu of occupations.
function enterTarget(r){if(r.mode==='state'||r.mode==='none')return null;var g=r.groups[0];return g&&g.items[0]?g.items[0].url:null}
root.USSearch={enterTarget:enterTarget,prep:prep,search:search,findState:findState};
})(typeof window!=='undefined'?window:globalThis);

(function(){
  if(typeof document==='undefined')return;
  var idx=null,loading=null,uid=0;
  function load(){
    if(idx)return Promise.resolve(idx);
    if(!loading)loading=fetch('/search-index.json').then(function(r){return r.json()}).then(function(d){idx=USSearch.prep(d);return idx});
    return loading;
  }
  function esc(t){return String(t).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
  function setup(box){
    var input=box.querySelector('input'),list=box.querySelector('.search-list'),status=box.querySelector('[role=status]');
    var id='sr'+(++uid),opts=[],active=-1,result=null;
    list.id=id+'-list';input.setAttribute('aria-controls',list.id);
    function close(){list.hidden=true;input.setAttribute('aria-expanded','false');input.removeAttribute('aria-activedescendant');active=-1}
    function setActive(i){
      opts.forEach(function(o){o.classList.remove('active');o.setAttribute('aria-selected','false')});
      active=i;
      if(i>=0&&opts[i]){opts[i].classList.add('active');opts[i].setAttribute('aria-selected','true');input.setAttribute('aria-activedescendant',opts[i].id);opts[i].scrollIntoView({block:'nearest'})}
      else input.removeAttribute('aria-activedescendant');
    }
    function render(){
      var v=input.value.trim();
      if(v.length<2){close();opts=[];if(status)status.textContent='';return}
      load().then(function(ix){
        if(input.value.trim()!==v)return;
        var r=USSearch.search(ix,v,8),h='',n=0;result=r;
        if(r.mode==='state')h+='<h4>No state overview page · choose an occupation in '+esc(r.state.name)+'</h4>';
        else if(r.mode==='occupation+state')h+='<h4>Occupations in '+esc(r.state.name)+'</h4>';
        else if(r.mode==='occupation')h+='<h4>Occupations · United States</h4>';
        r.groups.forEach(function(g){g.items.forEach(function(it){
          h+='<a role="option" aria-selected="false" id="'+id+'-'+(n++)+'" href="'+esc(it.url)+'"><span>'+esc(it.title)+'</span>'
            +'<small>'+(it.kind==='occupation+state'?esc(r.state.name):'U.S.')+'</small>'
            +(it.note?'<span class="note">'+esc(it.note)+'</span>':'')+'</a>';
        })});
        if(!n)h='<p class="empty">No occupation matches “'+esc(v)+'”. Try a broader job title, or <a href="/salary/">browse all salaries</a>.</p>';
        h+='<div class="foot"><span class="keys">↑ ↓ move · Enter open · Esc close</span><span>BLS OEWS data</span></div>';
        list.innerHTML=h;list.hidden=false;input.setAttribute('aria-expanded','true');
        opts=[].slice.call(list.querySelectorAll('[role=option]'));
        opts.forEach(function(o,i){o.addEventListener('mousemove',function(){if(active!==i)setActive(i)})});
        if(status)status.textContent=(n?n+(n===1?' result':' results'):'No results')+(r.state?' in '+r.state.name:'');
        // Preselect only when Enter has an intended destination; a state alone has none.
        setActive(n&&USSearch.enterTarget(r)?0:-1);
      });
    }
    input.addEventListener('input',render);
    input.addEventListener('focus',function(){load();if(input.value.trim().length>1)render()});
    input.addEventListener('keydown',function(e){
      var n=opts.length,open=!list.hidden;
      if(e.key==='ArrowDown'){e.preventDefault();if(!open){render();return}if(n)setActive((active+1)%n)}
      else if(e.key==='ArrowUp'){e.preventDefault();if(open&&n)setActive(active<=0?n-1:active-1)}
      else if(e.key==='Enter'){
        e.preventDefault();
        if(open&&active>=0&&opts[active]){window.location.href=opts[active].getAttribute('href');return}
        if(!open&&input.value.trim().length>1)render();
      }
      else if(e.key==='Escape'){e.preventDefault();if(open)close();else{input.value='';if(status)status.textContent=''}}
      else if(e.key==='Tab')close();
    });
    box.querySelector('form').addEventListener('submit',function(e){
      // Without JavaScript the form goes to /salary/; with it, Enter is handled above.
      e.preventDefault();
    });
    document.addEventListener('click',function(e){if(!box.contains(e.target))close()});
  }
  // /salary/ directory: filter the full list in place (the list itself is plain HTML, so it works without JS).
  function hubFilter(tools){
    var input=tools.querySelector('input'),count=tools.querySelector('.hub-count'),empty=tools.querySelector('.hub-empty');
    var cats=[].slice.call(document.querySelectorAll('.hub-cat')),total=document.querySelectorAll('.hub-list li').length;
    tools.hidden=false;
    function apply(){
      var terms=input.value.toLowerCase().split(/\s+/).filter(Boolean),shown=0;
      cats.forEach(function(c){var n=0;
        [].forEach.call(c.querySelectorAll('li'),function(li){var t=li.querySelector('a').textContent.toLowerCase();
          var ok=terms.every(function(w){return t.indexOf(w)>-1||t.indexOf(w.replace(/s$/,''))>-1});li.hidden=!ok;if(ok)n++});
        c.hidden=!n;shown+=n});
      count.textContent=terms.length?shown+' of '+total+' occupations':total+' occupations';
      empty.hidden=shown>0;
    }
    input.addEventListener('input',apply);
    var q=(location.search.match(/[?&]q=([^&]*)/)||[])[1];
    if(q){input.value=decodeURIComponent(q.replace(/\+/g,' '))}
    apply();
  }
  function init(){
    [].forEach.call(document.querySelectorAll('[data-search]'),setup);
    var hub=document.querySelector('[data-hub-filter]');if(hub)hubFilter(hub);
    var header=document.querySelector('.site-header');
    var sBtn=document.querySelector('[data-toggle=search]'),mBtn=document.querySelector('[data-toggle=menu]');
    function toggle(cls,btn,other){
      var on=!header.classList.contains(cls);
      header.classList.remove('search-open','menu-open');
      if(sBtn)sBtn.setAttribute('aria-expanded','false');if(mBtn)mBtn.setAttribute('aria-expanded','false');
      if(on){header.classList.add(cls);btn.setAttribute('aria-expanded','true')}
      if(on&&cls==='search-open'){var i=header.querySelector('.header-search input');if(i)i.focus()}
    }
    if(sBtn)sBtn.addEventListener('click',function(){toggle('search-open',sBtn)});
    if(mBtn)mBtn.addEventListener('click',function(){toggle('menu-open',mBtn)});
    document.addEventListener('keydown',function(e){
      if(e.key==='Escape'&&header&&(header.classList.contains('menu-open'))){header.classList.remove('menu-open');if(mBtn){mBtn.setAttribute('aria-expanded','false');mBtn.focus()}}
      if(e.key!=='/'||e.ctrlKey||e.metaKey||e.altKey)return;
      var t=document.activeElement;if(t&&(/^(input|textarea|select)$/i.test(t.tagName)||t.isContentEditable))return;
      var target=document.querySelector('.search-xl input')||document.querySelector('.header-search input');
      if(!target)return;
      if(target.offsetParent===null&&sBtn){header.classList.add('search-open');sBtn.setAttribute('aria-expanded','true')}
      e.preventDefault();target.focus();
    });
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
