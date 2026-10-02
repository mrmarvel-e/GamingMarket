const games = window.GM_GAMES || {};
const select = document.querySelector("#game-select");
const box = document.querySelector("#game-fields");
function render(){
  if(!select||!box)return;
  const g=games[select.value]; box.innerHTML="";
  if(!g)return;
  Object.keys(g.fields||{}).forEach(k=>{
    const label=document.createElement("label");
    const fieldName=k.replaceAll("_"," ").replace(/\b\w/g,c=>c.toUpperCase());
    label.textContent=fieldName+" (optional)";
    const input=document.createElement("input"); input.name=k; input.placeholder=fieldName; input.required=false;
    label.appendChild(input); box.appendChild(label);
  });
}
select?.addEventListener("change",render); render();
