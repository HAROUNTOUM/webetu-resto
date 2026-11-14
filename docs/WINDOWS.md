# Programme Windows (`webetu-resto.exe`)

Pour les étudiants qui ne veulent ni Python, ni Docker, ni terminal.

## Installer

1. Ouvre la page **Releases** du projet et télécharge `webetu-resto.exe`.
2. Double-clique dessus.
3. Windows peut afficher « Windows a protégé votre PC » (le programme n'est pas signé
   numériquement, ce qui coûte cher). Clique sur **Informations complémentaires**, puis
   **Exécuter quand même**.
4. Ton navigateur s'ouvre sur une page locale. Saisis ton **matricule** et ton **mot de
   passe**, choisis ton restaurant, clique sur **Enregistrer et activer**. C'est fini.
5. Dans « Réglages », active **Démarrer avec Windows** : le programme se lancera tout seul,
   sans fenêtre, à chaque ouverture de session.

Optionnel : compare l'empreinte du fichier avec `webetu-resto.exe.sha256` (PowerShell :
`Get-FileHash .\webetu-resto.exe -Algorithm SHA256`).

## Au quotidien

- Rien à faire : tant que l'ordinateur est allumé, le programme réserve chaque jour les
  3 prochains jours (petit-déjeuner, déjeuner, dîner).
- Pour voir l'état ou changer quelque chose, double-clique à nouveau sur le programme : la
  page s'ouvre (il ne se lance pas deux fois).
- **Si l'ordinateur reste éteint plus de 3 jours**, les repas de ces jours ne peuvent plus être
  réservés (règle du serveur : 24 h à l'avance). Pour ne jamais rien rater, utilise aussi
  l'option GitHub Actions de [`SELF-HOSTING.md`](SELF-HOSTING.md) (option D).

## Où sont mes données ?

Dans `%APPDATA%\webetu-resto` (colle ce chemin dans l'explorateur de fichiers) :
`.env` (matricule et mot de passe), `state.json` (historique) et `webetu-resto.log`.
Le bouton **Oublier mes données** de la page supprime l'identifiant, l'historique et le
démarrage automatique.

## Mettre à jour

Quand une nouvelle version existe, la page affiche un bandeau « Télécharger ». Remplace
simplement l'ancien `.exe` par le nouveau (ta configuration est conservée).

## Désinstaller

1. Dans la page : **Oublier mes données**, puis **Quitter le programme**.
2. Supprime `webetu-resto.exe` et le dossier `%APPDATA%\webetu-resto`.

## Problèmes fréquents

| Problème | Solution |
|---|---|
| L'antivirus bloque le fichier | Le programme n'est pas signé. Ajoute une exception, ou installe depuis le code source (README). |
| « Aucune demande d'hébergement trouvée » | L'outil ne fonctionne que pour les étudiants qui ont une demande d'hébergement cette année. |
| « Impossible de joindre l'ONOU » | Vérifie ta connexion internet, puis clique sur **Actualiser**. |
| Mot de passe changé sur Webetu | Clique sur **Changer de compte ou de restaurant** et saisis le nouveau. |
| La page ne s'ouvre pas | Double-clique sur le programme, ou ouvre <http://127.0.0.1:8765/>. |

## بالعربية (ملخّص)

1. نزّل `webetu-resto.exe` من صفحة **Releases** ثم شغّله بنقرتين.
2. إذا ظهرت رسالة حماية ويندوز: **مزيد من المعلومات** ثم **تشغيل على أي حال**.
3. أدخل رقم التسجيل وكلمة المرور، اختر المطعم، ثم **حفظ وتفعيل**.
4. فعّل **التشغيل مع ويندوز** حتى يعمل تلقائيًا.
5. إذا بقي الحاسوب مطفأً أكثر من 3 أيام فلن يمكن حجز وجبات تلك الأيام.
