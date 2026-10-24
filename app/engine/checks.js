() => {
  const out=[];
  const path=e=>e.id?'#'+CSS.escape(e.id):e===document.documentElement?'html':e===document.body?'body':path(e.parentElement)+' > '+e.tagName.toLowerCase()+':nth-of-type('+([...e.parentElement.children].filter(x=>x.tagName===e.tagName).indexOf(e)+1)+')';
  const visible=e=>!e.closest('[hidden],[inert],[aria-hidden="true"]')&&e.getClientRects().length&&getComputedStyle(e).visibility==='visible';
  const name=e=>{
    const refs=(e.getAttribute('aria-labelledby')||'').split(/\s+/).map(id=>document.getElementById(id)?.textContent||'').join(' ').trim();
    return refs||(e.getAttribute('aria-label')||'').trim()||[...(e.labels||[])].map(x=>x.textContent).join(' ').trim()||(e.getAttribute('title')||'').trim()||(e.innerText||'').trim()||[...e.querySelectorAll('img[alt],svg title')].map(x=>x.getAttribute('alt')||x.textContent).join(' ').trim();
  };
  const add=(rule,impact,message,e,wcag,principle,fix,category='violation')=>out.push({rule_id:rule,impact,message,selector:path(e),html:e.outerHTML.slice(0,2000),wcag_criteria:wcag,principle,wcag_level:category==='best-practice'?'—':'A',help_url:'',source:'basic',fix,category});
  if(!document.documentElement.lang.trim())add('html-has-lang','serious','Document language is missing.',document.documentElement,['3.1.1'],'understandable','Add the correct lang attribute to the html element.');
  if(!document.title.trim())add('document-title','serious','Page title is missing.',document.documentElement,['2.4.2'],'operable','Add a descriptive title element.');
  for(const e of document.querySelectorAll('img'))if(visible(e)&&!e.hasAttribute('alt')&&!name(e)&&!['presentation','none'].includes(e.getAttribute('role')))add('image-alt','serious','Image needs a text alternative.',e,['1.1.1'],'perceivable','Provide a meaningful text alternative or alt="" for a decorative image.');
  for(const e of document.querySelectorAll('input:not([type=hidden]):not([type=submit]):not([type=button]):not([type=reset]):not([type=image]),select,textarea'))if(visible(e)&&!name(e))add('label','serious','Form control needs an accessible label.',e,['1.3.1','4.1.2'],'robust','Associate a visible label or provide an accessible name.');
  for(const e of document.querySelectorAll('a[href],button'))if(visible(e)&&!name(e))add(e.tagName==='A'?'link-name':'button-name','serious','Interactive element needs an accessible name.',e,[e.tagName==='A'?'2.4.4':'4.1.2'],'operable','Add descriptive text or a valid accessible name.');
  if(!document.querySelector('h1'))add('page-has-heading-one','moderate','Consider a level-one heading.',document.body,[],'perceivable','Review the heading structure in context. A missing h1 alone does not prove a WCAG failure.','best-practice');
  if(!document.querySelector('main,[role=main]'))add('landmark-one-main','moderate','Consider a main landmark.',document.body,[],'perceivable','Review navigation and bypass mechanisms.','best-practice');
  return out;
}
