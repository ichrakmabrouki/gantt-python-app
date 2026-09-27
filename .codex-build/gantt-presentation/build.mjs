import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const workspaceDir = "C:\\Users\\PC\\Documents\\gantt_python";
const SKILL_DIR = "C:\\Users\\PC\\.codex\\plugins\\cache\\openai-primary-runtime\\presentations\\26.905.11957\\skills\\presentations";
const TMP_DIR = path.join(workspaceDir, ".codex-build", "gantt-presentation");
const FINAL_PPTX = path.join(workspaceDir, "exports", "presentation", "fonctionnement_app_gantt_atelier_v2.pptx");
const RUNTIME_PYTHON = "C:\\Users\\PC\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\python\\python.exe";
const { resolvePresentationFont, finalizePresentation } = await import(pathToFileURL(path.join(SKILL_DIR, "container_tools", "artifact_tool_utils.mjs")).href);
const font = resolvePresentationFont();
const colors = { navy: "#081B33", deep: "#102A43", blue: "#1677B8", cyan: "#36B6D6", lime: "#A8D13E", ink: "#172B4D", muted: "#587089", pale: "#F4F8FB", line: "#D6E2EC", white: "#FFFFFF", orange: "#F49A3F" };
const iconPath = (name) => path.join(workspaceDir, "assets", "icons", name);
const icon = async (name) => new Uint8Array(await fs.readFile(iconPath(name)));
const presentation = Presentation.create({ slideSize: { width: 1280, height: 720 } });

function box(slide, {left, top, width, height, fill = colors.white, radius = 18, line = "none", shadow, text, style}) {
  const shape = slide.shapes.add({ geometry: "rect", position: { left, top, width, height }, fill, line: line === "none" ? { fill: "none", width: 0 } : { style: "solid", fill: line, width: 1 }, borderRadius: radius, shadow });
  if (text) { shape.text = text; shape.text.style = { typeface: font, color: colors.ink, fontSize: 20, autoFit: "shrinkText", ...style }; }
  return shape;
}
function text(slide, value, left, top, width, height, style = {}) {
  const shape = slide.shapes.add({ geometry: "textbox", position: { left, top, width, height }, fill: "none", line: { fill: "none", width: 0 } });
  shape.text = value;
  shape.text.style = { typeface: font, color: colors.ink, fontSize: 20, autoFit: "shrinkText", ...style };
  return shape;
}
function heading(slide, title, subtitle) {
  text(slide, title, 72, 48, 1080, 54, { fontSize: 34, bold: true, color: colors.navy });
  if (subtitle) text(slide, subtitle, 72, 108, 1040, 34, { fontSize: 17, color: colors.muted });
  box(slide, { left: 72, top: 148, width: 84, height: 5, fill: colors.cyan, radius: 2 });
}
function footer(slide, page) {
  text(slide, "App Gantt Atelier", 72, 682, 240, 18, { fontSize: 11, color: colors.muted });
  text(slide, String(page).padStart(2, "0"), 1164, 682, 44, 18, { fontSize: 11, color: colors.muted, align: "right" });
}
function note(slide, body) { slide.speakerNotes.textFrame.setText(body); }
async function addIcon(slide, file, left, top, width, height, alt) { slide.images.add({ blob: await icon(file), contentType: "image/png", alt, fit: "contain", position: { left, top, width, height } }); }

// 1 Cover
{
  const s = presentation.slides.add(); s.background.fill = colors.navy;
  box(s, { left: 0, top: 0, width: 1280, height: 720, fill: colors.navy, radius: 0 });
  box(s, { left: 0, top: 0, width: 408, height: 720, fill: colors.deep, radius: 0 });
  box(s, { left: 72, top: 86, width: 148, height: 7, fill: colors.lime, radius: 3 });
  text(s, "APP GANTT\nATELIER", 72, 142, 625, 170, { fontSize: 58, bold: true, color: colors.white, breakLine: false });
  text(s, "Pilotage et optimisation de l’ordonnancement en atelier", 72, 340, 570, 56, { fontSize: 23, color: "#DCEBF5" });
  text(s, "Présentation du fonctionnement", 72, 614, 420, 30, { fontSize: 17, color: colors.cyan });
  const timeline = ["Données", "Optimisation", "Planning", "Décision"];
  timeline.forEach((item, i) => { const x = 700 + i * 128; box(s, { left: x, top: 510 - i * 60, width: 94, height: 94, fill: i === 3 ? colors.lime : "#173D62", radius: 47 }); text(s, item, x - 15, 615 - i * 60, 125, 26, { fontSize: 14, bold: true, color: i === 3 ? colors.lime : "#E8F4FC", align: "center" }); });
  note(s, "Présentation basée sur les fonctionnalités du dépôt local app.py. URL publique fournie par l’utilisateur : https://appgantt-atelier.streamlit.app/");
}

// 2 Purpose
{
  const s = presentation.slides.add(); s.background.fill = colors.pale; heading(s, "Rôle de l’application", "Un outil web pour transformer des données de production en planning exploitable");
  await addIcon(s, "icon-brain.png", 775, 190, 330, 330, "Icône d’optimisation");
  text(s, "L’application aide l’atelier à organiser les opérations, visualiser la charge des machines et mesurer l’impact de l’ordonnancement.", 72, 206, 590, 95, { fontSize: 28, color: colors.ink });
  const points = ["Importer les données des ordres de fabrication", "Calculer un planning optimisé", "Comparer les indicateurs opérationnels et économiques"];
  points.forEach((p, i) => { box(s, { left: 72, top: 345 + i * 76, width: 550, height: 52, fill: colors.white, radius: 12, line: colors.line }); box(s, { left: 88, top: 358 + i * 76, width: 26, height: 26, fill: colors.cyan, radius: 13, text: String(i + 1), style: { fontSize: 14, bold: true, color: colors.white, align: "center" } }); text(s, p, 132, 358 + i * 76, 456, 28, { fontSize: 18 }); });
  footer(s, 2); note(s, "Source : app.py, pages Données, Planning et KPI.");
}

// 3 Workflow
{
  const s = presentation.slides.add(); s.background.fill = colors.white; heading(s, "Parcours utilisateur", "Le flux suit la logique de l’atelier, de l’import à la décision");
  const steps = [
    ["1", "Connexion", "Compte utilisateur et session sécurisée", "icon-user.png", colors.blue],
    ["2", "Données", "Import du fichier de production ou démonstration", "icon-data.png", colors.cyan],
    ["3", "Calcul", "Choix du mode puis lancement de l’optimisation", "icon-play.png", colors.orange],
    ["4", "Lecture", "Gantt, KPIs, historique et export", "icon-chart.png", colors.lime],
  ];
  const cards=[];
  for (let i=0;i<steps.length;i++) { const [num,title,body,file,c] = steps[i]; const x=64+i*302; const card=box(s,{left:x,top:225,width:254,height:296,fill:colors.pale,radius:20,line:colors.line}); cards.push(card); box(s,{left:x+28,top:250,width:42,height:42,fill:c,radius:21,text:num,style:{fontSize:18,bold:true,color:i===3?colors.navy:colors.white,align:"center"}}); await addIcon(s,file,x+157,246,58,58,title); text(s,title,x+28,330,190,37,{fontSize:25,bold:true,color:colors.navy}); text(s,body,x+28,380,196,76,{fontSize:16,color:colors.muted}); }
  for (let i=0;i<3;i++) s.shapes.connect(cards[i],cards[i+1],{kind:"straight",fromSide:"right",toSide:"left",line:{style:"solid",fill:colors.cyan,width:3},tail:{type:"arrow",width:"sm",length:"sm"}});
  footer(s, 3); note(s, "Source : app.py, navigation latérale et authentification.");
}

// 4 Data and optimizer
{
  const s = presentation.slides.add(); s.background.fill = colors.pale; heading(s, "Données et optimisation", "Le calcul s’appuie sur les opérations, les pièces et la capacité des machines");
  const a=box(s,{left:86,top:220,width:285,height:300,fill:colors.white,radius:20,line:colors.line}); const b=box(s,{left:498,top:220,width:285,height:300,fill:colors.navy,radius:20}); const c=box(s,{left:910,top:220,width:285,height:300,fill:colors.white,radius:20,line:colors.line});
  await addIcon(s,"icon-document.png",182,246,90,90,"Fichier de production"); await addIcon(s,"icon-brain.png",594,246,90,90,"Moteur d’optimisation"); await addIcon(s,"icon-calendar.png",1006,246,90,90,"Planning obtenu");
  text(s,"Fichier d’entrée",112,360,235,34,{fontSize:24,bold:true,color:colors.navy,align:"center"}); text(s,"Opérations\nMachines\nOrdres de fabrication",116,410,226,82,{fontSize:17,color:colors.muted,align:"center"});
  text(s,"Optimiseur",524,360,235,34,{fontSize:24,bold:true,color:colors.white,align:"center"}); text(s,"Respecte les contraintes\net cherche un ordre\nde production pertinent",528,410,226,82,{fontSize:17,color:"#DCEBF5",align:"center"});
  text(s,"Planning",936,360,235,34,{fontSize:24,bold:true,color:colors.navy,align:"center"}); text(s,"Début et fin\nde chaque opération\npar machine",940,410,226,82,{fontSize:17,color:colors.muted,align:"center"});
  s.shapes.connect(a,b,{kind:"straight",fromSide:"right",toSide:"left",line:{style:"solid",fill:colors.blue,width:3},tail:{type:"arrow",width:"med",length:"med"}}); s.shapes.connect(b,c,{kind:"straight",fromSide:"right",toSide:"left",line:{style:"solid",fill:colors.blue,width:3},tail:{type:"arrow",width:"med",length:"med"}});
  footer(s,4); note(s,"Source : app.py, page Données et logique de planification.");
}

// 5 Gantt
{
  const s = presentation.slides.add(); s.background.fill = colors.white; heading(s, "Diagramme de Gantt", "Une lecture visuelle de l’occupation des ressources au fil du temps");
  text(s,"L’utilisateur filtre le planning par machine, jour et pièce ou job. Le Gantt affiche les opérations sur une échelle de temps.",72,190,510,95,{fontSize:23,color:colors.ink});
  const panel=box(s,{left:645,top:185,width:535,height:400,fill:colors.navy,radius:20});
  text(s,"MACHINE 01",680,230,150,22,{fontSize:13,bold:true,color:"#CBE7F5"}); text(s,"MACHINE 02",680,327,150,22,{fontSize:13,bold:true,color:"#CBE7F5"}); text(s,"MACHINE 03",680,424,150,22,{fontSize:13,bold:true,color:"#CBE7F5"});
  [0,1,2,3,4].forEach(i=>box(s,{left:830+i*64,top:215,width:1,height:270,fill:"#355878",radius:0}));
  [[830,222,155,colors.cyan],[1005,222,98,colors.orange],[862,319,112,colors.lime],[991,319,154,colors.cyan],[830,416,89,colors.orange],[938,416,165,colors.lime]].forEach(([l,t,w,c])=>box(s,{left:l,top:t,width:w,height:42,fill:c,radius:8}));
  text(s,"Filtres de lecture\nMachine, jour, pièce ou job",72,350,465,65,{fontSize:22,bold:true,color:colors.blue}); text(s,"Le diagramme aide à repérer les périodes chargées, les enchaînements et les temps disponibles.",72,445,475,70,{fontSize:19,color:colors.muted});
  footer(s,5); note(s,"Source : app.py, page Planning. Le visuel Gantt est une représentation illustrative, pas une donnée réelle.");
}

// 6 KPI
{
  const s = presentation.slides.add(); s.background.fill = colors.pale; heading(s, "Indicateurs de performance", "Les résultats techniques deviennent des éléments de pilotage");
  const metrics=[ ["Makespan", "Durée totale du planning"], ["Utilisation", "Charge moyenne des machines"], ["Temps d’attente", "Capacité non occupée"], ["Coût et marge", "Lecture économique par OF et pièce"] ];
  metrics.forEach((m,i)=>{const x=76+(i%2)*570,y=205+Math.floor(i/2)*175;box(s,{left:x,top:y,width:535,height:140,fill:colors.white,radius:18,line:colors.line,shadow:"shadow-sm"});box(s,{left:x+26,top:y+28,width:10,height:80,fill:i%2===0?colors.cyan:colors.lime,radius:5});text(s,m[0],x+60,y+31,405,35,{fontSize:24,bold:true,color:colors.navy});text(s,m[1],x+60,y+76,405,30,{fontSize:18,color:colors.muted});});
  text(s,"Les onglets couvrent la performance, les coûts par OF, le profit et la marge, ainsi que les visualisations.",76,590,1060,42,{fontSize:20,color:colors.ink,align:"center"});
  footer(s,6); note(s,"Source : app.py, page KPI.");
}

// 7 Persistence and export
{
  const s = presentation.slides.add(); s.background.fill = colors.white; heading(s, "Historique, analytics et export", "Le résultat peut être conservé, contrôlé et partagé");
  const items=[ ["Historique", "Archivage des journées et rechargement d’un planning antérieur", "icon-history.png"], ["Analytics", "Suivi des accès et consultation réservée à l’administrateur", "icon-chart.png"], ["Export", "Production de fichiers CSV, Excel ou Gantt HTML", "icon-export.png"] ];
  for(let i=0;i<items.length;i++){const [ttl,body,file]=items[i];const x=85+i*375;box(s,{left:x,top:222,width:330,height:285,fill:i===1?colors.navy:colors.pale,radius:22,line:i===1?"none":colors.line});await addIcon(s,file,x+123,249,84,84,ttl);text(s,ttl,x+36,357,258,34,{fontSize:25,bold:true,color:i===1?colors.white:colors.navy,align:"center"});text(s,body,x+42,414,246,58,{fontSize:16,color:i===1?"#DCEBF5":colors.muted,align:"center"});}
  footer(s,7); note(s,"Source : app.py, pages Historique, Analytics et Export.");
}

// 8 Cloud and conclusion
{
  const s = presentation.slides.add(); s.background.fill = colors.navy;
  text(s,"Application en ligne",72,68,790,55,{fontSize:38,bold:true,color:colors.white});
  text(s,"Le lien fourni utilise le domaine streamlit.app. La page publique affiche le message de réveil du serveur, ce qui confirme un déploiement sur Streamlit Community Cloud.",72,142,785,84,{fontSize:23,color:"#DCEBF5"});
  const cloud=box(s,{left:900,top:88,width:220,height:118,fill:"#173D62",radius:59,text:"Cloud\nStreamlit",style:{fontSize:24,bold:true,color:colors.white,align:"center"}});
  const users=box(s,{left:900,top:360,width:220,height:118,fill:colors.lime,radius:59,text:"Utilisateurs\nweb",style:{fontSize:24,bold:true,color:colors.navy,align:"center"}});
  s.shapes.connect(users,cloud,{kind:"straight",fromSide:"top",toSide:"bottom",line:{style:"solid",fill:colors.cyan,width:4},head:{type:"arrow",width:"med",length:"med"},tail:{type:"arrow",width:"med",length:"med"}});
  text(s,"À retenir",72,300,300,35,{fontSize:26,bold:true,color:colors.lime});
  const takeaways=["Accès depuis différents PC, réseaux et adresses IP", "Calcul et données centralisés côté application et Supabase", "Le déploiement reste à surveiller avec les journaux Streamlit et l’état du projet Supabase"]; 
  takeaways.forEach((p,i)=>{box(s,{left:72,top:356+i*78,width:725,height:52,fill:"#173D62",radius:12});text(s,p,98,369+i*78,670,27,{fontSize:18,color:colors.white});});
  text(s,"https://appgantt-atelier.streamlit.app/",72,657,660,24,{fontSize:15,color:colors.cyan});
  note(s,"Vérification effectuée le 21 septembre 2026 via l’URL fournie. La page a répondu avec le message Streamlit : le serveur est en phase de réveil. Cela constitue un signal de déploiement cloud, mais pas une validation complète des fonctions nécessitant une authentification.");
}

const candidatePath = path.join(TMP_DIR, "candidate.pptx");
await (await PresentationFile.exportPptx(presentation)).save(candidatePath);
const requirements = { explicitTotalSlideCount: 8, requiredNativeTableOwnerSlides: [], requiredNativeChartOwnerSlides: [] };
await finalizePresentation({ ...requirements, workspaceDir, candidatePath, finalPath: FINAL_PPTX, pythonExecutable: RUNTIME_PYTHON, integrityValidatorPath: path.join(SKILL_DIR,"container_tools","inspect_presentation_package_integrity.py"), layoutValidatorPath: path.join(SKILL_DIR,"container_tools","inspect_presentation_layout_geometry.py"), layoutArgs:["--expected-slide-size-emu","12192000,6858000","--validate-bullet-geometry","--validate-heading-fit"], fontPolicy:{basis:"design",families:[font]}, verifyArtifactToolImport:true, receiptPath:path.join(TMP_DIR,"validation-v2.json") });
console.log(FINAL_PPTX);
