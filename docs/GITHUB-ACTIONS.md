# Réservation sans ordinateur allumé (GitHub Actions)

GitHub fait le passage quotidien à ta place, sur ses serveurs, **gratuitement**. Ton
ordinateur peut rester éteint. Compte environ 10 minutes, une seule fois.

> ⚠️ Utilise un dépôt **privé** : les journaux d'un dépôt public sont visibles par tout le
> monde. Tes identifiants, eux, restent dans les « secrets » GitHub (jamais affichés).

## Étapes

1. Crée un compte gratuit sur <https://github.com> (ou connecte-toi).
2. Ouvre <https://github.com/new/import>.
3. Dans **Your old repository's clone URL**, colle l'adresse de ce projet (celle de la page
   où tu lis ce guide). Dans **Owner** choisis ton nom, dans **Name** écris `mes-repas`,
   choisis **Private**, puis clique sur **Begin import** et attends la fin.
4. Ouvre ton dépôt `mes-repas` → **Settings** → **Secrets and variables** → **Actions**
   → **New repository secret**. Crée ces secrets, un par un :

   | Name | Secret |
   |---|---|
   | `WEBETU_USERNAME` | ton matricule |
   | `WEBETU_PASSWORD` | ton mot de passe Webetu |
   | `WEBETU_RESTO_ID` | *(facultatif)* le numéro de ton restaurant, affiché `#68` dans le programme Windows ou `webtu setup`. À remplir seulement si tu as plusieurs restaurants. |

5. Onglet **Actions** → clique sur **I understand my workflows, go ahead and enable them**.
6. À gauche, choisis **Daily reservation** → **Run workflow** → coche **Simulate only** →
   **Run workflow**. Attends la coche verte ✅ (environ 1 minute). Ouvre l'exécution pour
   lire le résultat.
7. Relance **Run workflow** sans cocher la simulation : tes 3 prochains jours sont réservés.

C'est terminé. GitHub relance le passage chaque jour vers 00:05 (heure d'Alger) et à
nouveau le matin pour combler les trous, avec un petit délai aléatoire.

## Bon à savoir

- Si un passage échoue, GitHub t'envoie un e-mail.
- Mot de passe changé sur Webetu : mets à jour le secret `WEBETU_PASSWORD`.
- Pour arrêter : onglet **Actions** → **Daily reservation** → menu **⋯** → **Disable
  workflow**, ou supprime le dépôt.
- Tu peux combiner ce mode avec le programme Windows : le passage est idempotent (il ne
  réserve jamais deux fois le même repas).

## بالعربية (ملخّص)

1. أنشئ حسابًا مجانيًا في GitHub.
2. افتح <https://github.com/new/import> والصق رابط هذا المشروع، اختر **Private** ثم **Begin import**.
3. في مستودعك: **Settings ← Secrets and variables ← Actions ← New repository secret** وأنشئ:
   `WEBETU_USERNAME` (رقم التسجيل) و`WEBETU_PASSWORD` (كلمة المرور)، واختياريًا `WEBETU_RESTO_ID`.
4. من تبويب **Actions** فعّل الـ workflows، ثم **Daily reservation ← Run workflow**.
5. بعدها يعمل الحجز تلقائيًا كل يوم حوالي منتصف الليل بتوقيت الجزائر، حتى لو كان حاسوبك مطفأً.
