const grid=document.querySelector('#memory-grid');
const more=document.querySelector('#more-memories');
const load=document.querySelector('#load-more');
const status=document.querySelector('#gallery-status');
const total=grid.children.length+more.content.children.length;
function updateCount(){status.textContent=`已展示 ${grid.children.length} / ${total} 張來店紀念`;load.hidden=!more.content.children.length;load.style.display=load.hidden?'none':'';}
load.addEventListener('click',()=>{Array.from(more.content.children).slice(0,12).forEach(el=>grid.append(el));updateCount();});
updateCount();
const dialog=document.querySelector('#photo-dialog');
const large=document.querySelector('#large-photo');
document.addEventListener('click',event=>{const link=event.target.closest('a[data-photo]');if(!link||!dialog.showModal)return;event.preventDefault();large.src=link.href;large.alt=link.querySelector('img').alt;document.querySelector('#photo-caption').textContent=large.alt;dialog.showModal();});
document.querySelector('#close-photo').addEventListener('click',()=>dialog.close());
dialog.addEventListener('click',event=>{if(event.target===dialog){const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close();}});
dialog.addEventListener('close',()=>{large.removeAttribute('src');});
