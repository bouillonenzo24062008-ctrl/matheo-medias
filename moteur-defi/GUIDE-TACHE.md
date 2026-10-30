# Tâche du dimanche : fabriquer les défis de la semaine, puis tout programmer après le « OK » d'Enzo

Ce guide est lu par la tâche programmée chaque dimanche. Il décrit tout, du choix des défis à la programmation.
Enzo (Mathéo, appli web de spé maths Terminale, compte « avecmatheo.fr ») valide TOUJOURS avant publication.
Réponds-lui en français, directement, sans le flatter. Fais court : le quota Claude d'Enzo est limité.

## Règles qui ne bougent jamais

- Maths justes, au niveau du programme de Terminale spé maths. `fabriquer.py` refuse un calcul faux, mais
  chaque étape doit aussi être équivalente à la précédente : relis-les une par une.
- Ne promets ni note ni réussite au bac (« sécurise ta note », « réussis ton bac » : interdit).
- N'invente ni fonctionnalité, ni chiffre, ni témoignage. « Coach IA » et « Préparation au Bac » ne sont pas
  encore disponibles : n'en parle pas. N'écris pas le prix de Mathéo Plus.
- Aucune formule écrite comme du code dans les vidéos (le moteur les compose comme en LaTeX).
- Jamais de suppression, jamais de publication sans le « OK » d'Enzo dans cette conversation.

## 1. Préparer (une fois par tâche)

1. `add_repo` (outil Claude Code Remote) : owner `bouillonenzo24062008-ctrl`, repo `matheo-medias`, access `push`,
   puis clone-le comme indiqué et passe dans `matheo-medias/moteur-defi`.
2. Vérifie les outils : `python3 -c "import numpy, scipy, matplotlib, PIL, playwright"` et `which ffmpeg`.
   S'il manque un paquet : `pip install <paquet> --break-system-packages`.

## 2. Choisir 3 défis

- Lis `defis/` : ne refais jamais un défi déjà présent (même équation ou même idée).
- Varie les chapitres d'une semaine à l'autre : exponentielle, logarithme, limites, dérivation et convexité,
  suites (récurrence, limites), primitives et intégrales, équations différentielles y' = ay + b,
  probabilités conditionnelles et loi binomiale, géométrie dans l'espace (produit scalaire, plans).
  Si le bilan du dimanche (autre tâche) a montré qu'un chapitre marche mieux, privilégie-le.
- Un bon défi se résout de tête en 10 secondes par un élève qui connaît l'astuce, et piège ceux qui ne la
  connaissent pas. Idéalement une solution à écarter (barre + note), comme « X = −1 impossible car eˣ > 0 ».
- 4 à 6 étapes, la dernière est la réponse. Formules COURTES : une ligne, pas plus large qu'environ 700 px sur
  la planche `--glyphes` (au-delà, elles deviennent petites à l'écran).

## 3. Fabriquer chaque défi

Exemples complets : `defis/exponentielle.json` (avec encadrés, barre, note et étiquettes) et `defis/ln-somme.json`
(barre et note seulement). La description de chaque champ est en tête de `fabriquer.py`.

1. Écris `defis/<nom-court>.json` avec les formules et `"cles": []` pour l'instant, et la `verification`.
2. `python3 fabriquer.py defis/<nom>.json --glyphes` puis regarde `out/glyphes.png` (outil Read) : chaque glyphe a
   un numéro. Donne une clé à chacun, dans cet ordre ; même clé d'une étape à l'autre = le même terme qui glisse.
   Un terme qui disparaît ou apparaît prend une clé qu'on ne retrouve pas à l'étape voisine.
3. `python3 fabriquer.py defis/<nom>.json --apercu` puis regarde `out/apercu.png`. Corrige ce qui est coupé,
   trop petit ou illisible.
4. `python3 fabriquer.py defis/<nom>.json` (3 à 4 minutes) : vérifie dans la sortie `RÉSULTAT : OK`, aucune ligne
   « JAMAIS LISIBLE », une vidéo de moins de 20 Mo. Regarde `out/<nom>-couverture.jpg`.

## 4. Mettre en ligne et proposer à Enzo

1. Copie `out/<nom>.mp4` dans `../videos/defi-<nom>.mp4` et la couverture dans `../couvertures/defi-<nom>.jpg`.
   Commit (le fichier du défi aussi) et push sur `main`. GitHub Pages met en ligne en 1 à 2 minutes :
   `https://bouillonenzo24062008-ctrl.github.io/matheo-medias/videos/defi-<nom>.mp4`
2. Écris une description par défi (skill ig-caption puis ig-human s'ils sont disponibles), sur ce modèle :

   ```
   Tu as trouvé avant la réponse ? Dis-le en commentaire 👇

   <l'énoncé en une ligne> : l'astuce, c'est <l'astuce>. Et le piège, c'est <le piège>.

   Un exercice type de spé maths Terminale sur <chapitre>, comme ceux de Mathéo : cours, exos corrigés et méthode pas à pas, lien en bio.

   #spemaths #terminale #<un hashtag du chapitre>
   ```
   Pas de tiret long (—), au plus 3 hashtags, écriture des formules en texte simple (e^x, ln 2, x²).
3. Propose les dates : lundi, mercredi et vendredi qui suivent, à 18 h (heure de Paris).
4. Envoie à Enzo, puis ARRÊTE-TOI et attends sa réponse :

   **Défis de la semaine** : 3 vidéos prêtes
   1. <titre> (lundi 18 h) : <lien github.io>
      Description : « ... »
   2. ...
   Réponds OK pour tout programmer, OK 1 3 pour en choisir, ou dis ce qu'il faut corriger.

   S'il demande une correction : refais l'étape 3 pour ce défi, remets en ligne, renvoie le lien.

## 5. Après le « OK » d'Enzo : programmer chaque défi validé

Heure de publication : 18 h à Paris = 17:00 UTC (en hiver, après le dernier dimanche d'octobre) ou 16:00 UTC (en
été). Horodatage Unix : `python3 -c "import datetime as d;print(int(d.datetime(2026,11,2,17,tzinfo=d.timezone.utc).timestamp()))"`.

**Facebook** (programmé directement dans Facebook, rien ne peut sauter) : outil Porter `execute_action`,
action `facebook_insights.video_upload`, account_id
`DTn8t_QMOCt6PQYDubTr2g.facebook-insights~1433339929852423~facebook-insights-bouillonenzo24062008@gmail.com~d133cabe-6726-47d8-a05d-cdeeba3eb78b~Mathéo l Spé maths Terminale. (1433339929852423)`,
params : `page_id` « 1433339929852423 », `file_url` (lien github.io de la vidéo), `title` « Tu saurais résoudre ça ? »,
`description` (la description, avec « sur avecmatheo.fr » à la place de « lien en bio »), `published` false,
`scheduled_publish_time` (horodatage). N'envoie PAS `thumb` (Facebook le refuse).

**TikTok** (en brouillon : Enzo ajoute le son et publie) :
1. Porter `execute_action`, action `creative.rehost_media`, params `url` (lien github.io), `kind` « video » :
   garde `asset_url`.
2. Porter `execute_action`, action `tiktok_insights.video_publish`, account_id
   `LtQfJ-sEjN2FRmiSfTkW7w.tiktok-insights~-000hdr1RgpKhRc7DJDvfiJuuiGRzkHekzHk~tiktok-insights-Mathéo — Maths Terminale~d133cabe-6726-47d8-a05d-cdeeba3eb78b~Mathéo — Maths Terminale`,
   params `video_url` (asset_url), `upload_to_draft` true, `is_brand_organic` true, `is_branded_content` false.
   Une seule fois par vidéo : ne renvoie jamais un brouillon « en cours de traitement » (ça ferait un doublon).
   Les brouillons arrivent dans la boîte de réception TikTok d'Enzo (jusqu'à 30 min).

**Instagram** (pas de programmation possible par l'API) : pour chaque date, crée une tâche ponctuelle
(`create_trigger`, `run_once_at` = la date à 17:00:00Z en hiver, notifications push) avec ce texte, à compléter :

   > Tu publies, à la demande d'Enzo, un Reel sur son compte Instagram « avecmatheo.fr ». Sois bref : peu d'appels
   > d'outils. 0. Vérifie d'abord avec Windsor.ai get_data (connecteur « instagram », compte 17841422466687110,
   > champs date, media_id, media_permalink, media_caption, depuis la veille, sans force_refresh) qu'une
   > publication de même description n'existe pas déjà ; si elle existe, envoie son lien et arrête-toi.
   > 1. Windsor.ai execute_action, connecteur « instagram », compte 17841422466687110, action create_video_post :
   > video_url <lien>, cover_url <lien de la couverture>, share_to_feed true, caption (à copier exactement) : <…>.
   > 2. En cas d'échec, réessaie UNE fois après 2 minutes, puis envoie à Enzo l'erreur exacte et « Publie-le à la
   > main depuis l'appli : vidéo <lien>, description ci-dessus ». 3. Si c'est publié, publie la même vidéo en story
   > (action create_story, video_url) et envoie à Enzo : « <titre> est en ligne sur Instagram (story aussi).
   > Publie le brouillon TikTok maintenant. »

**Notion** : dans la base « Vidéos pub Mathéo » (source collection://35b35071-3c51-435e-84b9-431954030453),
crée une page par défi : Vidéo = « Défi <titre> », Statut « Prête », date de sortie, et dans le contenu le lien de
la vidéo, de la couverture et la description.

Termine par une ligne à Enzo : ce qui est programmé où et quand, et « Les brouillons TikTok sont dans ta boîte de
réception : ajoute le son et publie-les le jour prévu à 18 h. »
