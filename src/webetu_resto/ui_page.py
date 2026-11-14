"""The single HTML page of the local interface (no external files, no CDN)."""

from __future__ import annotations

PAGE_HTML = r"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>Webetu Resto</title>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='9' fill='%234f46e5'/%3E%3Cpath d='M11 7v7a2 2 0 0 0 2 2v9M15 7v7a2 2 0 0 1-2 2M21 25V7c-2 1-3 4-3 8v2h3' fill='none' stroke='white' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E">
<style>
:root{
  --bg1:#f6f8ff; --bg2:#eef2ff; --card:rgba(255,255,255,.78); --card-solid:#fff;
  --text:#0f172a; --muted:#64748b; --line:rgba(15,23,42,.09);
  --accent:#4f46e5; --accent2:#7c3aed; --accent-soft:rgba(79,70,229,.10);
  --ok:#059669; --ok-bg:rgba(16,185,129,.14); --warn:#b45309; --warn-bg:rgba(245,158,11,.16);
  --bad:#dc2626; --bad-bg:rgba(239,68,68,.12); --info:#1d4ed8; --info-bg:rgba(59,130,246,.12);
  --shadow:0 1px 2px rgba(15,23,42,.05),0 12px 32px -12px rgba(15,23,42,.18);
  --radius:20px; color-scheme:light;
}
@media (prefers-color-scheme:dark){
  :root{
    --bg1:#0a0f1f; --bg2:#10172e; --card:rgba(24,31,56,.72); --card-solid:#182038;
    --text:#e8ecf8; --muted:#94a0bd; --line:rgba(255,255,255,.09);
    --accent:#818cf8; --accent2:#a78bfa; --accent-soft:rgba(129,140,248,.16);
    --ok:#34d399; --ok-bg:rgba(52,211,153,.14); --warn:#fbbf24; --warn-bg:rgba(251,191,36,.14);
    --bad:#f87171; --bad-bg:rgba(248,113,113,.14); --info:#93c5fd; --info-bg:rgba(147,197,253,.13);
    --shadow:0 1px 2px rgba(0,0,0,.3),0 16px 40px -14px rgba(0,0,0,.6);
    color-scheme:dark;
  }
}
*{box-sizing:border-box}
html,body{margin:0;min-height:100%}
body{min-height:100vh}
body{
  font-family:"Segoe UI Variable","Segoe UI",system-ui,-apple-system,"Noto Sans Arabic",Tahoma,Roboto,sans-serif;
  color:var(--text); line-height:1.5; -webkit-font-smoothing:antialiased;
  background:
    radial-gradient(900px 500px at 8% -10%,rgba(124,58,237,.16),transparent 60%),
    radial-gradient(800px 480px at 100% 0%,rgba(16,185,129,.13),transparent 55%),
    linear-gradient(180deg,var(--bg1),var(--bg2)) fixed;
}
.wrap{max-width:760px;margin:0 auto;padding:20px 16px 48px}
header{display:flex;align-items:center;gap:12px;padding:8px 2px 20px}
.logo{width:42px;height:42px;border-radius:13px;display:grid;place-items:center;color:#fff;
  background:linear-gradient(135deg,var(--accent),var(--accent2));box-shadow:0 8px 20px -8px var(--accent)}
.logo svg{width:22px;height:22px}
.brand{flex:1;min-width:0}
.brand b{display:block;font-size:17px;letter-spacing:-.01em}
.brand span{display:block;font-size:12.5px;color:var(--muted)}
.lang{display:flex;gap:2px;padding:3px;border-radius:999px;background:var(--accent-soft)}
.lang button{border:0;background:transparent;color:var(--muted);font:inherit;font-size:12.5px;font-weight:600;
  padding:5px 11px;border-radius:999px;cursor:pointer}
.lang button[aria-pressed=true]{background:var(--card-solid);color:var(--text);box-shadow:0 1px 3px rgba(0,0,0,.15)}
.card{background:var(--card);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);
  border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow);padding:22px;margin-bottom:16px}
.card.enter{animation:rise .35s ease both}
@keyframes rise{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
h1{font-size:22px;margin:0 0 6px;letter-spacing:-.02em}
h2{font-size:16px;margin:0;letter-spacing:-.01em}
.sub{color:var(--muted);margin:0 0 18px;font-size:14.5px}
.stepper{display:flex;align-items:center;gap:10px;margin-bottom:18px;font-size:13px;color:var(--muted)}
.stepper i{width:26px;height:26px;border-radius:50%;display:grid;place-items:center;font-style:normal;font-weight:700;
  background:var(--accent-soft);color:var(--muted)}
.stepper .on i{background:linear-gradient(135deg,var(--accent),var(--accent2));color:#fff}
.stepper .on{color:var(--text);font-weight:600}
.stepper hr{flex:1;border:0;height:2px;background:var(--line);margin:0}
label{display:block;font-size:13px;font-weight:600;margin:14px 0 6px}
.field{position:relative}
input[type=text],input[type=password]{width:100%;font:inherit;font-size:16px;color:var(--text);padding:13px 14px;
  border-radius:14px;border:1.5px solid var(--line);background:var(--card-solid);outline:none;transition:.15s}
input:focus{border-color:var(--accent);box-shadow:0 0 0 4px var(--accent-soft)}
.field .eye{position:absolute;inset-block:0;inset-inline-end:6px;border:0;background:transparent;color:var(--muted);
  cursor:pointer;padding:0 10px;border-radius:10px}
.field .eye:hover{color:var(--text)}
.field input.has-eye{padding-inline-end:46px}
svg.i{width:18px;height:18px;flex:none}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;font:inherit;font-weight:650;font-size:15px;
  border:0;border-radius:14px;padding:12px 18px;cursor:pointer;transition:.15s;color:var(--text);
  background:var(--accent-soft)}
.btn:hover{transform:translateY(-1px)}
.btn:active{transform:none}
.btn.primary{color:#fff;background:linear-gradient(135deg,var(--accent),var(--accent2));
  box-shadow:0 10px 22px -10px var(--accent)}
.btn.block{width:100%;margin-top:20px}
.btn.ghost{background:transparent;border:1.5px solid var(--line)}
.btn.danger{color:var(--bad);background:var(--bad-bg)}
.btn[disabled]{opacity:.55;cursor:not-allowed;transform:none}
.btn:focus-visible,.lang button:focus-visible,.sw:focus-visible,.eye:focus-visible,.opt:focus-within{
  outline:3px solid var(--accent-soft);outline-offset:2px}
.row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.spread{justify-content:space-between}
.note{display:flex;gap:10px;align-items:flex-start;font-size:13px;color:var(--muted);margin-top:16px}
.note svg{color:var(--ok);margin-top:2px}
.alert{display:flex;gap:10px;align-items:flex-start;border-radius:14px;padding:12px 14px;font-size:14px;margin-top:16px}
.alert svg{margin-top:2px}
.alert.bad{background:var(--bad-bg);color:var(--bad)}
.alert.warn{background:var(--warn-bg);color:var(--warn)}
.alert.info{background:var(--info-bg);color:var(--info)}
.alert a{color:inherit;font-weight:700}
.opts{display:grid;gap:10px;margin:6px 0 0}
.opt{display:flex;gap:12px;align-items:center;padding:14px;border-radius:16px;border:1.5px solid var(--line);
  background:var(--card-solid);cursor:pointer;transition:.15s}
.opt:hover{border-color:var(--accent)}
.opt input{accent-color:var(--accent);width:18px;height:18px;margin:0}
.opt.sel{border-color:var(--accent);background:var(--accent-soft)}
.opt .nm{font-weight:650}
.chips{display:flex;gap:6px;flex-wrap:wrap;margin-top:4px}
.chip{font-size:11.5px;font-weight:650;padding:2px 9px;border-radius:999px;background:var(--accent-soft);color:var(--muted)}
.chip.ru{background:var(--ok-bg);color:var(--ok)}
.pill{display:inline-flex;align-items:center;gap:8px;font-weight:700;font-size:15px;padding:7px 14px 7px 12px;border-radius:999px}
.pill .dot{width:9px;height:9px;border-radius:50%;background:currentColor;box-shadow:0 0 0 0 currentColor;animation:pulse 2s infinite}
.pill.ok{background:var(--ok-bg);color:var(--ok)} .pill.warn{background:var(--warn-bg);color:var(--warn)}
.pill.bad{background:var(--bad-bg);color:var(--bad)} .pill.info{background:var(--info-bg);color:var(--info)}
@keyframes pulse{0%{box-shadow:0 0 0 0 color-mix(in srgb,currentColor 55%,transparent)}
  70%{box-shadow:0 0 0 8px transparent}100%{box-shadow:0 0 0 0 transparent}}
.meta{color:var(--muted);font-size:13.5px;margin:12px 0 0}
.sw-row{display:flex;align-items:center;gap:14px;padding:14px 0;border-top:1px solid var(--line)}
.sw-row:first-of-type{border-top:0}
.sw-row .tx{flex:1;min-width:0}.sw-row b{display:block;font-size:14.5px}.sw-row span{font-size:13px;color:var(--muted)}
.sw{position:relative;width:48px;height:28px;border-radius:999px;border:0;background:var(--line);cursor:pointer;flex:none;transition:.2s}
.sw::after{content:"";position:absolute;top:3px;inset-inline-start:3px;width:22px;height:22px;border-radius:50%;background:#fff;
  box-shadow:0 1px 3px rgba(0,0,0,.3);transition:.2s}
.sw[aria-checked=true]{background:linear-gradient(135deg,var(--accent),var(--accent2))}
.sw[aria-checked=true]::after{inset-inline-start:23px}
.grid{width:100%;border-collapse:separate;border-spacing:0 8px;margin-top:8px}
.grid th{font-size:12.5px;color:var(--muted);font-weight:650;text-align:center;padding:0 4px 2px}
.grid th:first-child,.grid td:first-child{text-align:start}
.grid td{padding:0 4px;text-align:center}
.day{font-weight:650;font-size:14px;text-transform:capitalize}
.day small{display:block;color:var(--muted);font-weight:500;font-size:12px;text-transform:none}
.cell{display:inline-flex;align-items:center;justify-content:center;gap:6px;min-width:92px;padding:9px 10px;border-radius:12px;
  font-size:12.5px;font-weight:700}
.cell.booked{background:var(--ok-bg);color:var(--ok)}
.cell.missing{background:var(--warn-bg);color:var(--warn)}
.cell.not_served{background:transparent;color:var(--muted);font-weight:500}
.mealhead{display:inline-flex;align-items:center;gap:6px}
.skel{height:14px;border-radius:8px;background:linear-gradient(90deg,var(--line),transparent,var(--line));background-size:200% 100%;
  animation:sh 1.2s infinite;margin:10px 0}
@keyframes sh{from{background-position:200% 0}to{background-position:-200% 0}}
.spin{width:16px;height:16px;border-radius:50%;border:2.5px solid currentColor;border-top-color:transparent;animation:rot .7s linear infinite}
@keyframes rot{to{transform:rotate(360deg)}}
.toast{position:fixed;inset-inline:0;bottom:20px;display:flex;justify-content:center;pointer-events:none;z-index:9}
.toast div{background:var(--text);color:var(--bg1);padding:11px 18px;border-radius:999px;font-size:14px;font-weight:600;
  box-shadow:0 12px 30px -8px rgba(0,0,0,.4);animation:rise .25s ease both}
footer{color:var(--muted);font-size:12.5px;text-align:center;margin-top:24px}
.center{text-align:center;padding:40px 10px}
@media (max-width:520px){.cell{min-width:0;padding:8px 8px}.cell span{display:none}.card{padding:18px}}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="logo"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 2v7c0 1.1.9 2 2 2h4a2 2 0 0 0 2-2V2"/><path d="M7 2v20"/><path d="M21 15V2a5 5 0 0 0-5 5v6c0 1.1.9 2 2 2h3Zm0 0v7"/></svg></div>
    <div class="brand"><b>Webetu Resto</b><span id="tagline"></span></div>
    <div class="lang" role="group" aria-label="Language">
      <button data-lang="fr">FR</button><button data-lang="ar">عربي</button><button data-lang="en">EN</button>
    </div>
  </header>
  <main id="app" aria-live="polite"></main>
  <footer id="foot"></footer>
</div>
<div class="toast" id="toast" aria-live="polite"></div>
<script nonce="__NONCE__">
(() => {
"use strict";
const CSRF = "__CSRF__";
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));

const T = {
en:{tagline:"Your meals, booked automatically.",setup_title:"Connect your Webetu account",
setup_sub:"Enter the same matricule and password you use in the Webetu app. You only do this once.",
username:"Matricule",password:"Password",show:"Show",hide:"Hide",verify:"Check and continue",checking:"Checking…",
privacy:"Your password only leaves this computer to sign in to Webetu. It is saved in your user folder on this PC.",
step1:"Account",step2:"Restaurant",pick_title:"Choose your restaurant",
pick_sub:"A meal is only valid in the restaurant where it was booked.",connected:"Connected",residence:"Residence",
back:"Back",activate:"Save and activate",saving:"Saving…",badge_ru:"University restaurant",
status_active:"Automatic booking is on",status_paused:"Automatic booking is paused",status_attention:"Needs your attention",
status_starting:"Starting — first check soon",status_stale:"No successful check for {n} days",status_engine:"The background engine is stopped",
next_pass:"Daily pass around {time}",last_check:"Last check",never:"never",today:"today",yesterday:"yesterday",days_ago:"{n} days ago",
booked_n:"{n} booked",book_now:"Book now",booking:"Booking…",refresh:"Refresh",auto_label:"Automatic booking",
auto_hint:"Books the next 3 days for you, every day.",days_title:"Your next 3 days",meal1:"Breakfast",meal2:"Lunch",meal3:"Dinner",
s_booked:"Booked",s_missing:"Not yet",s_not_served:"Not served",loading_status:"Checking your reservations…",
warn_stale:"If this computer stays off for more than 3 days, some meals can no longer be booked. Open it every day, or use the always-on GitHub option.",
update_banner:"Version {v} is available",update_link:"Download",winstart_label:"Start with Windows",
winstart_hint:"Opens quietly in the background when you sign in.",change_account:"Change account or restaurant",
forget:"Forget my data",forget_confirm:"Remove your matricule and password from this computer and stop automatic booking?",
quit:"Quit program",quit_confirm:"Quit? Automatic booking stops until you open the program again.",
quit_done:"The program is closed. You can close this tab.",
disclaimer:"Unofficial project — not affiliated with MESRS or ONOU. Use at your own risk.",
run_ok:"Done: {n} meal(s) booked",run_nothing:"Everything is already booked ✓",run_fail:"Some meals could not be booked",saved:"Saved ✓",
e_required:"Fill in both fields.",e_bad_credentials:"Wrong matricule or password.",
e_network:"Can't reach ONOU right now. Check your internet connection and try again.",
e_no_residence:"No housing request found for this academic year. This tool only works for students with a residence.",
e_server:"The server answered with an error. Try again later.",e_expired:"This step expired. Enter your password again.",
e_busy:"A booking is already running.",e_no_depots:"No restaurant found for your account.",e_config:"Configuration problem.",
e_default:"Something went wrong. Please try again.",e_local:"The program is not running anymore. Open it again.",
account:"Account",engine:"Settings"},
fr:{tagline:"Tes repas, réservés automatiquement.",setup_title:"Connecte ton compte Webetu",
setup_sub:"Saisis le même matricule et mot de passe que dans l'application Webetu. Une seule fois.",
username:"Matricule",password:"Mot de passe",show:"Afficher",hide:"Masquer",verify:"Vérifier et continuer",checking:"Vérification…",
privacy:"Ton mot de passe ne quitte cet ordinateur que pour te connecter à Webetu. Il est enregistré dans ton dossier utilisateur sur ce PC.",
step1:"Compte",step2:"Restaurant",pick_title:"Choisis ton restaurant",
pick_sub:"Un repas n'est valable que dans le restaurant où il a été réservé.",connected:"Connecté",residence:"Résidence",
back:"Retour",activate:"Enregistrer et activer",saving:"Enregistrement…",badge_ru:"Restaurant universitaire",
status_active:"La réservation automatique est active",status_paused:"La réservation automatique est en pause",status_attention:"Action requise",
status_starting:"Démarrage — première vérification bientôt",status_stale:"Aucune vérification réussie depuis {n} jours",status_engine:"Le moteur en arrière-plan est arrêté",
next_pass:"Passage quotidien vers {time}",last_check:"Dernière vérification",never:"jamais",today:"aujourd'hui",yesterday:"hier",days_ago:"il y a {n} jours",
booked_n:"{n} réservé(s)",book_now:"Réserver maintenant",booking:"Réservation…",refresh:"Actualiser",auto_label:"Réservation automatique",
auto_hint:"Réserve les 3 prochains jours pour toi, chaque jour.",days_title:"Tes 3 prochains jours",meal1:"Petit-déjeuner",meal2:"Déjeuner",meal3:"Dîner",
s_booked:"Réservé",s_missing:"Pas encore",s_not_served:"Non servi",loading_status:"Vérification de tes réservations…",
warn_stale:"Si cet ordinateur reste éteint plus de 3 jours, certains repas ne pourront plus être réservés. Allume-le chaque jour, ou utilise l'option GitHub toujours active.",
update_banner:"La version {v} est disponible",update_link:"Télécharger",winstart_label:"Démarrer avec Windows",
winstart_hint:"S'ouvre discrètement en arrière-plan à l'ouverture de session.",change_account:"Changer de compte ou de restaurant",
forget:"Oublier mes données",forget_confirm:"Supprimer ton matricule et ton mot de passe de cet ordinateur et arrêter la réservation automatique ?",
quit:"Quitter le programme",quit_confirm:"Quitter ? La réservation automatique s'arrête jusqu'à la prochaine ouverture.",
quit_done:"Le programme est fermé. Tu peux fermer cet onglet.",
disclaimer:"Projet non officiel — sans affiliation avec le MESRS ou l'ONOU. Utilisation à tes risques.",
run_ok:"Terminé : {n} repas réservé(s)",run_nothing:"Tout est déjà réservé ✓",run_fail:"Certains repas n'ont pas pu être réservés",saved:"Enregistré ✓",
e_required:"Remplis les deux champs.",e_bad_credentials:"Matricule ou mot de passe incorrect.",
e_network:"Impossible de joindre l'ONOU pour le moment. Vérifie ta connexion internet et réessaie.",
e_no_residence:"Aucune demande d'hébergement trouvée pour cette année universitaire. Cet outil ne fonctionne que pour les étudiants résidents.",
e_server:"Le serveur a répondu par une erreur. Réessaie plus tard.",e_expired:"Cette étape a expiré. Saisis à nouveau ton mot de passe.",
e_busy:"Une réservation est déjà en cours.",e_no_depots:"Aucun restaurant trouvé pour ton compte.",e_config:"Problème de configuration.",
e_default:"Une erreur est survenue. Réessaie.",e_local:"Le programme n'est plus lancé. Ouvre-le à nouveau.",
account:"Compte",engine:"Réglages"},
ar:{tagline:"وجباتك تُحجز تلقائيًا.",setup_title:"اربط حسابك في Webetu",
setup_sub:"أدخل نفس رقم التسجيل وكلمة المرور المستعملين في تطبيق Webetu. مرة واحدة فقط.",
username:"رقم التسجيل",password:"كلمة المرور",show:"إظهار",hide:"إخفاء",verify:"تحقق ثم تابع",checking:"جارٍ التحقق…",
privacy:"كلمة المرور لا تغادر هذا الحاسوب إلا لتسجيل الدخول إلى Webetu. وهي محفوظة في مجلد المستخدم على هذا الجهاز.",
step1:"الحساب",step2:"المطعم",pick_title:"اختر مطعمك",
pick_sub:"الوجبة صالحة فقط في المطعم الذي تم الحجز فيه.",connected:"تم الاتصال",residence:"الإقامة",
back:"رجوع",activate:"حفظ وتفعيل",saving:"جارٍ الحفظ…",badge_ru:"مطعم جامعي",
status_active:"الحجز التلقائي مفعّل",status_paused:"الحجز التلقائي متوقف مؤقتًا",status_attention:"يتطلب انتباهك",
status_starting:"جارٍ البدء — أول فحص قريبًا",status_stale:"لا يوجد فحص ناجح منذ {n} أيام",status_engine:"المحرّك الخلفي متوقف",
next_pass:"المرور اليومي حوالي {time}",last_check:"آخر فحص",never:"أبدًا",today:"اليوم",yesterday:"أمس",days_ago:"منذ {n} أيام",
booked_n:"تم حجز {n}",book_now:"احجز الآن",booking:"جارٍ الحجز…",refresh:"تحديث",auto_label:"الحجز التلقائي",
auto_hint:"يحجز لك الأيام الثلاثة القادمة كل يوم.",days_title:"أيامك الثلاثة القادمة",meal1:"فطور",meal2:"غداء",meal3:"عشاء",
s_booked:"محجوز",s_missing:"لم يُحجز بعد",s_not_served:"غير متوفر",loading_status:"جارٍ فحص حجوزاتك…",
warn_stale:"إذا بقي هذا الحاسوب مطفأً أكثر من 3 أيام فلن يمكن حجز بعض الوجبات. شغّله كل يوم، أو استعمل خيار GitHub الذي يعمل دائمًا.",
update_banner:"الإصدار {v} متوفر",update_link:"تحميل",winstart_label:"التشغيل مع ويندوز",
winstart_hint:"يعمل بهدوء في الخلفية عند تسجيل الدخول.",change_account:"تغيير الحساب أو المطعم",
forget:"حذف بياناتي",forget_confirm:"هل تريد حذف رقم التسجيل وكلمة المرور من هذا الحاسوب وإيقاف الحجز التلقائي؟",
quit:"إغلاق البرنامج",quit_confirm:"هل تريد الإغلاق؟ يتوقف الحجز التلقائي حتى تفتح البرنامج مجددًا.",
quit_done:"تم إغلاق البرنامج. يمكنك إغلاق هذه الصفحة.",
disclaimer:"مشروع غير رسمي — لا علاقة له بوزارة التعليم العالي أو الديوان الوطني للخدمات الجامعية. الاستعمال على مسؤوليتك.",
run_ok:"تم: حُجزت {n} وجبة",run_nothing:"كل شيء محجوز بالفعل ✓",run_fail:"تعذّر حجز بعض الوجبات",saved:"تم الحفظ ✓",
e_required:"املأ الحقلين.",e_bad_credentials:"رقم التسجيل أو كلمة المرور غير صحيحة.",
e_network:"تعذّر الاتصال بالموقع حاليًا. تحقق من الإنترنت وأعد المحاولة.",
e_no_residence:"لم يتم العثور على طلب إقامة لهذه السنة الجامعية. هذه الأداة تعمل فقط للطلبة المقيمين.",
e_server:"الخادم أرجع خطأ. أعد المحاولة لاحقًا.",e_expired:"انتهت صلاحية هذه الخطوة. أدخل كلمة المرور من جديد.",
e_busy:"هناك عملية حجز جارية بالفعل.",e_no_depots:"لم يتم العثور على أي مطعم لحسابك.",e_config:"مشكلة في الإعدادات.",
e_default:"حدث خطأ. أعد المحاولة.",e_local:"البرنامج لم يعد يعمل. افتحه من جديد.",
account:"الحساب",engine:"الإعدادات"}
};

const stored = (() => { try { return localStorage.getItem("lang"); } catch { return null; } })();
const guess = (navigator.language || "fr").slice(0, 2);
let lang = T[stored] ? stored : (T[guess] ? guess : "fr");
const t = (k, v = {}) => String(T[lang][k] ?? T.en[k] ?? k).replace(/\{(\w+)\}/g, (_, n) => v[n] ?? "");

const ICON = {
  check:'<path d="M20 6 9 17l-5-5"/>', minus:'<path d="M5 12h14"/>',
  eye:'<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>',
  eyeoff:'<path d="M9.9 4.24A9.1 9.1 0 0 1 12 5c6.5 0 10 7 10 7a17 17 0 0 1-2.2 3.2"/><path d="M6.6 6.6A16.5 16.5 0 0 0 2 12s3.5 7 10 7a9.7 9.7 0 0 0 5.4-1.6"/><path d="m2 2 20 20"/><path d="M9.9 9.9a3 3 0 0 0 4.2 4.2"/>',
  refresh:'<path d="M21 12a9 9 0 0 0-15-6.7L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 15 6.7L21 16"/><path d="M16 16h5v5"/>',
  shield:'<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/>',
  alert:'<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
  download:'<path d="M12 15V3"/><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m7 10 5 5 5-5"/>',
  m1:'<path d="M10 2v2"/><path d="M14 2v2"/><path d="M16 8a1 1 0 0 1 1 1v8a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4V9a1 1 0 0 1 1-1h14a4 4 0 1 1 0 8h-1"/><path d="M6 2v2"/>',
  m2:'<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/>',
  m3:'<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/>'
};
const ic = (n) => '<svg class="i" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + ICON[n] + "</svg>";

const S = {
  view: "loading", st: null, status: null, statusErr: null, statusBusy: false,
  setup: { step: 1, username: "", password: "", show: false, error: null, busy: false, verified: null, choice: null },
  wasBusy: false, closed: false, lastKey: "", screen: ""
};

async function api(path, body) {
  const opts = body === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json", "X-CSRF-Token": CSRF }, body: JSON.stringify(body) };
  let res;
  try { res = await fetch(path, opts); } catch { throw { code: "local" }; }
  let json;
  try { json = await res.json(); } catch { throw { code: "default" }; }
  if (!json.ok) throw json.error || { code: "default" };
  return json.data;
}
const errText = (e) => t("e_" + (e && e.code), {}) === "e_" + (e && e.code) ? t("e_default") : t("e_" + e.code);

function toast(msg) {
  const box = $("#toast");
  box.innerHTML = "<div>" + esc(msg) + "</div>";
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { box.innerHTML = ""; }, 3800);
}

function applyLang() {
  document.documentElement.lang = lang;
  document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
  $("#tagline").textContent = t("tagline");
  $("#foot").textContent = t("disclaimer") + (S.st && S.st.version ? "  ·  v" + S.st.version : "");
  document.querySelectorAll("[data-lang]").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.lang === lang)));
}

function fmtDay(iso) {
  const d = new Date(iso + "T12:00:00");
  const loc = lang === "ar" ? "ar-DZ" : lang;
  return { wd: d.toLocaleDateString(loc, { weekday: "long" }), dt: d.toLocaleDateString(loc, { day: "numeric", month: "long" }) };
}
function ago(days) {
  if (days === null || days === undefined) return t("never");
  if (days <= 0) return t("today");
  if (days === 1) return t("yesterday");
  return t("days_ago", { n: days });
}

/* ---------------------------------------------------------------- views */
function viewLoading() { return '<div class="card"><div class="skel" style="width:60%"></div><div class="skel"></div><div class="skel" style="width:80%"></div></div>'; }

function stepper(n) {
  return '<div class="stepper"><span class="' + (n === 1 ? "on" : "") + '"><i>1</i></span><span class="' + (n === 1 ? "on" : "") + '">' + t("step1") +
    '</span><hr><span class="' + (n === 2 ? "on" : "") + '"><i>2</i></span><span class="' + (n === 2 ? "on" : "") + '">' + t("step2") + "</span></div>";
}
function alertBox(kind, text) {
  return '<div class="alert ' + kind + '" role="alert">' + ic("alert") + "<div>" + esc(text) + "</div></div>";
}

function viewSetup1() {
  const s = S.setup;
  return '<form class="card" id="f1" autocomplete="on" novalidate>' + stepper(1) +
    "<h1>" + t("setup_title") + '</h1><p class="sub">' + t("setup_sub") + "</p>" +
    '<label for="u">' + t("username") + '</label><div class="field"><input id="u" name="username" type="text" inputmode="numeric" autocomplete="username" value="' + esc(s.username) + '" autofocus></div>' +
    '<label for="p">' + t("password") + '</label><div class="field"><input class="has-eye" id="p" name="password" autocomplete="current-password" type="' + (s.show ? "text" : "password") + '" value="' + esc(s.password) + '">' +
    '<button type="button" class="eye" data-act="eye" aria-label="' + (s.show ? t("hide") : t("show")) + '">' + ic(s.show ? "eyeoff" : "eye") + "</button></div>" +
    (s.error ? alertBox("bad", s.error) : "") +
    '<button class="btn primary block" type="submit"' + (s.busy ? " disabled" : "") + ">" + (s.busy ? '<span class="spin"></span>' + t("checking") : t("verify")) + "</button>" +
    '<div class="note">' + ic("shield") + "<span>" + t("privacy") + "</span></div></form>";
}

function viewSetup2() {
  const s = S.setup, v = s.verified;
  const opts = v.depots.map((d) => {
    const meals = [1, 2, 3].filter((m) => d.meals[m - 1]).map((m) => '<span class="chip">' + t("meal" + m) + "</span>").join("");
    return '<label class="opt ' + (s.choice === d.id ? "sel" : "") + '"><input type="radio" name="depot" value="' + d.id + '"' + (s.choice === d.id ? " checked" : "") + ">" +
      '<div><div class="nm">' + esc(d.name) + '</div><div class="chips"><span class="chip">#' + d.id + "</span>" + (d.is_ru ? '<span class="chip ru">' + t("badge_ru") + "</span>" : "") + meals + "</div></div></label>";
  }).join("");
  return '<form class="card" id="f2" novalidate>' + stepper(2) + "<h1>" + t("pick_title") + '</h1><p class="sub">' + t("pick_sub") + "</p>" +
    '<div class="chips" style="margin:-6px 0 14px"><span class="chip ru">' + t("connected") + "</span>" +
    (v.residence ? '<span class="chip">' + t("residence") + ": " + esc(v.residence) + "</span>" : "") + "</div>" +
    '<div class="opts">' + opts + "</div>" + (s.error ? alertBox("bad", s.error) : "") +
    '<div class="row" style="margin-top:20px"><button type="button" class="btn ghost" data-act="back">' + t("back") + "</button>" +
    '<button class="btn primary" style="flex:1" type="submit"' + (s.busy || s.choice === null ? " disabled" : "") + ">" +
    (s.busy ? '<span class="spin"></span>' + t("saving") : t("activate")) + "</button></div></form>";
}

function health() {
  const st = S.st;
  if (!st.auto) return { kind: "warn", text: t("status_paused") };
  if (!st.daemon_running) return { kind: "bad", text: t("status_engine") };
  const failed = st.last_run && st.last_run.status === "failed";
  if (failed || (st.manual && st.manual.error)) return { kind: "bad", text: t("status_attention") };
  if (st.days_since_last_run === null) return { kind: "info", text: t("status_starting") };
  if (st.days_since_last_run >= 3) return { kind: "warn", text: t("status_stale", { n: st.days_since_last_run }) };
  return { kind: "ok", text: t("status_active") };
}

function lastLine() {
  const st = S.st, lr = st.last_run;
  let txt = t("last_check") + ": " + ago(st.days_since_last_run);
  if (lr && lr.at) {
    const d = new Date(lr.at);
    if (!isNaN(d)) txt += " · " + d.toLocaleTimeString(lang === "ar" ? "ar-DZ" : lang, { hour: "2-digit", minute: "2-digit" });
  }
  if (lr) txt += " · " + t("booked_n", { n: lr.booked });
  return txt;
}

function viewDashboard() {
  const st = S.st, h = health();
  let html = "";
  if (st.update) html += '<div class="alert info" style="margin:0 0 16px">' + ic("download") + "<div>" + esc(t("update_banner", { v: st.update.version })) +
    ' — <a href="' + esc(st.update.url) + '" target="_blank" rel="noopener noreferrer">' + t("update_link") + "</a></div></div>";
  if (st.manual && st.manual.error) html += alertBox("bad", st.manual.message && st.manual.error === "unknown" ? st.manual.message : errText({ code: st.manual.error }));
  else if (st.days_since_last_run !== null && st.days_since_last_run >= 3) html += '<div class="alert warn" style="margin:0 0 16px">' + ic("alert") + "<div>" + t("warn_stale") + "</div></div>";

  html += '<section class="card"><div class="row spread"><span class="pill ' + h.kind + '"><span class="dot"></span>' + esc(h.text) + "</span>" +
    '<span class="chip">' + esc(st.username) + "</span></div>" +
    '<p class="meta">' + t("next_pass", { time: esc(st.run_at) }) + "<br>" + esc(lastLine()) + "</p>" +
    '<div class="row" style="margin-top:16px"><button class="btn primary" data-act="run"' + (st.busy ? " disabled" : "") + ">" +
    (st.busy ? '<span class="spin"></span>' + t("booking") : t("book_now")) + '</button><button class="btn" data-act="refresh"' + (S.statusBusy ? " disabled" : "") + ">" + ic("refresh") + t("refresh") + "</button></div>" +
    '<div class="sw-row" style="margin-top:14px"><div class="tx"><b>' + t("auto_label") + "</b><span>" + t("auto_hint") + '</span></div><button class="sw" role="switch" data-act="auto" aria-checked="' + st.auto + '" aria-label="' + t("auto_label") + '"></button></div></section>';

  html += '<section class="card"><h2>' + t("days_title") + "</h2>";
  if (S.statusBusy && !S.status) html += '<div class="skel"></div><div class="skel" style="width:85%"></div><div class="skel" style="width:70%"></div>';
  else if (S.statusErr) html += alertBox("bad", S.statusErr);
  else if (S.status) {
    const x = S.status, meals = x.days.length ? x.days[0].meals.map((m) => m.type) : [];
    html += '<table class="grid"><thead><tr><th></th>' + meals.map((m) => '<th><span class="mealhead">' + ic("m" + m) + t("meal" + m) + "</span></th>").join("") + "</tr></thead><tbody>" +
      x.days.map((d) => {
        const f = fmtDay(d.date);
        return '<tr><td class="day">' + esc(f.wd) + "<small>" + esc(f.dt) + "</small></td>" + d.meals.map((c) =>
          '<td><span class="cell ' + c.state + '">' + (c.state === "booked" ? ic("check") : c.state === "missing" ? ic("minus") : "") + "<span>" + t("s_" + c.state) + "</span></span></td>").join("") + "</tr>";
      }).join("") + "</tbody></table>" +
      '<p class="meta">' + esc(x.resto) + (x.residence ? " · " + esc(x.residence) : "") + "</p>";
  }
  html += "</section>";

  html += '<section class="card"><h2>' + t("engine") + "</h2>";
  if (st.autostart && st.autostart.supported) html += '<div class="sw-row"><div class="tx"><b>' + t("winstart_label") + "</b><span>" + t("winstart_hint") +
    '</span></div><button class="sw" role="switch" data-act="autostart" aria-checked="' + st.autostart.enabled + '" aria-label="' + t("winstart_label") + '"></button></div>';
  html += '<div class="row" style="margin-top:12px"><button class="btn" data-act="change">' + t("change_account") + '</button><button class="btn danger" data-act="forget">' + t("forget") +
    '</button><button class="btn ghost" data-act="quit">' + t("quit") + "</button></div></section>";
  return html;
}

function viewClosed() { return '<div class="card center"><h1>✓</h1><p class="sub">' + t("quit_done") + "</p></div>"; }

function render() {
  applyLang();
  const app = $("#app");
  if (S.closed) app.innerHTML = viewClosed();
  else if (S.view === "loading") app.innerHTML = viewLoading();
  else if (S.view === "setup") app.innerHTML = S.setup.step === 1 || !S.setup.verified ? viewSetup1() : viewSetup2();
  else app.innerHTML = viewDashboard();
  const screen = S.closed ? "closed" : S.view === "setup" ? "setup" + (S.setup.step === 1 || !S.setup.verified ? 1 : 2) : S.view;
  if (screen !== S.screen) {
    S.screen = screen;
    app.querySelectorAll(".card").forEach((c) => c.classList.add("enter"));
  }
}

/* -------------------------------------------------------------- actions */
async function loadState(initial) {
  try {
    const next = await api("/api/state");
    const key = JSON.stringify(next);
    const wasBusy = S.st && S.st.busy;
    S.st = next;
    if (initial) S.view = next.configured ? "dash" : "setup";
    if (wasBusy && !next.busy && next.manual) {
      const m = next.manual;
      toast(m.error ? errText({ code: m.error }) : m.failed ? t("run_fail") : m.booked ? t("run_ok", { n: m.booked }) : t("run_nothing"));
      loadStatus();
    }
    if (initial || key !== S.lastKey) { S.lastKey = key; if (!(S.view === "setup")) render(); else if (initial) render(); }
    if (initial && next.configured) loadStatus();
  } catch (e) {
    if (e && e.code === "local" && !S.closed) { S.view = "dash"; S.statusErr = t("e_local"); }
  }
}

async function loadStatus() {
  if (S.statusBusy) return;
  S.statusBusy = true; S.statusErr = null; if (S.view === "dash") render();
  try { S.status = await api("/api/status"); } catch (e) { S.statusErr = errText(e); }
  S.statusBusy = false; if (S.view === "dash") render();
}

async function doVerify() {
  const s = S.setup;
  if (!s.username.trim() || !s.password) { s.error = t("e_required"); return render(); }
  s.busy = true; s.error = null; render();
  try {
    s.verified = await api("/api/verify", { username: s.username.trim(), password: s.password });
    s.choice = s.verified.suggested_id !== null ? s.verified.suggested_id : (s.verified.depots.length === 1 ? s.verified.depots[0].id : null);
    s.step = 2; s.password = "";
  } catch (e) { s.error = errText(e); }
  s.busy = false; render();
}

async function doSave() {
  const s = S.setup;
  s.busy = true; s.error = null; render();
  try {
    S.st = await api("/api/save", { resto_id: s.choice });
    S.setup = { step: 1, username: "", password: "", show: false, error: null, busy: false, verified: null, choice: null };
    S.view = "dash"; S.status = null; render(); toast(t("saved")); loadStatus();
  } catch (e) {
    s.busy = false; s.error = errText(e);
    if (e && e.code === "expired") { s.step = 1; s.verified = null; }
    render();
  }
}

async function act(name) {
  try {
    if (name === "eye") { S.setup.show = !S.setup.show; return render(); }
    if (name === "back") { S.setup.step = 1; S.setup.error = null; return render(); }
    if (name === "refresh") return loadStatus();
    if (name === "run") { S.st.busy = true; render(); await api("/api/run", {}); return setTimeout(() => loadState(false), 600); }
    if (name === "auto") { S.st = await api("/api/auto", { enabled: !S.st.auto }); return render(); }
    if (name === "autostart") { S.st = await api("/api/autostart", { enabled: !S.st.autostart.enabled }); return render(); }
    if (name === "change") { S.view = "setup"; S.setup.step = 1; S.setup.username = S.st.username || ""; S.setup.verified = null; return render(); }
    if (name === "forget") {
      if (!confirm(t("forget_confirm"))) return;
      S.st = await api("/api/forget", {}); S.status = null; S.view = "setup"; S.setup.step = 1; S.setup.username = ""; return render();
    }
    if (name === "quit") {
      if (!confirm(t("quit_confirm"))) return;
      await api("/api/quit", {}); S.closed = true; return render();
    }
  } catch (e) {
    if (S.st) S.st.busy = false;
    toast(errText(e)); render();
  }
}

/* ---------------------------------------------------------------- wiring */
document.addEventListener("click", (ev) => {
  const lb = ev.target.closest("[data-lang]");
  if (lb) { lang = lb.dataset.lang; try { localStorage.setItem("lang", lang); } catch {} return render(); }
  const el = ev.target.closest("[data-act]");
  if (el) act(el.dataset.act);
});
document.addEventListener("input", (ev) => {
  if (ev.target.id === "u") S.setup.username = ev.target.value;
  if (ev.target.id === "p") S.setup.password = ev.target.value;
});
document.addEventListener("change", (ev) => {
  if (ev.target.name === "depot") { S.setup.choice = Number(ev.target.value); render(); }
});
document.addEventListener("submit", (ev) => {
  ev.preventDefault();
  if (ev.target.id === "f1") doVerify();
  if (ev.target.id === "f2" && S.setup.choice !== null) doSave();
});

render();
loadState(true);
setInterval(() => { if (!S.closed) loadState(false); }, 4000);
})();
</script>
</body>
</html>
"""
