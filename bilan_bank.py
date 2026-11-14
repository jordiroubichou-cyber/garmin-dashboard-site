"""Bibliothèque de phrases du paragraphe « Le mot du coach » (section Analyse du jour).

Principe : le paragraphe est assemblé à partir de blocs (salutation, accroche, blague, transitions…), chaque bloc étant choisi dans une banque selon le scénario :
  1. OPENER   : accroche selon la note /20 de la période (6 niveaux)
  2. PILIERS  : meilleur pilier (STRONG) + pilier le plus faible (WEAK), ou BALANCED si les 5 piliers sont proches
  3. GOAL     : où en est la prédiction vs l'objectif de course (5 cas)
  4. STATE    : état de forme du moment (9 profils) + un modificateur (dette de sommeil, VFC, stress…)
  5. CLOSER   : conclusion / conseil selon performance (3 niveaux) x état (3 niveaux) = 9 cas
  6. TAIL     : tendance vs période précédente OU compte à rebours de la prochaine course
Sélection 100 % déterministe (md5 de la date + sel), sans IA ni appel externe : même date + mêmes données = même texte.
Une variante qui référence une variable absente (donnée manquante) est écartée automatiquement.

Règles de ton : humour, tutoiement, surnoms ; piques et insultes rigolotes UNIQUEMENT quand l'entraînement est insuffisant
ou que la note est basse ; jamais d'insulte quand l'état physique est mauvais (fatigue, surcharge) : là, on te gronde
gentiment pour t'inciter à lever le pied. Pour ajouter des phrases : complète simplement les listes ci-dessous
(variables autorisées par banque : voir ALLOWED en bas du fichier ; le test_analysis.py vérifie tout)."""
import hashlib
import re
import string
from datetime import date

import redondance as R

NAME = "Jordi"

# ---------------------------------------------------------------------------------------------
# SURNOMS ET INSULTES
# ---------------------------------------------------------------------------------------------
NICK = ["champion", "le sang", "poulet", "la machine", "le patron", "monstre", "grand", "coach", "l'artiste", "le boss",
        "mon lapin", "la légende", "bonhomme", "mon grand", "le fauve", "Forrest", "l'athlète", "mon poulet", "chef", "le S",
        "Kipchoge du dimanche", "Jordi la fusée", "le tigre", "mon gars sûr", "Superman", "le roi de la foulée", "ma gazelle",
        "le phénomène", "mon pote", "l'ours", "Usain Jordi", "le métronome", "gros", "la bête", "l'ami", "le crack", "maestro", "le Z", "mon petit poulet", "grand fou", "Eliud Jordi", "la gazelle de Biarritz",
        "poulet rôti", "le chacal", "monsieur Marathon", "le tank", "mon lion", "Rocky", "la flèche", "le dieu du bitume", "mon vieux", "le colosse", "Jordi-la-foulée", "monsieur le président", "le magicien", "mon brave", "le patron du bitume", "la locomotive", "le renard", "ma panthère",
        "le Mozart du semi", "mon héros", "Capitaine Foulée", "le roi du dimanche", "l'étalon", "mon petit marathonien", "le seigneur des sentiers", "grand champion", "le titan", "monsieur Fartlek", "le lièvre", "l'écureuil turbo", "le sage", "mon cher", "le maître", "le guépard", "chef de meute", "le moteur"]
INS = ["gros tas", "flemmard", "tas de graisse", "limace", "marmotte", "patate de canapé", "feignasse", "mollusque", "pantoufle",
       "gros sac", "escargot", "moule", "grosse larve", "paresseux", "bulot", "grosse loutre", "sac à patates", "tortue de salon",
       "gros dormeur", "champion du canapé", "athlète de zapping", "ours en hibernation", "boule de graisse", "vieille pantoufle", "gros lard", "gros bébé", "grosse marmotte", "gros nounours", "limace en short", "sac de sable", "gros cochon de canapé", "tas de mollesse", "gros paresseux", "boudin de canapé", "momie de salon", "Mister Sieste", "grosse flemme", "pot de colle du fauteuil", "gros ramollo", "mou du genou", "limace de compétition", "champion du pyjama", "hibernateur professionnel", "gros loir"]

WIN = {"1S": "cette semaine", "1M": "ce mois-ci", "3M": "ces 3 derniers mois"}

# ---------------------------------------------------------------------------------------------
# 1. OPENER : par niveau de note /20 de la période
# Variables : {nick} {ins} {name} {score} {win}
# ---------------------------------------------------------------------------------------------
OPENER = {
    "tres_bas": [
        "{nick}, {score}/20 {win}… Même ta montre se demande si tu l'as portée pour autre chose que décorer ton poignet.",
        "{score}/20 {win}, {ins} : à ce niveau-là, ce n'est plus un entraînement, c'est une sieste avec une montre connectée.",
        "Alors {name}, {score}/20 {win} ? Ton canapé a dû faire plus de kilomètres que toi.",
        "{score}/20 {win}. Franchement {ins}, même ma calculette a honte de ce score.",
        "Aïe aïe aïe, {score}/20 {win} : le Garmin a envoyé un SOS, mais tu l'as pris pour une notification et tu l'as ignoré.",
        "{nick}, {score}/20 {win}. On va dire que c'était une période de « récupération active » très, très passive.",
        "{score}/20 {win} : tu n'as pas perdu ta forme, {ins}, tu l'as mise en pension sans date de retour.",
        "Bilan {win} : {score}/20. Si c'était une course, tu serais encore en train de lacer tes chaussures.",
        "{name}, {score}/20 {win}… ton plan d'entraînement a déposé une main courante pour abandon de poste.",
        "{score}/20 {win} : le Garmin cherche encore le moment où tu t'es entraîné, il a fini par abandonner les recherches.",
        "Alors là {nick}, {score}/20 {win}, on est plus près de la hibernation que de la préparation marathon.",
        "{score}/20 {win}, {ins} : même un panneau « sortie » a plus de cardio que toi en ce moment.",
        "{score}/20 {win} : ta montre a plus de séances de sommeil que de séances de sport, {ins}.",
        "{nick}, {score}/20 {win} : pour te motiver, imagine la tête de ton futur toi sur la ligne d'arrivée en train de marcher.",
        "{score}/20 {win}, {nick} : j'ai vu des fougères plus actives que ton planning.",
        "{name}, {score}/20 {win} : ton entraînement a pris sa retraite sans prévenir son employeur.",
        "{score}/20 {win}, {ins} : même la poussière sur tes baskets a plus de kilomètres que toi.",
    ],
    "bas": [
        "{nick}, {score}/20 {win} : c'est pas la catastrophe, mais ton ambition a l'air d'avoir pris des vacances sans te prévenir.",
        "{score}/20 {win}. Tu t'entraînes un peu comme on fait ses impôts : le plus tard et le moins possible.",
        "{name}, {score}/20 {win}, ça sent le « je m'y remets lundi » répété depuis trois semaines.",
        "{score}/20 {win}, {ins} : tu as bien fait quelques trucs, mais disons que ça ne fera pas peur à tes futurs adversaires.",
        "Note {win} : {score}/20. Tu es au stade où l'effort existe, mais où on a encore du mal à le prouver.",
        "{nick}, {score}/20 {win}. Il y a du potentiel là-dedans, il dort juste très profondément.",
        "{score}/20 {win} : ni honte ni gloire, juste un gros « peut mieux faire » écrit en rouge sur ton bulletin.",
        "Avec {score}/20 {win}, tu es dans le ventre mou du classement, et au vu de la période, le mot « ventre » n'est pas anodin.",
        "{name}, {score}/20 {win} : tu fais semblant de t'entraîner et ta montre fait semblant d'y croire.",
        "{score}/20 {win}, {ins}. Le moteur est là, c'est le conducteur qui traîne les pieds.",
        "Bon, {score}/20 {win} : le verdict tombe, et il porte un petit sourire gêné.",
        "{nick}, {score}/20 {win}. Ce n'est pas un échec, c'est un prologue très, très long.",
        "{score}/20 {win} : ni fait, ni à faire, mais plutôt « à refaire », {nick}.",
        "{name}, {score}/20 {win} : un bulletin avec la mention « présent, mais discret », {ins}.",
        "{nick}, {score}/20 {win} : il y a de l'intention, il manque l'exécution, comme un bon plan sans la moindre pelle.",
        "{score}/20 {win}, {ins} : tu es dans le « je vais m'y mettre » depuis assez longtemps pour que ça devienne un mode de vie.",
        "{name}, {score}/20 {win} : ni catastrophe ni exploit, juste un bon vieux mercredi.",
    ],
    "moyen": [
        "{nick}, {score}/20 {win} : du solide, du sérieux, mais pas encore de quoi faire pleurer tes rivaux.",
        "{score}/20 {win}. Tu es au milieu du gué : assez bon pour ne pas rougir, pas assez pour te vanter à la machine à café.",
        "{name}, {score}/20 {win} : la copie est correcte, mais la mention « bien » te regarde de loin en ricanant.",
        "{score}/20 {win}. C'est le score d'un mec qui s'entraîne vraiment, mais qui garde un peu de marge « au cas où ».",
        "{nick}, {score}/20 {win}. On est dans le « pas mal du tout », catégorie « peut encore passer à la vitesse supérieure ».",
        "Note {win} : {score}/20. Honnête comme un diesel : ça avance, c'est fiable, ça ne fait pas vibrer les foules.",
        "{score}/20 {win}, {nick} : tu es sur la bonne route, il manque juste de mettre un peu plus de gaz.",
        "{name}, {score}/20 {win} : tu cumules les bons points et les petits relâchements, une vraie balance de pâtissier.",
        "{score}/20 {win}. Le niveau est là, reste à trouver le bouton « un cran de plus ».",
        "{nick}, {score}/20 {win} : ton entraînement a une allure de croisière, magnifique pour les pigeons, léger pour un marathonien.",
        "Avec {score}/20 {win}, tu mérites un petit hochement de tête respectueux, pas encore la standing ovation.",
        "{score}/20 {win} : l'équilibre est correct, la marge de progression, elle, est insolente.",
        "{score}/20 {win}, {nick} : du travail propre, pas encore du travail héroïque, mais on sent que ça travaille en coulisses.",
        "{name}, {score}/20 {win} : un peu comme une pizza correcte : ça passe, ça nourrit, mais ça ne fait pas d'étincelles.",
        "{score}/20 {win}, {nick} : solide comme un bon pain complet, pas encore la baguette de compétition.",
        "{name}, {score}/20 {win} : tu es régulier dans la demi-mesure, ce qui est déjà une forme d'art.",
        "{score}/20 {win} : la route est tracée, il te reste à appuyer sur le champignon, {nick}.",
    ],
    "bon": [
        "{nick}, {score}/20 {win} : voilà un bilan qui sent bon la sueur et le sérieux !",
        "{score}/20 {win}. Quelqu'un s'entraîne bien en ce moment, et oui, c'est de toi que je parle, {nick}.",
        "{name}, {score}/20 {win} : tu as de quoi bomber le torse, mais pas trop, la vanité alourdit les foulées.",
        "{score}/20 {win} : franchement propre. Ton Garmin a même osé un petit sourire en coin.",
        "Note {win} : {score}/20. Tu envoies du lourd, {nick}, sans vraiment trembler.",
        "{score}/20 {win}. Les chiffres sont beaux, ta préparation commence à ressembler à quelque chose de très sérieux.",
        "{nick}, {score}/20 {win} : on sent la régularité, ce vieux truc que personne n'aime mais qui gagne les courses.",
        "{name}, {score}/20 {win} : si tu continues comme ça, tes baskets vont demander une augmentation.",
        "{score}/20 {win} : la rigueur paye, et là elle paye plutôt bien.",
        "{nick}, {score}/20 {win}. Même ton moi du mois dernier te regarderait avec un peu de jalousie.",
        "Avec {score}/20 {win}, tu es clairement dans le haut du panier, celui sans légumes en purée.",
        "{score}/20 {win} : du bon boulot, du vrai, de celui qui laisse des traces dans les cuisses.",
        "{score}/20 {win}, {nick} : on dirait que quelqu'un a mangé son plan d'entraînement au petit déjeuner et qu'il l'a bien digéré.",
        "{name}, {score}/20 {win} : ton Garmin te fait des clins d'œil, ne le prends pas pour de la drague.",
        "{nick}, {score}/20 {win} : ça sent bon, comme une cuisine un dimanche où quelqu'un s'applique.",
        "{score}/20 {win}, {name} : si tu continues, je vais devoir sortir les compliments de la réserve.",
        "{score}/20 {win} : de la belle ouvrage, signée {name}, avec la sueur au bas de la page.",
    ],
    "tres_bon": [
        "{nick}, {score}/20 {win} : mais c'est quoi ce niveau ?! Garde un peu de talent pour les autres, par politesse.",
        "{score}/20 {win}. Je commence à croire que tu as signé un deal avec le diable du cardio.",
        "{name}, {score}/20 {win} : tu fais passer le reste du peloton pour un club de pétanque.",
        "{score}/20 {win}, {nick} : le Garmin est en train d'encadrer ta fiche de performance.",
        "Note {win} : {score}/20. On n'est plus dans l'entraînement, on est dans la démonstration de force.",
        "{score}/20 {win}. Tu es en feu, {nick}, vérifie juste que ta montre ne fond pas au poignet.",
        "{nick}, {score}/20 {win} : j'avais prévu une blague pour te chambrer, mais là, honnêtement, je n'ai rien.",
        "{name}, {score}/20 {win} : tes concurrents devraient changer de sport, ou de courses.",
        "{score}/20 {win} : du jamais vu depuis tes débuts, et pas un gramme de chance là-dedans, que du boulot.",
        "{nick}, {score}/20 {win}. Les bonnes performances ne se négocient pas, elles se courent, et toi tu cours.",
        "Avec {score}/20 {win}, tu mériterais presque une médaille en chocolat, par pur esprit de contradiction.",
        "{score}/20 {win} : l'élite fait un pas de côté et te laisse la place, c'est écrit dans les chiffres.",
        "{score}/20 {win}, {nick} : les concurrents ont dû voir ta fiche, ils ont déjà regardé les inscriptions des courses voisines.",
        "{name}, {score}/20 {win} : même moi, qui suis pourtant objectif, je suis obligé de lâcher un petit « bravo ».",
        "{score}/20 {win}, {nick} : tes mollets ont un agent, et ton Garmin envisage de demander une augmentation.",
        "{name}, {score}/20 {win} : franchement, on n'a plus l'habitude de voir des chiffres aussi propres.",
        "{score}/20 {win} : une période de patron, {nick}, de celles qu'on raconte aux petits-enfants.",
    ],
    "elite": [
        "{nick}, {score}/20 {win} : quelqu'un a branché ton Garmin sur un cheval de course ?",
        "{score}/20 {win}. Je suis obligé de vérifier si la montre n'a pas un bug en ta faveur, parce que là, c'est insolent.",
        "{name}, {score}/20 {win} : tu es officiellement dans la catégorie « machine à produire de la perf ».",
        "{score}/20 {win}, {nick} : les copains vont arrêter de t'inviter au footing, ça devient un manque de respect.",
        "Note {win} : {score}/20. On n'a pas de mot, alors on se contente d'un respect poli et un peu jaloux.",
        "{score}/20 {win}. Tu es au sommet de ta propre courbe, avec la vue qui va avec : fais gaffe au vertige.",
        "{nick}, {score}/20 {win} : même mes banques de phrases n'ont pas prévu autant de compliments.",
        "{name}, {score}/20 {win} : tout est aligné, comme un alignement de planètes mais en plus transpirant.",
        "{score}/20 {win} : je dirais « bravo » mais tu as trop de modestie pour l'entendre, alors voilà : respect.",
        "{nick}, {score}/20 {win}. Si la forme avait un pays, tu en serais le président.",
        "Avec {score}/20 {win}, tu es la preuve vivante que le sérieux, ça marche vraiment.",
        "{score}/20 {win} : un bilan de pro, de ceux qu'on imprime et qu'on accroche dans le vestiaire.",
        "{score}/20 {win}, {nick} : je cherche encore le point faible, à la loupe, avec une lampe torche, rien.",
        "{name}, {score}/20 {win} : tu es dans le club des gens dont on regarde le dossier pour se motiver.",
        "{score}/20 {win}, {nick} : si c'était une copie, je la ferais encadrer.",
        "{name}, {score}/20 {win} : tu viens de faire passer les statistiques pour un conte de fées.",
        "{score}/20 {win} : même mon algorithme, d'habitude blasé, a eu un petit frisson, {nick}.",
    ],
}

# ---------------------------------------------------------------------------------------------
# 2. PILIERS : meilleur pilier (STRONG) / pilier le plus faible (WEAK) par clé de pilier
# Variables : {nick} {ins} {win} {sc} (note du pilier /4) + {glabel} {gret} {gtarget} (pred) · {kmw} {long_km} (run) ·
#             {acwr} (load) · {sleep_h} {hrv_pct} (rec) · {sw} {cw} (cross)
# ---------------------------------------------------------------------------------------------
STRONG = {
    "pred": [
        "Ton meilleur pilier, ce sont les prédictions ({sc}/4) : ton {glabel} se dessine en {gret}, le chrono commence à te respecter.",
        "Les chronos prédits sont ton point fort ({sc}/4) : {gret} sur {glabel}, ça fait déjà peur à ta propre moyenne.",
        "Côté prédictions ({sc}/4), tu brilles : {gret} annoncé sur {glabel}, de quoi faire sourire ton futur dossard.",
        "Tes projections de temps tiennent la route ({sc}/4), {nick} : {glabel} en {gret}, la calculatrice est de ton côté.",
        "Le pilier « prédictions » ressort en tête ({sc}/4) : tes jambes savent ce qu'elles font, {glabel} en {gret}.",
        "Tes temps estimés sont ta fierté {win} ({sc}/4) : {gret} sur {glabel}, ça sent le chrono qui claque.",
        "Ce qui brille le plus, c'est la projection de performance ({sc}/4) : {glabel} en {gret}, jolie ligne sur la fiche.",
        "Tes prédictions sont ton arme fatale ({sc}/4) : {gret} sur {glabel}, même ta calculatrice demande ton autographe.",
        "Le chrono prédit est ton chouchou ({sc}/4) : {glabel} en {gret}, de quoi mettre la pression à tes futurs concurrents, {nick}.",
        "Ta prédiction de chrono est ton plus bel atout ({sc}/4) : {glabel} en {gret}, une belle promesse à tenir, {nick}.",
    ],
    "run": [
        "Ta course à pied tient le haut de l'affiche ({sc}/4) avec {kmw} km par semaine : tes chaussures chantent ton nom.",
        "Le pilier course à pied est ton meilleur ({sc}/4) : {kmw} km/sem, les trottoirs de ton quartier te connaissent par cœur.",
        "Côté course ({sc}/4), c'est du sérieux : {kmw} km par semaine, ta paire de baskets a demandé un syndicat.",
        "Tu cours bien {win} ({sc}/4), {nick} : {kmw} km/sem, la routine qui fait les marathoniens.",
        "Ton point fort, c'est la course ({sc}/4) : {kmw} km par semaine, la sortie longue à {long_km} km, bref, tu tiens ta préparation.",
        "Les kilomètres parlent pour toi ({sc}/4) : {kmw} par semaine, tes mollets te remercient (ou menacent de le faire).",
        "La course à pied porte ton bilan ({sc}/4) : {kmw} km/sem et une régularité qui ne se discute plus.",
        "La course à pied est ton royaume ({sc}/4) : {kmw} km par semaine, tes baskets sont officiellement tes meilleures amies.",
        "Tu es dans ton élément ({sc}/4) : {kmw} km/sem, même les pigeons de ton quartier te saluent en passant, {nick}.",
        "La course à pied porte tout le reste ({sc}/4) : {kmw} km/sem, un vrai moteur de préparation.",
    ],
    "load": [
        "Ta gestion de la charge est ta plus grande force ({sc}/4) : ratio à {acwr}, ni trop, ni trop peu, tu pilotes comme un pro.",
        "Le pilier « charge » domine ({sc}/4) : un ratio de {acwr}, c'est du dosage d'orfèvre, pas de la bourrinerie.",
        "Tu sais doser, {nick} ({sc}/4) : ratio à {acwr}, le corps encaisse et progresse sans râler.",
        "Côté charge ({sc}/4), c'est propre : {acwr} de ratio, la montée en puissance est maîtrisée de bout en bout.",
        "Ta progressivité est ton atout ({sc}/4) : ratio {acwr}, tes tendons te font un gros câlin silencieux.",
        "La gestion de charge est impeccable {win} ({sc}/4) : {acwr}, la zone idéale te va comme un gant.",
        "Pas de pic, pas de trou : ta charge est régulière ({sc}/4), ratio {acwr}, un modèle du genre.",
        "Ta charge est un modèle du genre ({sc}/4) : ratio à {acwr}, un dosage digne d'un pharmacien de précision.",
        "Charge sous contrôle ({sc}/4) : {acwr} de ratio, ni trop ni trop peu, tu es le Goldilocks de l'entraînement, {nick}.",
        "Ta charge est irréprochable ({sc}/4) : ratio {acwr}, une courbe qu'on pourrait encadrer, {nick}.",
    ],
    "rec": [
        "Ta récupération est ton meilleur atout ({sc}/4) : {sleep_h} h de sommeil et une VFC à {hrv_pct}, ton corps te dit merci.",
        "Le sommeil et la VFC portent ton bilan ({sc}/4) : {sleep_h} h par nuit, le corps absorbe l'entraînement comme une éponge.",
        "Côté récupération ({sc}/4), tu assures : VFC à {hrv_pct}, les nuits sont bonnes, la machine se régénère.",
        "Tu dors comme un pro ({sc}/4), {nick} : {sleep_h} h de moyenne, l'oreiller est ton meilleur partenaire d'entraînement.",
        "La récupération est ton point fort ({sc}/4) : VFC à {hrv_pct} et un sommeil solide, la base de tout progrès.",
        "Le pilier récupération brille ({sc}/4) : tes nuits de {sleep_h} h font plus pour ta forme que bien des séances.",
        "Ta récupération est d'une qualité rare ({sc}/4) : le sommeil réparateur, ça se voit dans les chiffres.",
        "La récupération est ta botte secrète ({sc}/4) : {sleep_h} h de sommeil, VFC à {hrv_pct}, tu dors comme on s'entraîne : sérieusement.",
        "Côté dodo, tu es champion ({sc}/4) : {sleep_h} h par nuit, la VFC {hrv_pct}, ton oreiller mérite une médaille.",
        "Ta récupération est un modèle ({sc}/4) : VFC à {hrv_pct}, {sleep_h} h de sommeil, le repos est ton arme secrète.",
    ],
    "cross": [
        "Ton cross-training est en tête ({sc}/4) : {sw} séance(s) de muscu par semaine, tes muscles ont un plan B pour chaque situation.",
        "La polyvalence fait ta force ({sc}/4) : muscu, vélo, natation, tu varies les plaisirs comme un vrai touche-à-tout.",
        "Côté muscu et multisport ({sc}/4), tu assures : tu renforces ce que la course fatigue, bien joué.",
        "Le pilier muscu et cross-training domine ({sc}/4), {nick} : {sw} séance(s) de muscu par semaine, tes tendons applaudissent.",
        "Tu travailles ton physique en profondeur ({sc}/4) : la muscu et les autres sports te rendent plus solide à chaque foulée.",
        "Le cross-training est ton atout caché ({sc}/4) : un athlète complet, pas un simple coureur du dimanche.",
        "Muscu, vélo, natation : ta polyvalence ressort ({sc}/4), et ça protégera tes jambes quand les kilomètres vont s'accumuler.",
        "Le cross-training est ton atout charme ({sc}/4) : tu travailles tout le corps, pas seulement les jambes, les tendons te remercient.",
        "Tu es un athlète complet ({sc}/4), {nick} : muscu, vélo, natation, tu fais le tour de la cage thoracique sans te lasser.",
        "Ton cross-training est un trésor ({sc}/4) : tu bâtis un corps complet, pas seulement des jambes, {nick}.",
    ],
}
WEAK = {
    "pred": [
        "Côté prédictions ({sc}/4), il y a du boulot : {gret} sur {glabel} pour {gtarget} visé, le chrono te regarde en rigolant.",
        "Tes chronos prédits sont ton point faible ({sc}/4), {nick} : {glabel} en {gret}, l'objectif de {gtarget} fait un peu de la figuration.",
        "Le pilier « prédictions » traîne ({sc}/4) : {gret} annoncé sur {glabel}, loin de {gtarget}, la calculatrice fait la grimace.",
        "Les projections de temps sont à la peine ({sc}/4) : {glabel} en {gret}, {ins}, ton objectif attend toujours que tu viennes le chercher.",
        "Ta prédiction chrono est le maillon faible ({sc}/4) : {gret} sur {glabel}, ça ne rentre pas encore dans les {gtarget}.",
        "Au rayon chrono ({sc}/4), c'est tiède : {gret} sur {glabel}, la case « {gtarget} » reste lointaine.",
        "Le pilier prédictions est ton talon d'Achille ({sc}/4) : {glabel} en {gret}, pas encore le bon voyant au vert.",
        "Le pilier prédictions joue à cache-cache avec toi ({sc}/4) : {glabel} en {gret}, {gtarget} visé, il faudra l'attraper.",
        "Les chronos prédits boudent ({sc}/4) : {gret} sur {glabel}, l'objectif de {gtarget} fait semblant de ne pas te connaître, {nick}.",
        "Tes prédictions sont ton point mou ({sc}/4) : {gret} sur {glabel} pour {gtarget} visé, le chrono n'est pas encore dans le bon fuseau horaire.",
    ],
    "run": [
        "Ta course à pied est ton point faible ({sc}/4) : {kmw} km par semaine, {ins}, ton marathon n'est pas du tout impressionné.",
        "Le pilier course patine ({sc}/4) : {kmw} km/sem, c'est le volume d'un touriste qui cherche son hôtel, pas d'un marathonien.",
        "Côté course ({sc}/4), c'est maigre : {kmw} km par semaine, les trottoirs de ton quartier t'ont oublié.",
        "Tu cours trop peu {win} ({sc}/4), {nick} : {kmw} km/sem, tes baskets ont repris racine dans le placard.",
        "La course à pied est à la traîne ({sc}/4) : {kmw} km par semaine, ta sortie longue à {long_km} km pas à la hauteur des ambitions.",
        "Ton volume de course est le grand absent ({sc}/4) : {kmw} km/sem, le marathon, lui, ne se prépare pas avec de bonnes intentions.",
        "Le pilier course accuse le coup ({sc}/4) : {kmw} km par semaine, il va falloir réveiller les jambes, {ins}.",
        "La course à pied fait pâle figure ({sc}/4) : {kmw} km par semaine, le bitume commence à t'oublier.",
        "Ton volume de course est au régime sec ({sc}/4) : {kmw} km/sem, autant dire que tes mollets sont en CDD, {ins}.",
        "La course à pied doit se réveiller ({sc}/4) : {kmw} km/sem, les kilomètres sont comme la monnaie, il faut en avoir pour les dépenser.",
    ],
    "load_low": [
        "Ta charge d'entraînement est trop légère ({sc}/4) : ratio à {acwr}, tu es en sous-régime, {nick}, le corps attend qu'on le sollicite.",
        "Le pilier « charge » est trop bas ({sc}/4) : {acwr} de ratio, tu t'entraînes moins que d'habitude, et ton niveau va finir par s'en apercevoir.",
        "Côté charge ({sc}/4), c'est le calme plat : ratio {acwr}, la période a l'air d'avoir été très, très reposante.",
        "Ta progressivité est à l'arrêt ({sc}/4) : {acwr} de ratio, la forme ne se construit pas en restant au chaud, {ins}.",
        "La charge d'entraînement est en berne ({sc}/4) : ratio {acwr}, tu es loin de la zone où on progresse vraiment.",
        "Charge d'entraînement : {sc}/4, ratio à {acwr} : le corps a perdu l'habitude d'être sollicité, il va falloir remonter doucement.",
        "Charge d'entraînement en mode économie d'énergie ({sc}/4) : ratio {acwr}, la batterie du corps est pleine mais inutilisée.",
        "Côté charge ({sc}/4), tu es en sommeil : ratio {acwr}, il faut rallumer les moteurs, {nick}.",
        "Charge très légère ({sc}/4) : ratio {acwr}, ton corps attend un peu plus de motivation, {nick}.",
    ],
    "load_high": [
        "Ta charge d'entraînement est trop forte ({sc}/4) : ratio à {acwr}, tu montes en puissance plus vite que ton corps ne l'encaisse, {nick}.",
        "Le pilier « charge » grince ({sc}/4) : {acwr} de ratio, ça monte trop vite, et les blessures adorent les montées trop rapides.",
        "Côté charge ({sc}/4), tu pousses fort : ratio {acwr}, la zone de confort est derrière toi, le risque de blessure devant.",
        "Ta progressivité est à revoir ({sc}/4) : {acwr} de ratio, ton corps aime la routine, pas les montagnes russes.",
        "La gestion de charge est ton point noir ({sc}/4) : ratio {acwr}, trop d'un coup, le yoyo n'a jamais fait de marathonien.",
        "Charge d'entraînement : {sc}/4, ratio à {acwr} : tu en fais beaucoup, peut-être trop, et ton corps le dira bientôt à sa façon.",
        "Charge d'entraînement en mode « tout, tout de suite » ({sc}/4) : ratio {acwr}, ton corps demande une pause syndicale.",
        "Côté charge ({sc}/4), tu appuies comme un fou : ratio {acwr}, les tendons commencent à envoyer des lettres de réclamation.",
        "Charge en surchauffe ({sc}/4) : ratio {acwr}, tu travailles comme si le marathon était demain.",
    ],
    "rec": [
        "Ta récupération est ton point faible ({sc}/4) : {sleep_h} h de sommeil et une VFC à {hrv_pct}, ton corps tire la langue.",
        "Le pilier récupération sonne l'alarme ({sc}/4) : {sleep_h} h par nuit, tu t'entraînes sur ta réserve, pas sur ton énergie.",
        "Côté sommeil et VFC ({sc}/4), c'est juste : VFC à {hrv_pct}, ton corps te réclame un peu plus de temps de présence au lit.",
        "Ta récupération tire sur la corde, {nick} ({sc}/4) : {sleep_h} h de sommeil de moyenne et une VFC à {hrv_pct}, rien ne progresse sans que le corps répare.",
        "La récupération est à la peine ({sc}/4) : VFC à {hrv_pct}, ce que tu ne régénères pas, tu le paieras cash.",
        "Le pilier récupération est dans le rouge ({sc}/4) : des nuits de {sleep_h} h, et un corps qui dit « stop » discrètement.",
        "Ton repos est ton talon d'Achille ({sc}/4) : récupérer fait partie de l'entraînement, et en ce moment tu sèches même cette séance-là, {ins}.",
        "La récupération fait la grimace ({sc}/4) : {sleep_h} h de sommeil, VFC à {hrv_pct}, ton corps rame pour suivre.",
        "Le dodo est le maillon faible ({sc}/4), {nick} : {sleep_h} h de moyenne et une VFC à {hrv_pct}, le repos aussi s'entraîne.",
        "La récupération est à renforcer ({sc}/4) : VFC à {hrv_pct}, {sleep_h} h de sommeil, il faut soigner les nuits autant que les séances.",
    ],
    "cross": [
        "La muscu et le multisport sont ton point faible ({sc}/4) : {sw} séance(s) de muscu par semaine, tes tendons attendent leur renfort.",
        "Le pilier cross-training traîne ({sc}/4) : {sw} séance(s) de muscu par semaine, {ins}, les haltères prennent la poussière.",
        "Côté muscu et multisport ({sc}/4), c'est maigre : {sw} muscu/sem, {cw} vélo+natation, ton corps ne tiendra pas sur un seul pied.",
        "Tu négliges le cross-training ({sc}/4), {nick} : sans renfort, les kilomètres de marathon se paient en blessures.",
        "Ta muscu et ton multisport sont à la peine ({sc}/4) : {sw} séance(s) par semaine, les gainages se languissent de toi.",
        "Le cross-training est le grand oublié ({sc}/4) : un coureur qui ne se renforce pas, c'est une voiture sans amortisseurs.",
        "Pilier muscu et multisport : {sc}/4, {ins}. Le vélo et la natation existent, même s'ils semblent absents de ton agenda.",
        "Le cross-training est aux abonnés absents ({sc}/4) : {sw} séance(s) de muscu par semaine, tes haltères ont posé une main courante.",
        "Côté renfort ({sc}/4), c'est mince : {sw} muscu/sem, {cw} vélo+natation, un coureur sans renfort, c'est un château de cartes en short.",
        "Le cross-training est à relancer ({sc}/4) : {sw} séance(s) de muscu par semaine, un coureur sans renfort est un château de sable à marée montante.",
    ],
}
# Tous les piliers proches les uns des autres
BALANCED = {
    "hi": [
        "Tes 5 piliers sont tous bien orientés, du coup pas de maillon faible à chambrer, et c'est franchement agaçant.",
        "Le profil est équilibré et solide partout : aucun pilier ne dépasse, aucun ne traîne, une vraie machine bien réglée.",
        "Tout se tient : performance, charge, récupération, polyvalence, c'est de l'horlogerie, et je n'ai rien à redire.",
        "Pas de pilier qui sort du lot : tout est bon partout, ce qui est moins drôle pour moi mais très bon pour toi.",
        "Les cinq piliers sont alignés vers le haut, {nick}, tu construis quelque chose de très propre.",
        "Rien à signaler au rayon points faibles : l'ensemble est cohérent et solide, bravo pour cette régularité.",
    ],
    "mid": [
        "Tes 5 piliers sont tous au même niveau, moyen, tout est correct, rien n'est flamboyant : un vrai buffet de cantine.",
        "Le profil est plat : aucun pilier ne brille, aucun ne s'effondre, c'est stable mais ça ne fait pas rêver.",
        "Pas de point fort ni de point faible marqué : tu es régulièrement moyen sur tous les fronts, {nick}.",
        "Tes piliers avancent groupés, dans le milieu du peloton : le potentiel est là, il manque l'étincelle sur un des cinq.",
        "Équilibré dans la tiédeur : tout est à peu près pareil, choisis un pilier et fais-en ton fer de lance.",
        "Aucun pilier ne dépasse : pour progresser, il va falloir choisir lequel tirer vers le haut en premier.",
    ],
    "lo": [
        "Tes 5 piliers sont tous au ras du sol : l'équilibre est parfait, mais dans la médiocrité, {ins}.",
        "Tout est faible partout : au moins tu n'as pas de pilier favori, c'est de l'égalité dans la galère.",
        "Pas un seul pilier ne tient la route, et c'est d'une régularité presque admirable, {nick}.",
        "Les cinq piliers sont dans le même état : au repos. Il va falloir en réveiller un pour entraîner les autres.",
        "Le profil est plat et bas, comme une bière oubliée au soleil : choisis un pilier et commence par là.",
        "Aucun pilier ne s'en sort : on repart de zéro, ce qui a au moins l'avantage de simplifier le plan.",
    ],
}
# Quand même le meilleur pilier est bas, ou même le plus faible est bon
BEST_LOW = [
    "Même ton meilleur pilier, « {pname} », ne fait que {sc}/4 : on est loin d'un podium, {nick}.",
    "Ton « meilleur » pilier est {pname} avec {sc}/4, et c'est dire le niveau du reste, {ins}.",
    "Le moins pire des piliers est « {pname} » ({sc}/4) : on prend les bonnes nouvelles là où elles sont.",
    "« {pname} » ressort en tête, avec un modeste {sc}/4 : c'est la médaille d'or d'une compétition à trois participants.",
    "Si tu cherches un point positif, « {pname} » est le moins faible ({sc}/4) : tout se joue à partir de là.",
    "Le meilleur pilier, « {pname} », plafonne à {sc}/4 : il y a de la marge, beaucoup de marge.",
]
WORST_HIGH = [
    "Même ton pilier le plus faible, « {pname} », tient la route avec {sc}/4 : le mot « faiblesse » est presque exagéré.",
    "Ton point le moins fort, « {pname} » ({sc}/4), serait le point fort de beaucoup d'autres, {nick}.",
    "Le « maillon faible » s'appelle {pname} avec {sc}/4, ce qui reste très honorable : tu peux t'en servir comme cible du mois.",
    "Pas de vrai point faible : « {pname} » est juste un peu derrière ({sc}/4), mais sans honte.",
    "Ton pilier le plus bas, « {pname} », affiche {sc}/4 : c'est un problème de riche.",
    "Le plus faible des piliers, « {pname} » ({sc}/4), est encore bien au-dessus de ce que font la plupart des gens.",
]

# ---------------------------------------------------------------------------------------------
# 3. GOAL : où en est la prédiction vs l'objectif (course visée)
# Variables : {nick} {ins} {win} {glabel} {gret} {gtarget} {ggap} {gpct}
# ---------------------------------------------------------------------------------------------
GOAL = {
    "ahead": [
        "Côté objectif, {glabel} : prédiction {gret} pour {gtarget} visé, tu es en avance, {nick}, et c'est tout à ton honneur.",
        "Ton {glabel} est déjà dans les clous : {gret} prédit pour {gtarget} visé, il ne reste qu'à confirmer le jour J.",
        "Prédiction sur {glabel} : {gret}, pour un objectif de {gtarget}. La cible est atteinte sur le papier, reste à la tenir sur le bitume.",
        "Pour {glabel}, tes projections ({gret}) battent ton objectif ({gtarget}) : le plan marche, ne le casse surtout pas.",
        "{glabel} : {gret} annoncé, {gtarget} visé, tu as de la marge de sécurité, ce qui est rare et précieux.",
        "Ton objectif de {gtarget} sur {glabel} est à portée de main avec {gret} de prédiction, ne fais pas n'importe quoi maintenant.",
        "Sur {glabel}, la montre prédit {gret} pour {gtarget} visé : de quoi dormir tranquille, enfin presque.",
        "Objectif {glabel} : {gret} prédit pour {gtarget} visé, tu as de la marge, garde-la comme une bonne bouteille.",
        "Pour {glabel}, la montre prédit {gret}, ton objectif est de {gtarget} : tu as l'avance, il reste à la gérer sans la gâcher, {nick}.",
    ],
    "close": [
        "Côté objectif, {glabel} : prédiction {gret} pour {gtarget} visé, à {ggap} près, ça va se jouer au détail.",
        "Ton {glabel} est tout proche : {gret} prédit pour {gtarget}, il manque {ggap}, soit quelques bonnes semaines de travail.",
        "Pour {glabel}, tu es à {ggap} de ton objectif ({gret} contre {gtarget}) : c'est jouable, mais ça va demander du sérieux.",
        "{glabel} : {gret} annoncé, {gtarget} visé, ça tient à un fil de {ggap}, {nick}.",
        "Sur {glabel}, les projections disent {gret} pour {gtarget} visé : {ggap} à gagner, une paille pour un athlète motivé.",
        "Ton objectif de {gtarget} sur {glabel} te nargue de {ggap} : tout est possible, rien n'est gagné.",
        "{glabel} en {gret} prédit, pour {gtarget} visé : il te manque {ggap}, et l'effort supplémentaire à fournir sera bien réel.",
        "Objectif {glabel} : {gret} prédit, {gtarget} visé, {ggap} d'écart : on est dans la zone où chaque séance se voit.",
        "Pour {glabel}, tu es à {ggap} du but : ça ne tient plus qu'à un fil, et le fil c'est ta régularité, {nick}.",
    ],
    "mid": [
        "Côté objectif, {glabel} : prédiction {gret} pour {gtarget} visé, il reste {ggap} à gagner, ce n'est pas une promenade de santé.",
        "Ton {glabel} demande encore du travail : {gret} prédit pour {gtarget}, soit {ggap} de retard à rattraper.",
        "Pour {glabel}, l'écart est de {ggap} ({gret} prédit, {gtarget} visé) : accessible, mais pas sans sueur ni régularité.",
        "{glabel} : {gret} annoncé, {gtarget} visé, tu as {ggap} à grignoter, et ça ne se fera pas avec de bonnes intentions.",
        "Sur {glabel}, les projections te laissent à {ggap} de ton objectif de {gtarget} : il va falloir mettre du cœur à l'ouvrage.",
        "Ton objectif de {gtarget} sur {glabel} est encore loin de {ggap} ({gret} prédit) : ça se travaille, séance après séance.",
        "{glabel} en {gret} prédit pour {gtarget} visé : {ggap} de décalage, ce n'est pas désespéré, c'est un programme.",
        "Objectif {glabel} : {gret} prédit pour {gtarget} visé, {ggap} à rattraper : ça se joue en semaines, pas en jours.",
        "Pour {glabel}, l'écart ({ggap}) est du genre qui se comble avec du travail propre et du sommeil, {nick}.",
    ],
    "far": [
        "Côté objectif, {glabel} : prédiction {gret} pour {gtarget} visé, {ggap} d'écart, {ins}, il va falloir sérieusement s'y mettre.",
        "Ton {glabel} est loin du compte : {gret} prédit pour {gtarget} visé, soit {ggap} à rattraper, c'est un vrai chantier.",
        "Pour {glabel}, l'écart est de {ggap} ({gret} prédit, {gtarget} visé) : l'objectif existe, la préparation, un peu moins.",
        "{glabel} : {gret} annoncé, {gtarget} visé, {ggap} de décalage : ça ne se rattrape pas en regardant les courses des autres à la télé.",
        "Sur {glabel}, ta prédiction ({gret}) est à {ggap} de ton objectif de {gtarget} : un fossé qui se comble à coups de séances, pas de promesses.",
        "Ton objectif de {gtarget} sur {glabel} s'éloigne de {ggap} ({gret} prédit) : revois ta copie, {nick}, ou ton objectif.",
        "{glabel} en {gret} prédit pour {gtarget} visé : {ggap} de trop, il y a du pain sur la planche, et pas que du pain complet.",
        "Objectif {glabel} : {gret} prédit pour {gtarget} visé, {ggap} d'écart : ça va demander de la sueur et de la patience, dans cet ordre.",
        "Pour {glabel}, le fossé est de {ggap} : on le comble à coups de séances, pas de plans sur la comète.",
    ],
    "none": [
        "Côté objectif, pas assez de sorties pour sortir une prédiction crédible : cours un peu plus et la montre te donnera un chrono.",
        "Impossible de prédire un temps sérieux : trop peu de courses {win}, difficile de deviner ce que tu vaux en restant sur le canapé.",
        "Pas de prédiction fiable {win}, {nick} : sans sorties, la montre n'a rien à se mettre sous la dent.",
        "Aucun chrono prédit pour l'instant : il faut des kilomètres pour que les algorithmes aient une opinion sur toi.",
        "Pour l'objectif de course, les données manquent : donne-moi des sorties à analyser et je te sortirai un temps.",
        "La prédiction de temps reste muette {win} : une montre ne peut pas deviner ton niveau sans te voir courir.",
        "Côté chrono, aucune prédiction fiable {win} : la montre attend que tu lui montres de quoi tu es capable.",
        "Pas de temps prédit {win} : faute de sorties récentes, ton objectif reste dans la brume, {nick}.",
    ],
}

# ---------------------------------------------------------------------------------------------
# 4. STATE : état de forme du moment (profil du jour) + modificateur de période
# Variables : {nick} {ins} {name} {strain} {faf} {hrv_pct} {sleep_score} {sleep_h} {acwr} {bb}
# Aucune insulte quand l'état physique est mauvais (fatigue_aiguë, surcharge_musculaire, récupération_incomplète).
# ---------------------------------------------------------------------------------------------
STATE = {
    "forme_optimale": [
        "Côté forme du moment, tu es en pleine bourre : indice de fatigue à {strain}/100, le corps est frais, il n'attend que ton signal.",
        "Aujourd'hui, la machine est prête : VFC à {hrv_pct}, sommeil à {sleep_score}/100, tout est vert, {nick}.",
        "Ton état physique est excellent : tu as de la fraîcheur à revendre, profites-en pour envoyer de la qualité.",
        "Le corps dit « go » : fatigue à {strain}/100, tu es au niveau de forme qui fait faire des exploits, ou des bêtises, à toi de voir.",
        "Aujourd'hui, tu es frais comme un gardon qui a bien dormi : {sleep_h} h de sommeil et la VFC à {hrv_pct}.",
        "La forme est au rendez-vous : le Body Battery à {bb} et une fatigue à {strain}/100, c'est le jour d'envoyer du lourd.",
        "Tout est au vert ce matin, {nick} : indice de forme au sommet, les jambes ont envie de bouger toutes seules.",
        "Ton corps est dans sa meilleure version du moment : récupération au top, c'est le bon jour pour une grosse séance.",
        "État de forme : excellent. Tes jambes ont l'air d'avoir fait un pacte avec la fée du sommeil.",
        "Ton corps est en mode turbo : fatigue à {strain}/100, tout est vert, il ne manque que ta signature au bas de la séance.",
        "État de forme : excellent. Même ton Body Battery à {bb} te fait un clin d'œil, {nick}.",
    ],
    "assimilation_réussie": [
        "Aujourd'hui, ton corps a bien digéré la charge : VFC à {hrv_pct}, ratio à {acwr}, c'est exactement ce qu'on appelle progresser.",
        "Le travail paye : charge en hausse, VFC {hrv_pct}, le corps encaisse et en redemande, {nick}.",
        "Ton état est celui d'un athlète qui absorbe l'entraînement : sommeil à {sleep_score}/100, tout roule, ça progresse en silence.",
        "Bonne nouvelle ce matin : la charge est bien assimilée, le corps se renforce, pas de signe de fatigue qui dérange.",
        "L'assimilation est réussie : tu as chargé, tu as récupéré, tu as progressé, la recette parfaite.",
        "Ton corps digère l'entraînement comme un champion : VFC solide, ratio à {acwr}, continue sur ce rythme sans t'emballer.",
        "Le cycle charge-récupération fonctionne à merveille aujourd'hui : c'est le meilleur état pour grimper encore d'un cran.",
        "Ce matin, ton corps te dit merci : il a assimilé la charge récente, et ça se voit dans les chiffres.",
        "Charge absorbée, VFC solide, sommeil correct : c'est le moment où l'entraînement devient de la performance.",
        "Le travail porte ses fruits : VFC à {hrv_pct}, ratio à {acwr}, ton corps absorbe les séances comme un buvard.",
        "La charge est bien digérée, {nick} : sommeil à {sleep_score}/100, il ne reste plus qu'à récolter.",
    ],
    "maintien": [
        "Côté forme du moment, tu es en mode croisière : indice de fatigue à {strain}/100, ni en forme olympique, ni dans le mur.",
        "Aujourd'hui, tout est stable : VFC à {hrv_pct}, sommeil à {sleep_score}/100, rien de spectaculaire, rien d'inquiétant.",
        "Ton état physique est correct, sans plus : tu peux t'entraîner normalement, {nick}, sans chercher l'exploit.",
        "Le corps est en régime de croisière : pas de fatigue notable, pas d'éclat non plus, la journée parfaite pour une séance honnête.",
        "Forme du moment : « ça va ». Pas de quoi crier au miracle, assez pour bosser proprement.",
        "Ton état est stable et sans surprise, comme un bon vieux diesel : ça démarre, ça roule, ça ne déborde pas.",
        "Aucun signal d'alerte aujourd'hui : fatigue à {strain}/100, la séance du jour peut être de qualité moyenne sans souci.",
        "Le corps est en stand-by actif : prêt à bosser, pas prêt à faire des miracles, et c'est très bien comme ça.",
        "État de forme neutre : ni bonus, ni malus. Tu peux t'entraîner sereinement, sans te mettre dans le rouge.",
        "Forme du moment : en pilote automatique, fatigue à {strain}/100 : tu roules, sans bruit, sans fumée.",
        "Ton corps est en mode « tranquille » : rien à signaler, rien à fêter, rien à craindre, {nick}.",
    ],
    "déficit_aérobie": [
        "Côté forme du moment, ton état est correct (fatigue à {strain}/100), mais c'est ton endurance de base qui manque de volume : pas d'excuse pour rester assis.",
        "Aujourd'hui, le corps est disponible, mais ton moteur aérobie est trop petit : plus de sorties longues en endurance, {nick}.",
        "Ton état est correct, mais ta base d'endurance est un peu juste : les sorties en aisance respiratoire seront ton meilleur ami.",
        "Fatigue à {strain}/100 : le corps suit, il manque le volume. Ton marathon ne se gagne pas qu'avec de bonnes intentions.",
        "Côté endurance, le réservoir est trop petit : tu tiens sur le court, pas assez sur la durée. Du volume, du volume, du volume.",
        "Aujourd'hui, ton corps pourrait en faire plus : ce qui te manque, c'est le fond de caisse.",
        "Ton état est bon mais ta caisse aérobie fait penser à une mobylette : ça avance, mais pas assez longtemps.",
        "La forme du jour est là, la base aérobie, un peu moins : ajoute une sortie longue tranquille et laisse faire le temps.",
        "Ton corps répond présent, {ins} : utilise-le pour allonger tes sorties en endurance.",
        "Ton moteur d'endurance est un petit moteur de scooter : il te faudra du temps et des sorties longues pour le changer en diesel.",
        "Fatigue à {strain}/100, base aérobie à reconstruire : de la patience, du Z2 et encore du Z2, {nick}.",
    ],
    "déficit_anaérobie": [
        "Côté forme du moment, ton état est correct (fatigue à {strain}/100), et ce qui te manque, c'est un peu de vitesse : de quoi mettre de l'intensité.",
        "Aujourd'hui, le corps est prêt à accélérer : ton moteur est bon, mais il manque un peu de nerf, {nick}.",
        "Ton endurance tient, ta vitesse un peu moins : quelques fractionnés bien dosés feraient du bien à ton chrono.",
        "Fatigue à {strain}/100 : c'est jouable pour rappeler à tes jambes qu'elles savent aussi aller vite.",
        "Tu cours beaucoup, mais pas assez vite : un peu de qualité et ton chrono te dira merci.",
        "Le corps est disponible, ton rythme est trop sage : il est temps de réveiller les fibres rapides.",
        "Ton état est bon, ta vitesse de pointe en sommeil : une séance de VMA remettra tout ça en ordre.",
        "Côté vitesse, tu es en retard sur ton niveau de base : une séance de rythme bien placée arrangera ça.",
        "Les jambes roulent à vitesse de promenade : quelques accélérations, et tout ira mieux.",
        "Ta vitesse dort au fond d'un tiroir : on la ressort avec des fractionnés bien dosés, {nick}.",
        "Fatigue à {strain}/100 : le corps accepte le rythme, c'est le moment de réveiller les jambes avec de la VMA.",
    ],
    "récupération_incomplète": [
        "Côté forme du moment, ton corps n'a pas fini de récupérer : fatigue à {strain}/100, VFC à {hrv_pct}, il demande un peu de répit.",
        "Aujourd'hui, la récupération est incomplète : sommeil à {sleep_score}/100, le corps a encore besoin de temps, {nick}.",
        "Ton état est moyen : tu n'es pas au bout du rouleau, mais tu n'as pas tout rechargé non plus, séance douce conseillée.",
        "Le corps traîne un peu : la récupération n'est pas terminée, mieux vaut ne pas pousser aujourd'hui.",
        "Fatigue à {strain}/100 et un sommeil à {sleep_score}/100 : ton corps te demande un peu de douceur, ce n'est pas du luxe.",
        "Tu n'es pas complètement remis, {nick} : une séance tranquille fera plus de bien qu'une séance héroïque.",
        "Les signaux sont tièdes ce matin : le corps n'a pas fini de digérer, mieux vaut lever le pied.",
        "Aujourd'hui, le Body Battery à {bb} te dit d'y aller doucement : la récupération passe avant la performance.",
        "Ton organisme est en phase de réparation : écoute-le, il parle de moins en moins doucement.",
        "Ta récupération n'est qu'à moitié finie : sommeil à {sleep_score}/100, le corps demande la suite avant de repartir, {nick}.",
        "Ce matin, la batterie n'a pas fini de charger : Body Battery à {bb}, on débranche de la performance et on respire.",
    ],
    "surcharge_musculaire": [
        "Côté forme du moment, tes jambes sont en surcharge : ratio à {acwr}, les muscles ont pris cher, il faut ralentir un peu.",
        "Aujourd'hui, tes muscles réclament du repos : la charge est trop haute, {nick}, la séance du jour sera légère ou ne sera pas.",
        "Ton état est celui d'un coureur qui en a trop fait : ratio {acwr}, laisse tes jambes respirer avant qu'elles ne protestent.",
        "Les jambes sont lourdes comme du béton : fatigue musculaire marquée, une séance de récupération s'impose.",
        "La charge récente a dépassé la capacité d'encaissement de tes muscles : lève le pied maintenant, tu remercieras ton futur toi.",
        "Surcharge musculaire détectée : ratio à {acwr}, un jour de repos vaut mieux qu'une blessure de trois semaines.",
        "Ton corps te dit « stop » avec les jambes : écoute-le, parce que la prochaine fois il parlera avec un claquage.",
        "Aujourd'hui, mollets et cuisses sont à la peine : une séance douce ou du repos, mais pas de zèle.",
        "Tu as tellement chargé que tes muscles font grève : accorde-leur une trêve, ils reviendront plus forts.",
        "Les jambes ont la lourdeur d'un pot de béton : ratio à {acwr}, mieux vaut leur donner congé avant qu'elles ne le prennent seules.",
        "Tes muscles ont envoyé un préavis de grève : ratio {acwr}, on négocie avec du repos, {nick}.",
    ],
    "fatigue_aiguë": [
        "Côté forme du moment, tu es à plat : fatigue à {strain}/100, VFC à {hrv_pct}, la priorité du jour, c'est de dormir, pas de courir.",
        "Aujourd'hui, ton corps crie « pitié » : fatigue aiguë, repos obligatoire, {nick}, ce n'est pas une suggestion.",
        "Ton état est rouge : sommeil à {sleep_score}/100, Body Battery à {bb}, il est temps d'arrêter de faire n'importe quoi.",
        "Fatigue aiguë détectée : tu as tiré sur la corde, elle fait un bruit inquiétant, repos total ou séance très légère.",
        "Ton corps n'a plus de batterie : fatigue à {strain}/100, une grosse séance aujourd'hui serait un très mauvais pari.",
        "Les voyants sont tous au rouge : récupération d'abord, performance ensuite, dans cet ordre-là, s'il te plaît.",
        "Tu es cramé : et ce n'est pas une insulte, c'est un diagnostic. Dors, mange, hydrate-toi, et laisse les chaussures tranquilles.",
        "Aujourd'hui, c'est la forme de la serpillière : fatigue élevée, VFC à {hrv_pct}, repos recommandé et non négociable.",
        "Ton organisme a besoin d'une vraie pause : pousse aujourd'hui, et tu le paieras pendant une semaine.",
        "Ton corps affiche « batterie faible » en rouge : fatigue à {strain}/100, branche-le au repos, {nick}.",
        "Voyant rouge partout : sommeil {sleep_score}/100, VFC à {hrv_pct}, repos obligatoire, même les héros dorment.",
    ],
    "données_insuffisantes": [
        "Côté forme du moment, ta montre ne m'en dit pas assez pour juger : porte-la la nuit, que je puisse faire mon travail, {nick}.",
        "Aujourd'hui, les données de récupération manquent : sans sommeil ni VFC, je ne peux pas deviner si tu es frais ou cuit.",
        "L'état de forme reste un mystère : ta montre n'a pas assez de données, essaie de la porter aussi la nuit.",
        "Pas assez de données physiologiques pour te dire comment tu vas : en attendant, fie-toi à tes sensations.",
        "Ta forme du jour est inconnue : ni sommeil, ni VFC à analyser, je ne suis pas devin, juste un algorithme.",
        "Les données de santé sont trop maigres aujourd'hui : porte ta montre à la nuit, que j'ai quelque chose à raconter demain.",
        "Je ne vois ni VFC ni sommeil ce matin : je joue aux devinettes, {nick}, aide-moi en portant ta montre cette nuit.",
        "Pas de données de santé : le tableau de bord est en noir et blanc, mets ta montre à la cheville si besoin !",
    ],
}
# Modificateur ajouté à la phrase d'état (un seul, par ordre de priorité). Variables : {win} {nick} {sleep_debt} {hrv_pct_p} {stress} {bb}
MOD = {
    "debt": [
        "Et ta dette de sommeil de {sleep_debt} h sur 3 nuits ne t'aide pas : dors, c'est gratuit et c'est efficace.",
        "À noter : {sleep_debt} h de dette de sommeil, ton oreiller mérite un peu plus de ta présence.",
        "Petit bémol : le manque de sommeil ({sleep_debt} h de dette) te coûte plus que tu ne crois, {nick}.",
        "Ta dette de sommeil de {sleep_debt} h pèse sur les chiffres : rembourse-la avant de t'entraîner dur.",
        "N'oublie pas que dormir est un sport : tu es à {sleep_debt} h de dette, un rattrapage s'impose.",
        "Ta dette de sommeil de {sleep_debt} h est un crédit que ton corps te réclamera avec intérêts, {nick}.",
        "{sleep_debt} h de dette de sommeil : la banque du dodo ne fait pas de crédit éternel.",
    ],
    "hrv_low": [
        "Ta VFC moyenne {win} est basse ({hrv_pct_p} vs ta base) : le système nerveux demande une pause.",
        "Signal à surveiller : la VFC {win} est à {hrv_pct_p} par rapport à ta base, le corps est sous pression.",
        "La VFC {win} ({hrv_pct_p}) indique que la charge pèse sur le système nerveux : prudence.",
        "Attention, {nick} : VFC {win} à {hrv_pct_p} de ta base, ton corps te parle, écoute-le.",
        "Ta VFC {win} est sous ta base ({hrv_pct_p}) : mieux vaut doser la prochaine séance.",
        "La VFC {win} à {hrv_pct_p} de ta base te dit que le système nerveux demande une pause, ce n'est pas une insulte.",
        "VFC {win} à {hrv_pct_p} de ta base : ton corps fait la grimace, écoute-le, {nick}.",
    ],
    "stress": [
        "Le stress moyen élevé ({stress}) ne facilite pas la récupération : respire, ça fait aussi partie de l'entraînement.",
        "À noter : un stress à {stress}, ça use autant qu'une séance, {nick}, pense à décompresser.",
        "Ton niveau de stress ({stress}) freine ta récupération : le repos mental compte autant que le repos physique.",
        "Le stress ({stress}) pèse sur la balance : un peu de calme et de sommeil feraient des miracles.",
        "Stress à {stress} : ton corps encaisse l'entraînement et la vie, et la vie n'est pas toujours tendre.",
        "Stress moyen à {stress} : ton corps encaisse la vie en plus de l'entraînement, double peine, {nick}.",
        "Un stress à {stress}, c'est comme une séance de plus que personne n'a programmée, respire.",
    ],
    "hrv_good": [
        "Et ta VFC {win} est au-dessus de ta base ({hrv_pct_p}) : le système nerveux te remercie.",
        "Bonus : VFC {win} à {hrv_pct_p} de ta base, le corps encaisse bien, {nick}.",
        "Cerise sur le gâteau : la VFC {win} est haute ({hrv_pct_p}), signe d'une bonne adaptation.",
        "Ta VFC {win} grimpe ({hrv_pct_p} vs ta base) : un excellent signal pour la suite.",
        "À noter : VFC {win} supérieure à ta base ({hrv_pct_p}), le corps est dans une très bonne dynamique.",
        "VFC {win} à {hrv_pct_p} de ta base : le système nerveux a l'air d'avoir pris des vacances au bord de la mer.",
        "Ta VFC {win} est supérieure à ta base ({hrv_pct_p}) : on dirait que ton corps te fait un clin d'œil, {nick}.",
    ],
    "bb_low": [
        "Et le Body Battery plafonne à {bb} : les batteries se rechargent mal, pense au sommeil.",
        "Petit bémol : Body Battery à {bb} seulement, ton corps ne se recharge pas à fond.",
        "Le Body Battery maximal à {bb} montre que la récupération nocturne est juste, {nick}.",
        "Body Battery à {bb} : les réserves d'énergie sont basses, ne tire pas trop dessus.",
        "À surveiller : Body Battery à {bb}, un chiffre qui pousse à la prudence.",
        "Body Battery à {bb} : la batterie ne se recharge qu'à moitié, c'est comme brancher un téléphone sur une pile de lampe de poche.",
        "Le Body Battery plafonne à {bb} : ton corps ne fait pas le plein, ménage-le, {nick}.",
    ],
}

# ---------------------------------------------------------------------------------------------
# 5. CLOSER : conclusion / conseil. Clé = niveau de performance (hi/mid/lo) _ état (ok/ko/neutral)
# hi : note période ≥ 14 · mid : 10 à 14 · lo : < 10  |  ok : forme optimale / assimilation · ko : fatigue / surcharge / récup incomplète
# Variables : {nick} {ins} {name} {win} {score}
# ---------------------------------------------------------------------------------------------
CLOSER = {
    "hi_ok": [
        "Bilan : bonne perf, bonne forme, le combo gagnant : continue, {nick}, mais n'oublie pas que la régularité reste la plus belle des recettes.",
        "Tu cumules niveau et fraîcheur : c'est le moment de viser plus haut, une séance de qualité te tend les bras.",
        "Perf au vert, corps au vert : fonce, mais sans te prendre pour Kipchoge, tu n'as que ses jambes dans tes rêves.",
        "Tout est réuni pour un coup d'éclat : lance-toi, {nick}, et garde un œil sur ta récupération.",
        "Tu es au sommet, alors profite, mais pas trop : on n'a jamais vu un champion s'asseoir sur ses lauriers sans les écraser.",
        "Résumé : tu es fort et frais. Le pire serait de ne rien en faire, donc va chercher un chrono.",
        "Le bilan est excellent : continue à bosser, à dormir, et à manger comme un pro, et laisse les autres gamberger.",
        "Si tout reste comme ça, tes objectifs vont trembler : garde le cap, {nick}.",
        "Bilan : tu es à ton meilleur, profites-en pour fixer un objectif un peu plus fou, {nick}.",
        "Résumé : du talent, de la fraîcheur, du sérieux : il ne manque que la ligne d'arrivée.",
    ],
    "hi_ko": [
        "Bilan : tu as le niveau, mais le corps tire la langue : lève le pied, le talent n'a jamais empêché une blessure.",
        "Belle machine, moteur qui chauffe : respecte la récupération avant de tout casser, {nick}.",
        "Tes chiffres sont superbes, mais ta fatigue dit stop : l'intelligence, c'est de savoir se reposer quand on est fort.",
        "Tu as bien bossé, trop peut-être : laisse ton corps digérer, tu perdras moins qu'en forçant.",
        "La perf est là, la fraîcheur non : ne gâche pas un si beau travail par un excès de zèle.",
        "Résumé : bravo pour le travail, maintenant dors, mange et fais une pause, ta forme te le revaudra.",
        "Excellente période, état fatigué : une journée tranquille aujourd'hui sauvera ta semaine.",
        "Le niveau est bon, le corps est juste : écoute-le, {nick}, c'est lui qui porte le dossard.",
        "Résumé : tu as tout bon sauf la fraîcheur : un jour de repos, et tu repars comme une fusée.",
        "Bilan : tu as bien bossé, tu dois bien te reposer, c'est une règle d'or, {nick}.",
    ],
    "hi_neutral": [
        "Bilan : niveau solide, état correct : continue sur cette lancée, {nick}, et vise un cran de plus la semaine prochaine.",
        "Tu es bien parti : garde la régularité et ajoute un peu de qualité pour passer au niveau supérieur.",
        "Tout va bien dans l'ensemble : le plus dur est de le répéter semaine après semaine, c'est là que se fait la différence.",
        "Résumé : du bon travail et un corps qui suit : ne change rien d'essentiel, améliore juste les détails.",
        "Tu es sur la bonne voie : sois patient, la performance aime les constants.",
        "Le bilan est positif : maintiens l'effort, soigne ton sommeil, et laisse faire le temps.",
        "Belle période, forme tranquille : ne lâche rien, et peaufine les points faibles avant la prochaine échéance.",
        "En résumé : tu avances bien, {nick}, continue à empiler les semaines sérieuses.",
        "Bilan : beau travail, corps stable : le seul danger, c'est de croire que c'est acquis.",
        "Résumé : continue sur cette base, et pense à glisser une séance de qualité de temps en temps, {nick}.",
    ],
    "mid_ok": [
        "Bilan : niveau correct, corps frais : tu as de la marge, alors utilise-la pour monter un peu en charge, {nick}.",
        "Tu es frais et tu pourrais en faire plus : la fraîcheur est faite pour être utilisée, pas pour être admirée.",
        "Corps au top, résultats moyens : le problème n'est pas le moteur, c'est le conducteur, accélère un peu.",
        "La forme est là, le volume suit à moitié : une séance de plus par semaine, et tout change.",
        "Résumé : tu as les jambes, il manque l'envie de les utiliser plus souvent, {ins} (avec tendresse).",
        "Ton corps te dit « go » : exauce-le, il ne demande qu'à bosser un peu plus.",
        "Frais, disponible, correct : le plus dur est fait, il ne reste qu'à décider d'y aller plus fort.",
        "Tu as le feu vert physique : transforme-le en séances de qualité cette semaine.",
        "Bilan : tu es frais, donc plus d'excuse : profite-en pour envoyer une séance de qualité, {nick}.",
        "Résumé : un corps prêt et un niveau honnête : il ne manque qu'une bonne séance pour transformer l'essai.",
    ],
    "mid_ko": [
        "Bilan : niveau moyen et corps fatigué : ne force pas, la récupération est ta meilleure séance du jour.",
        "Ni brillant, ni en forme : pas de panique, un peu de repos et de régularité suffisent à relancer la machine, {nick}.",
        "Tu es dans le tiède et le fatigué : lève le pied aujourd'hui, mieux vaut redémarrer frais que s'obstiner.",
        "Résumé : ce n'est pas le moment de forcer, laisse le corps digérer avant de reprendre sérieusement.",
        "Le niveau est correct, la fraîcheur non : dors, mange, et reprends demain avec plus de punch.",
        "Pas la période de l'année : accorde-toi une pause, tu reviendras plus efficace et moins grincheux.",
        "Corps fatigué, résultats moyens : le repos fera plus pour toi que n'importe quelle séance héroïque.",
        "Prends soin de toi aujourd'hui, {nick} : la progression viendra, mais elle ne se force pas.",
        "Bilan : niveau moyen et fatigue : respecte la récupération, tu en tireras plus de profit que de n'importe quelle séance, {nick}.",
        "Résumé : pas le moment de tout donner : redescends d'un cran, dors, et repars demain.",
    ],
    "mid_neutral": [
        "Bilan : ni mauvais, ni excellent : un peu plus de régularité, et tu passes dans la catégorie supérieure, {nick}.",
        "Tu es dans la moyenne : pour en sortir, ajoute une séance de qualité par semaine et tiens-t'y.",
        "Résumé : une base saine, une marge de progression évidente : à toi de choisir ce que tu en fais.",
        "Le bilan est honnête : continue, et vise un pilier à améliorer à la fois, sans te disperser.",
        "Ni crise, ni exploit : la progression est lente mais réelle, et c'est comme ça qu'on prépare un marathon.",
        "Tu avances, doucement : accélère un peu, et tes résultats suivront, sans effort héroïque.",
        "Moyenne correcte, marge énorme : il ne manque qu'un peu de rigueur pour décoller, {nick}.",
        "Bilan neutre : change un petit truc cette semaine (une sortie, un sommeil, une séance) et regarde ce qui bouge.",
        "Bilan : tu es dans le juste milieu : un petit coup de collier, et le tableau change de couleur, {nick}.",
        "Résumé : une base saine, de la marge : choisis un seul point à améliorer cette semaine.",
    ],
    "lo_ok": [
        "Bilan : performance faible, mais corps frais : excuse prise en compte, rendez-vous demain à la première heure avec tes baskets, {ins}.",
        "Tu es reposé comme un loir et tu n'as rien fait : la forme est là, il ne manque que toi.",
        "Les voyants sont verts, ta motivation en grève : il est temps de lacer les chaussures et d'aller bosser, {nick}.",
        "Frais, disponible et inactif : le pire des trois, le seul que tu peux corriger dès demain matin.",
        "Résumé : tu n'as aucune excuse physique, {ins}, alors ce soir tu prépares ton sac et demain tu sors.",
        "Tu as le corps pour t'entraîner et la tête qui hésite : aujourd'hui, c'est la tête qui perd, pas les jambes.",
        "Ton corps est prêt, ton plan d'entraînement aussi : il ne manque que ta présence sur le bitume, {nick}.",
        "Pas de fatigue, pas d'excuse : une sortie facile ce soir, et on remet les compteurs à zéro.",
        "Bilan : aucune excuse physique, {ins} : sors tes baskets ce soir, ton corps t'attend de pied ferme.",
        "Résumé : le corps est prêt, l'agenda doit l'être aussi : trois séances cette semaine, {nick}.",
    ],
    "lo_ko": [
        "Bilan : peu d'entraînement et déjà fatigué ? Il y a un souci : dors, mange sainement, et reviens progressivement, {nick}.",
        "Niveau bas et corps fatigué : ne compense pas par une séance héroïque, reprends doucement, c'est comme ça qu'on repart.",
        "Les chiffres sont faibles et la forme aussi : commence par du sommeil et de la douceur, la performance viendra après.",
        "Résumé : ce n'est pas le moment de forcer, mais de reconstruire : sommeil, repas corrects, petites sorties faciles.",
        "Rien ne sert de se punir : une semaine de remise en route calme vaudra mieux qu'un coup d'éclat suivi d'une blessure.",
        "Corps fatigué, entraînement léger : tu repars de loin, alors avance pas à pas, sans chercher à rattraper d'un coup.",
        "Le plus urgent, c'est de récupérer : le programme viendra ensuite, doucement, régulièrement.",
        "Bilan : fatigue et manque de séances, un duo pas très drôle : je te laisse dormir et on s'y remet demain, {nick}.",
        "Bilan : repos d'abord, reprise ensuite : on ne bâtit rien de solide sur un corps épuisé, {nick}.",
        "Résumé : fatigue et peu d'entraînement : un cocktail à corriger par du sommeil, puis des petites sorties faciles.",
    ],
    "lo_neutral": [
        "Bilan : il faut remettre le couvert, {ins} : trois séances cette semaine, point final, on en reparle dimanche.",
        "Niveau faible, état correct : plus aucune excuse, programme trois sorties sur ton agenda et tiens-les.",
        "Résumé : ta forme dort, ton objectif t'attend : réveille les deux avec une sortie facile ce soir, {nick}.",
        "Tu as de la marge pour t'améliorer, énormément : commence par une séance, puis une autre, et tout s'enclenche.",
        "Le bilan est faible, mais le potentiel est là : il dort, il suffit de le réveiller par la régularité, {ins}.",
        "Pas de panique : tu repars de peu, mais chaque séance compte : la première est toujours la plus dure, la suivante coule de source.",
        "Entraînement insuffisant : programme, motivation, baskets, tu as tout, il manque juste le déclic, {nick}.",
        "Bilan : c'est le moment de t'y remettre sérieusement : un plan simple, trois séances par semaine, et on verra.",
        "Bilan : trois séances cette semaine, {ins}, pas une de moins : on se retrouve dimanche pour le contrôle.",
        "Résumé : tout est possible, rien n'est fait : la première séance est la plus belle, {nick}.",
    ],
}

# ---------------------------------------------------------------------------------------------
# 6. TAIL : tendance vs période précédente OU compte à rebours de la prochaine course
# TREND variables : {nick} {win} {dkm} · COUNT variables : {nick} {rlabel} {days}
# ---------------------------------------------------------------------------------------------
TREND = {
    "up": [
        "Et ton volume de course est en hausse de {dkm} % par rapport à la période précédente : continue, {nick}, mais avec progressivité.",
        "Petit plus : {dkm} % de kilomètres en plus qu'avant, la progression est visible, garde cette dynamique.",
        "À noter : tu cours {dkm} % de plus que la période précédente, bravo pour l'effort, sans te blesser s'il te plaît.",
        "Le volume course grimpe de {dkm} % : ça se voit, ça se sent, et ça va se payer en chronos.",
        "Bonne nouvelle : {dkm} % de kilomètres en plus, c'est ainsi qu'on construit une fondation solide.",
        "Tu cours {dkm} % de plus qu'avant : tes jambes vont devoir s'y habituer, et tes chaussures aussi.",
        "Ton volume de course gagne {dkm} % sur la période précédente : on dirait que quelqu'un a trouvé ses baskets, {nick}.",
        "{dkm} % de kilomètres en plus qu'avant : tes chaussures protestent, tes jambes applaudissent.",
    ],
    "down": [
        "Et ton volume de course chute de {dkm} % par rapport à la période précédente : un coup de mou ou un coup de flemme, {nick} ?",
        "Attention : {dkm} % de kilomètres en moins qu'avant, la dynamique descend, remonte-la avant de perdre le fil.",
        "À noter : tu cours {dkm} % de moins que la période précédente, et ça se verra sur le chrono si ça dure.",
        "Le volume course recule de {dkm} % : si c'est voulu, bien joué, sinon c'est un signal d'alerte, {ins}.",
        "Mauvaise nouvelle : {dkm} % de kilomètres en moins, les jambes aussi vont s'en souvenir.",
        "Tu as levé le pied de {dkm} % par rapport à avant : décide si c'est de la récupération ou de la paresse.",
        "Ton volume de course recule de {dkm} % : tes baskets ont repris racine dans le placard, {ins}.",
        "{dkm} % de kilomètres en moins qu'avant : ça glisse doucement vers le canapé, redresse la barre.",
    ],
    "flat": [
        "Et ton volume de course est stable par rapport à la période précédente : de la régularité, c'est déjà beaucoup.",
        "À noter : tu cours à peu près autant qu'avant, ce n'est pas mal, mais pour progresser, il faut un peu plus.",
        "Le volume course est stable : une base solide, il te reste à choisir le moment d'augmenter doucement.",
        "Tendance neutre : tu tiens le rythme de la période précédente, {nick}, sans l'améliorer ni le dégrader.",
        "Même volume qu'avant : constance respectable, mais l'objectif demande un petit coup de pouce.",
        "Pas de changement de volume : c'est stable, et c'est une qualité tant qu'on n'oublie pas de progresser un jour.",
        "Volume de course stable : même rythme que la période précédente, ni progression, ni dégringolade, ça sent la routine, {nick}.",
        "Aucune variation notable du volume de course : tu es le roi du statu quo, {nick}.",
    ],
}
COUNT = {
    "taper": [
        "{rlabel} dans {days} jours : c'est l'heure de l'affûtage, pas de folie, les jambes doivent arriver fraîches, {nick}.",
        "Plus que {days} jours avant {rlabel} : on ne gagne plus de forme maintenant, on évite juste de la perdre.",
        "{rlabel} approche ({days} jours) : sommeil, repas, calme, le plus dur est fait.",
        "Dans {days} jours, {rlabel} : arrête de te mettre la pression, le travail est dans les jambes, fais confiance.",
        "Encore {days} jours avant {rlabel} : zéro blessure, zéro folie, et tu arrives en pleine forme.",
        "Encore {days} jours avant {rlabel} : le plus gros du travail est fait, il n'y a plus qu'à faire attention à ne pas se prendre un pied dans un trottoir, {nick}.",
        "{rlabel} dans {days} jours : mange bien, dors bien, et ne fais surtout pas l'imbécile, {nick}.",
    ],
    "near": [
        "{rlabel} dans {days} jours : il reste quelques semaines pour peaufiner, alors chaque séance compte, {nick}.",
        "Plus que {days} jours avant {rlabel} : la préparation entre dans sa phase décisive, pas de relâchement.",
        "{rlabel} approche ({days} jours) : c'est le moment de préciser l'allure cible dans les séances clés.",
        "Dans {days} jours, {rlabel} : le gros du travail se joue maintenant, c'est maintenant ou jamais.",
        "Encore {days} jours avant {rlabel} : les semaines passent vite, les séances sautées, elles, se paient cher.",
        "{rlabel} dans {days} jours : la ligne d'arrivée se rapproche, il est temps de passer du « on verra » au « on y va ».",
        "Dans {days} jours, {rlabel} : ton futur toi te regarde, souris-lui, {nick}.",
    ],
    "mid": [
        "{rlabel} dans {days} jours : il y a du temps, mais pas de quoi flâner, chaque semaine compte, {nick}.",
        "Plus que {days} jours avant {rlabel} : c'est la période de construction, le moment d'accumuler les kilomètres.",
        "{rlabel} approche ({days} jours) : le plus dur, c'est de rester régulier quand l'échéance semble lointaine.",
        "Dans {days} jours, {rlabel} : une préparation se construit dès aujourd'hui, pas la veille.",
        "Encore {days} jours avant {rlabel} : de quoi bien faire les choses, à condition de s'y mettre pour de bon.",
        "{rlabel} dans {days} jours : tu as le temps de bâtir quelque chose, pas celui de procrastiner, {nick}.",
        "Plus que {days} jours avant {rlabel} : le calendrier avance, ton entraînement doit suivre.",
    ],
    "far": [
        "{rlabel} est dans {days} jours : il reste de la marge, mais la forme de demain se construit aujourd'hui, {nick}.",
        "Plus que {days} jours avant {rlabel} : tu as le temps de progresser, mais pas celui de procrastiner.",
        "{rlabel} dans {days} jours : c'est loin, c'est vrai, et c'est exactement ce qui rend les excuses faciles.",
        "Dans {days} jours, {rlabel} : le temps joue pour toi, pourvu que tu t'en serves.",
        "Encore {days} jours avant {rlabel} : une longue route, qui commence par la séance du jour.",
        "{rlabel} est à {days} jours : les excuses ont de la place, les résultats moins, {nick}.",
        "Dans {days} jours, {rlabel} : une longue route, mais chaque séance fait un pas de plus, {nick}.",
    ],
}


# ---------------------------------------------------------------------------------------------
# 0. GREET : salutation en tête de paragraphe, selon le contexte (ko = état physique mauvais, lo / mid / hi = niveau de la période)
# Variables : {nick} {ins} {name} {win}
# ---------------------------------------------------------------------------------------------
GREET = {
    "lo": [
        "Salut {ins} !", "Alors {ins}, on est vivant ?", "Coucou {name}… ou ce qu'il en reste.", "Salut {nick}, enfin, façon de parler.",
        "Hého {ins}, réveille-toi !", "Bonjour {name}, ta montre a des nouvelles, et ce n'est pas joli.", "Ciao {ins} !", "Holà {nick}, tu n'as pas de fièvre sportive, ça se voit.",
        "Salut gros lard !", "Oh, {name} ! On t'a cherché sur les parcours, personne ne t'a vu.", "Coucou {ins}, prêt pour la vérité ?", "Alors {nick}, toujours en vacances ?",
        "Bonjour {ins}, assieds-toi (tu es déjà assis, je sais).", "Salut {nick}, le bulletin est arrivé, et il ne sent pas la lavande.",
        "Alors {ins}, prêt à regarder la vérité en face ?",
        "Salut {nick}, ta montre a des nouvelles, et elles sentent la poussière.",
        "Hola {ins} !",
        "Coucou {ins}, on se réveille ?",
    ],
    "mid": [
        "Salut {nick} !", "Coucou {name} !", "Ciao {nick} !", "Holà {nick}, prêt pour ton bulletin ?", "Hello {name}, ta montre a parlé.",
        "Alors {nick}, quoi de beau ?", "Bonjour {name}, voici ce que dit ta montre.", "Hé {nick}, installe-toi, j'ai des chiffres.",
        "Salut le sang, café en main ?", "Yo {nick} !", "Bien le bonjour {name} !", "Oh, {nick}, on fait le point ?", "Coucou {nick}, petite revue de tes performances.",
        "Salut {name}, ton coach de poche est de retour.",
        "Hey {nick}, voyons ce que ta montre a dans le ventre.",
        "Salut {name} ! Un petit café et on regarde ça.",
        "Ciao {nick}, c'est l'heure du bulletin.",
        "Bonjour {name}, ta montre a bossé, voici le compte rendu.",
    ],
    "hi": [
        "Salut {nick} !", "Coucou {name}, tu vas aimer ça !", "Holà {nick}, du lourd aujourd'hui !", "Ciao {nick} !", "Salut le sang, assieds-toi, ça vaut le détour.",
        "Hello {name}, tu peux sortir le petit doigt de la fierté.", "Bonjour {nick}, la montre a de bonnes nouvelles !", "Hé {nick}, je prépare les applaudissements.",
        "Yo {nick}, ton dossier est une œuvre d'art.", "Salut {name}, j'ai du bon et du très bon.", "Coucou {nick}, rien que des sourires dans ce rapport.",
        "Oh {name}, on se tient droit pour lire ça !", "Bonjour champion, bonjour !", "Bienvenue {nick}, le tapis rouge est dans ton salon.",
        "Salut {nick}, installe-toi, c'est du bon !",
        "Hola {name}, ça va chauffer, dans le bon sens !",
        "Hey {nick}, sors le tapis rouge, le rapport est flatteur.",
        "Coucou {name}, tu vas sourire !",
    ],
    "ko": [
        "Salut {nick}, comment va le corps ?", "Coucou {name}, on s'écoute un peu aujourd'hui, d'accord ?", "Holà {nick}, tu as une petite mine sur les graphiques.",
        "Hello {name}, ta montre a des nouvelles, et elles demandent de la douceur.", "Salut {nick}, aujourd'hui c'est le coach bienveillant qui te parle.",
        "Ciao {nick}, on lève le pied et on lit ça tranquillement.", "Bonjour {name}, respire, ton corps a des choses à te dire.", "Hé {nick}, fais une pause, ça se lit mieux assis.",
        "Salut {name}, prends un thé, voici le bilan.", "Coucou {nick}, ton corps parle, prends deux minutes pour l'écouter.",
        "Salut {nick}, on prend soin de soi aujourd'hui ?",
        "Hola {name}, respire, on regarde tout ça sans se presser.",
        "Coucou {nick}, ton corps a besoin d'un peu de douceur, voici pourquoi.",
        "Bonjour {name}, le coach est en mode câlin aujourd'hui.",
    ],
}

# ---------------------------------------------------------------------------------------------
# 0 bis. TRANS : petites transitions humoristiques entre les blocs (une fois sur trois environ, jamais d'insulte)
# Variables : {nick} {name} {win}
# ---------------------------------------------------------------------------------------------
TRANS = {
    "pilier": [
        "Passons aux piliers.", "Direction l'analyse détaillée.", "Les cinq piliers maintenant, accroche-toi.", "Regardons sous le capot.",
        "Analyse technique, sortons la loupe.", "Entrons dans le dur, {nick}.", "Voyons ce que disent les piliers.", "Côté fondations, voici le topo.",
    ],
    "goal": [
        "Et la course dans tout ça ?", "Parlons objectif.", "Question chrono maintenant.", "Maintenant, le moment de vérité : le chrono.",
        "Sortons la calculette de course.", "Et côté dossard ?", "Gardons un œil sur la ligne d'arrivée.", "Passons à ce qui compte vraiment : l'objectif.",
    ],
    "state": [
        "Et ton corps, il en dit quoi ?", "Côté carrosserie maintenant.", "Prenons le pouls du moment.", "Vérifions le moteur.",
        "Un petit check-up du corps.", "Regard sur ton état de forme.", "Passons à la santé.", "Que dit le tableau de bord physiologique ?",
    ],
    "closer": [
        "Pour conclure, sans jargon.", "En résumé, {nick}.", "La phrase à retenir, la voici.", "Allez, le mot de la fin.",
        "Ce qu'il faut retenir.", "Pour finir, en toute franchise.", "Bref, voici l'essentiel.", "Conclusion de ton coach de poche.",
    ],
}

# ---------------------------------------------------------------------------------------------
# 0 ter. JOKE : une blague ou un trait d'humour avant la conclusion, selon performance (lo/mid/hi) x état (ok/ko/neutral)
# Piques autorisées en lo ; humour bienveillant partout ailleurs. Variables : {nick} {ins} {name} {win} {score}
# ---------------------------------------------------------------------------------------------
JOKE = {
    "lo_ok": [
        "Ton corps est reposé comme un chat au soleil, le seul sport que tu pratiques en ce moment.",
        "Tu as les jambes d'un athlète et l'emploi du temps d'un moine, mais pas celui qui court.",
        "Un jour, tes baskets te demanderont la garde alternée du canapé, {ins}.",
        "Tu n'as pas de blessure, tu n'as pas de fatigue, tu n'as que de l'inertie : un véritable record du monde.",
        "Ta montre commence à écrire des romans tellement elle s'ennuie.",
        "Si le farniente était un sport, tu aurais déjà ta licence, ton maillot et un sponsor.",
        "Tes jambes attendent depuis des jours qu'on les invite à danser : ne les fais pas poireauter.",
        "Même ton réveil a arrêté de sonner pour les séances, il a compris.",
        "Ton corps est une Ferrari au garage : superbe, brillante, immobile, et un peu triste.",
        "Si les excuses se muscaient, tu aurais des cuisses de sprinteur, {ins}.",
        "Ton repos est parfait, c'est donc le moment idéal pour mettre tes jambes à l'épreuve.",
    ],
    "lo_ko": [
        "Peu de séances et déjà cuit : il y a un mystère, et ce n'est pas le sport qui en est la cause.",
        "Ton corps est fatigué sans avoir bossé : il fait grève par solidarité avec ton emploi du temps.",
        "Si ta fatigue était une séance, elle compterait déjà dans ta charge hebdomadaire.",
        "Pas besoin d'en faire trop pour être cuit : le sommeil et le stress font parfois mieux que l'entraînement.",
        "Ton plan est en vacances, ton corps en arrêt maladie : on se retrouve quand les deux rentrent.",
        "C'est rare : tu parviens à être à plat sans avoir fait de sport, je te décerne la médaille de l'économie d'effort.",
        "Allez, pas de panique : reprends en douceur, la machine a juste besoin d'un redémarrage.",
        "Un corps fatigué et un agenda vide : on va régler ça par ordre d'importance, sommeil d'abord.",
        "Peu d'entraînement, beaucoup de fatigue : la vie fait le sport à ta place, c'est ironique.",
        "Ton corps te dit « stop » alors que tu n'as même pas commencé : il est précoce.",
        "Ta fatigue n'est pas une excuse, c'est une information : on la soigne, puis on repart en douceur.",
    ],
    "lo_neutral": [
        "À ce rythme, ton marathon aura lieu dans un autre univers, probablement celui où tu t'entraînes.",
        "Ta forme n'est pas perdue, elle est juste en pause longue durée, comme ta série préférée.",
        "On ne te demande pas de courir comme un guépard, juste comme quelqu'un qui n'a pas oublié ses chaussures.",
        "Tu as le talent, l'objectif et le matériel : il ne manque que les kilomètres, trois fois rien.",
        "Ton Garmin commence à se demander si tu n'es pas parti en retraite anticipée.",
        "Ton objectif attend dans le couloir depuis des semaines, avec un petit panneau « je suis toujours là ».",
        "Un petit footing aujourd'hui, et la courbe repart : ce n'est pas de la science, c'est de la persévérance.",
        "Tu veux qu'on organise un rendez-vous avec ton moi sportif ? Il a l'air d'avoir été injoignable.",
        "Ton objectif te regarde dans les yeux, et toi tu regardes ailleurs : un peu de courage, {ins}.",
        "Il ne s'agit pas de courir un marathon demain, juste une sortie ce soir : la différence est énorme.",
        "Ton niveau est comme un dossier oublié dans un tiroir : il suffit de l'ouvrir.",
    ],
    "mid_ok": [
        "Tu es frais, correct, régulier : le profil de l'athlète qui pourrait faire un truc énorme s'il cessait d'être raisonnable.",
        "Pas mal du tout, même si tes jambes ont encore la chance de dormir sur leurs deux oreilles.",
        "Tes chiffres sont comme un bon café : corrects, chauds, mais ils attendent une dose de sucre pour devenir exceptionnels.",
        "Le corps est prêt, la tête hésite entre « gagner » et « garder des forces pour demain » : tranche, {nick}.",
        "Avec cette fraîcheur, tu pourrais courir jusqu'au bout de l'horizon, ou au moins jusqu'à la boulangerie.",
        "Tu es dans la zone « pas mal du tout » : à un cheveu de « bravo », à un rien de « en progrès ».",
        "On sent que tu as du moteur en réserve : appuie un peu sur l'accélérateur, il ne mord pas.",
        "Le plan est bon, l'athlète est frais : si ça rate, ce sera la faute à pas de chance, jamais à pas de jambes.",
        "Frais, correct, un peu sage : tu pourrais allumer un petit feu sans mettre le feu à la baraque.",
        "Ton corps est un diesel bien réglé : il n'attend que ton geste pour monter en régime.",
        "Il y a de l'énergie dans ton réservoir, utilise-la avant qu'elle ne s'évapore.",
    ],
    "mid_ko": [
        "Tu es tiède et fatigué : c'est le profil exact d'un café oublié sur un coin de bureau, mais on peut te réchauffer.",
        "Même Superman prend des jours de repos : et lui au moins a une cape pour se consoler.",
        "Le corps tire la langue, la raison a raison : ce soir, pyjama et couette, prescription de ton coach.",
        "Tu es dans le « pas terrible et un peu cuit » : le canapé est autorisé aujourd'hui, mais pas de pétition.",
        "Même les meilleurs marathoniens dorment : c'est même ce qu'ils font de mieux (après courir, bien sûr).",
        "Ton corps te fait une petite crise de nerfs, c'est normal : offre-lui un jour tranquille et il revient en héros.",
        "Un marathon se prépare aussi avec des siestes : ne culpabilise pas, le repos est une séance qui compte.",
        "Le moteur a chauffé, on laisse refroidir : ça n'a rien de honteux, juste de la mécanique.",
        "Tu es fatigué et moyen, mais le mot « moyen » n'a jamais empêché de rebondir.",
        "Même les machines ont besoin d'un coup de graisse : ce soir, ce sera du sommeil.",
        "Pas besoin de héros aujourd'hui : la sieste est un entraînement qui ne dit pas son nom.",
    ],
    "mid_neutral": [
        "Tu es dans le vrai milieu du peloton : ni lanterne rouge, ni maillot jaune, mais avec un beau vélo de rechange.",
        "Ni feu d'artifice ni bougie qui fond : tu es comme une bonne soupe, correct, constant, pas encore gastronomique.",
        "Ton niveau est celui d'un bon compagnon de sortie : fiable, régulier, mais pas encore le gars qui fait peur sur les photos.",
        "Un petit coup d'accélérateur et tu quittes la case « sympa » pour la case « sérieux » : c'est tout près.",
        "Pas de drame, pas d'exploit : c'est le genre de semaine qu'on oublie, mais qui construit les grandes saisons.",
        "Les chiffres te regardent d'un air de dire « on t'attend, mais on a le temps ».",
        "Tu cumules les petites victoires : elles ne font pas de bruit, mais elles font des marathoniens.",
        "À ce niveau-là, le moindre petit effort supplémentaire se verra immédiatement, c'est le côté agréable d'être au milieu.",
        "Tu es en rythme de croisière, le pilote automatique ronronne : il suffit de reprendre la main pour grimper.",
        "Rien de dramatique, rien d'éclatant : le terrain parfait pour poser les bases d'une grosse saison.",
        "Tu es dans ce délicieux entre-deux où chaque petit effort supplémentaire se voit.",
    ],
    "hi_ok": [
        "Fraîcheur maximale, niveau excellent : c'est le moment de ne pas faire n'importe quoi, ou alors de faire n'importe quoi très vite.",
        "Si tu continues, tes chaussures vont demander un agent.",
        "Tu es dans une forme à rendre jaloux ton propre arbre généalogique.",
        "Tout est vert : on dirait que ta montre a cuisiné pour toi un menu quatre étoiles.",
        "À ce rythme, il va falloir élargir tes étagères pour y poser les médailles.",
        "Ton corps a la fraîcheur d'une salade bio et la puissance d'un moteur diesel, quelle combinaison.",
        "Les chronos te regardent avec respect, les chaussures avec adoration, et ton canapé avec une immense tristesse.",
        "On dit que la chance sourit aux audacieux, mais là, c'est surtout aux gens qui se couchent tôt et qui s'entraînent bien.",
        "À ce niveau-là, ton prochain adversaire devrait déclarer forfait par politesse.",
        "Un niveau qui monte, un corps qui suit : si ça continue, on va devoir recompter les médailles.",
        "Tout est au vert, le soleil brille, et même ta montre te fait un clin d'œil.",
    ],
    "hi_ko": [
        "Niveau très haut, corps un peu cuit : l'athlète qui a trop bien fait son boulot, un classique.",
        "Même les fusées ont besoin d'un peu de carburant : refais le plein avant le prochain décollage.",
        "Tu as trop bien bossé : une vraie faute professionnelle, à corriger par du repos.",
        "Un champion qui ne sait pas se reposer est un champion qui sera bientôt en kiné : écoute ton corps, {nick}.",
        "Beau tableau de chasse, belle fatigue : accorde-toi un jour de répit avant que les jambes ne t'envoient un courrier recommandé.",
        "Le talent, ça va, ça vient, la récupération, ça se mérite : passe à la caisse du repos.",
        "Tes chiffres ont l'air d'un coureur qui a mangé trop de courbatures : on le met au repos un peu.",
        "Tu es au top et en bout de souffle, c'est la définition d'une préparation sérieuse : maintenant, on souffle un peu.",
        "Tu as fait du très bon travail, et ton corps te présente la facture : paie-la en sommeil.",
        "Le niveau est haut, la fatigue aussi : prends un jour de repos, tes records ne s'envoleront pas.",
        "Plus on monte haut, plus il faut de bons crampons : et ce soir tes crampons s'appellent repos.",
    ],
    "hi_neutral": [
        "Franchement, si tu continues comme ça, je vais devoir inventer de nouveaux compliments.",
        "Ton niveau est celui d'un athlète qui s'entraîne vraiment : c'est rare, c'est beau, c'est un peu agaçant pour le canapé.",
        "Tes chiffres sont jolis, ta régularité est jolie, tout est joli : c'est presque suspect.",
        "Ton dossier est tellement bon que je me suis cru obligé de mettre des lunettes de soleil.",
        "Si on avait un trophée pour les semaines propres, tu serais déjà sur le podium.",
        "On dirait que tu as lu le manuel d'entraînement en entier, et même les notes de bas de page.",
        "Voilà ce que ça donne quand on s'y met pour de vrai : même les statistiques sourient.",
        "Tu n'as pas la grosse tête, mais tes mollets, eux, ont clairement pris du galon.",
        "Ton niveau est tel que même tes détracteurs imaginaires sont en train d'applaudir.",
        "Si la régularité avait un visage, ce serait le tien, avec un petit sourire de satisfaction.",
        "Ça se voit que tu t'es mis au sérieux : les chiffres ont l'air content.",
    ],
}


# ---------------------------------------------------------------------------------------------
# STALE : la montre n'a plus donné de nouvelles (données datées). Variables : {nick} {ins} {name} {win} {sdays} {sdate}
# ---------------------------------------------------------------------------------------------
STALE = {
    "warn": [
        "Petit souci d'intendance : ta montre n'a plus donné de nouvelles depuis {sdays} jours, ce que tu lis a donc un peu de retard sur ta vraie forme.",
        "Information importante : les dernières données remontent au {sdate}, je commente donc avec un léger décalage horaire, {nick}.",
        "Ta montre fait la tête : plus de données fraîches depuis {sdays} jours, prends donc mes remarques avec une pincée de sel.",
        "Alerte logistique : les derniers chiffres datent du {sdate}, le diagnostic est donc celui d'il y a quelques jours, pas de ce matin.",
        "Je travaille avec des données un peu rassises ({sdays} jours), alors pas de panique si ça ne colle pas tout à fait à tes sensations.",
        "La synchronisation a pris des vacances : dernières nouvelles de ta montre le {sdate}, vérifie qu'elle est bien chargée et connectée, {nick}.",
        "Mes chiffres ont du retard sur ta vie : la dernière mesure date de {sdays} jours, le temps de rebrancher la montre.",
        "Je te parle avec des infos qui datent un peu : la synchro est incomplète, donc mes conclusions sont à lire avec prudence.",
    ],
    "alert": [
        "Alerte rouge : ta montre ne donne plus signe de vie depuis {sdays} jours, ce que je dis est donc périmé, {nick}, vérifie vite la synchro.",
        "Gros trou dans la raquette : dernière donnée au {sdate}, je commente donc dans le brouillard, et ce n'est pas la meilleure situation pour juger ta forme.",
        "Ta montre est en grève depuis {sdays} jours : tant qu'elle n'est pas rebranchée, prends tout ce qui suit comme une vieille photo.",
        "Les données sont périmées ({sdays} jours) : mon analyse est en mode archéologie, il faut réparer la synchro avant de me croire.",
        "Houston, on a un problème : plus de données fraîches depuis le {sdate}, relance la synchro Garmin et reviens me voir.",
        "Sans données récentes, je suis comme un GPS sans signal : je continue de parler, mais ne me suis pas aveuglément, {nick}.",
        "Mes chiffres sont trop vieux pour être honnêtes ({sdays} jours) : vérifie la connexion de la montre et la session Garmin.",
        "Diagnostic de l'état du système : pas de données récentes, donc pas de diagnostic fiable de ta forme, la montre doit se reconnecter.",
    ],
}

# ---------------------------------------------------------------------------------------------
# ASIDE : petit commentaire entre parenthèses ajouté (une fois sur deux, 2 maximum par paragraphe) en fin de phrase d'analyse.
# Clé = lo / mid / hi / ko (état physique mauvais : jamais d'insulte). Variables : {nick} {ins} {name} {win}
# ---------------------------------------------------------------------------------------------
ASIDE = {
    "lo": [
        "oui, je te regarde, {ins}", "ta montre en tremble encore", "le canapé n'est pas un sport olympique", "ton futur toi prend des notes",
        "ton plan d'entraînement sanglote doucement", "c'est un constat, pas une insulte, {ins}", "ton moi de l'an dernier a honte", "pas de panique, mais un peu quand même",
        "même ton ombre te trouve calme", "les baskets, c'est comme les plantes : ça meurt sans attention", "tu as le droit de t'y remettre dès ce soir", "ton coach de poche garde espoir",
        "l'inertie est un puissant adversaire, {nick}", "ça ne se fera pas tout seul, {ins}", "ton agenda cherche encore une séance", "la bonne nouvelle : on ne peut que remonter",
        "ta gourde s'ennuie", "tes chaussettes de sport ont pris du repos, elles aussi", "je dis ça avec tendresse, {ins}", "ton réveil regrette les séances matinales",
    ],
    "mid": [
        "ni honte, ni gloire, {nick}", "c'est solide, sans être spectaculaire", "ta marge de progression est une mine d'or", "tes baskets te regardent avec confiance",
        "on est dans le milieu de peloton, avec vue sur la tête", "la régularité fera le reste", "pas mal, pas mal du tout", "un petit effort et ça s'envole",
        "le bon moment pour mettre un cran de plus", "tu fais mieux que la moyenne des gens qui promettent de s'y mettre", "ta montre hoche la tête", "ton futur toi dit « continue »",
        "il suffit d'un déclic, {nick}", "pas de quoi crier, assez pour sourire", "du travail propre, comme à l'atelier", "ça avance, doucement mais sûrement",
        "personne ne gagne un marathon en un jour", "c'est dans les détails que ça se joue", "la constance est ta meilleure amie", "tu tiens le bon bout",
    ],
    "hi": [
        "ta mère serait fière", "applaudissements du public imaginaire", "les concurrents prennent des notes en tremblant", "même ton Garmin sourit",
        "ça sent la médaille, {nick}", "je ne m'attendais pas à te faire autant de compliments", "tes chaussures demandent un agent", "voilà du travail d'orfèvre",
        "la fierté de ton coach de poche est immense", "ça mérite un petit cri de joie", "tu fais honneur à tes baskets", "du grand art, {nick}",
        "les chiffres sont à tes pieds", "si ça continue, je ne saurai plus quoi te reprocher", "j'ai cherché un défaut, je suis encore en train de chercher", "le peloton te regarde partir",
        "ta fiche sent la réussite", "bravo, et ce n'est pas ironique", "c'est digne d'un panneau « chapeau »", "ça, c'est du sérieux",
    ],
    "ko": [
        "ton corps te dit merci d'avance", "le repos fait partie du programme, {nick}", "même les héros dorment", "ce n'est pas de la faiblesse, c'est de la stratégie",
        "ta couette te tend les bras", "on lève le pied, on ne lève pas le drapeau blanc", "demain sera un autre jour", "la récupération est une séance comme une autre",
        "ton corps a ses raisons que la montre connaît", "un peu de douceur ne fait jamais de mal, {nick}", "pas besoin de faire le héros", "ton futur toi te remerciera",
        "dors, hydrate-toi, recommence", "le rebond sera plus fort après une vraie pause", "on se ménage pour mieux repartir", "la sagesse, c'est aussi savoir s'arrêter",
        "ce n'est qu'un petit contretemps", "même Kipchoge a des jours sans", "un thé, une sieste, et ça repart", "tout va bien se passer, {nick}",
    ],
}

# Variables autorisées par banque (vérifié par test_analysis.py)
_COMMON = {"nick", "ins", "name", "win"}
ALLOWED = {
    "GREET": _COMMON, "TRANS": _COMMON, "STALE": _COMMON | {"sdays", "sdate"}, "ASIDE": _COMMON, "JOKE": _COMMON | {"score"},
    "OPENER": _COMMON | {"score"},
    "STRONG": _COMMON | {"sc", "glabel", "gret", "gtarget", "kmw", "long_km", "acwr", "sleep_h", "hrv_pct", "sw", "cw"},
    "WEAK": _COMMON | {"sc", "glabel", "gret", "gtarget", "kmw", "long_km", "acwr", "sleep_h", "hrv_pct", "sw", "cw"},
    "BALANCED": _COMMON,
    "BEST_LOW": _COMMON | {"pname", "sc"},
    "WORST_HIGH": _COMMON | {"pname", "sc"},
    "GOAL": _COMMON | {"glabel", "gret", "gtarget", "ggap", "gpct"},
    "STATE": _COMMON | {"strain", "faf", "hrv_pct", "sleep_score", "sleep_h", "acwr", "bb"},
    "MOD": _COMMON | {"sleep_debt", "hrv_pct_p", "stress", "bb"},
    "CLOSER": _COMMON | {"score"},
    "TREND": _COMMON | {"dkm"},
    "COUNT": _COMMON | {"rlabel", "days"},
}
# Profils dont l'état est mauvais : aucune insulte autorisée dans ces blocs
NO_INSULT_PROFILES = {"fatigue_aiguë", "surcharge_musculaire", "récupération_incomplète"}
STATE_OK = {"forme_optimale", "assimilation_réussie"}
STATE_KO = {"fatigue_aiguë", "surcharge_musculaire", "récupération_incomplète"}


# ---------------------------------------------------------------------------------------------
# MOTEUR
# ---------------------------------------------------------------------------------------------
def _h(date_str, salt):
    return int(hashlib.md5((date_str + salt).encode("utf-8")).hexdigest(), 16)


def _fields(tpl):
    return {f for _, f, _, _ in string.Formatter().parse(tpl) if f}


def _cap(s):
    return s[:1].upper() + s[1:] if s[:1].isalpha() else s


def _ord(date_str):
    try:
        return date.fromisoformat(str(date_str)[:10]).toordinal()
    except ValueError:
        return _h(str(date_str), "ord") % 100000


def _pick(pool, date_str, salt, vars_, cost=None):
    """Rotation déterministe : les variantes utilisables (variables renseignées) sont rangées dans un ordre fixe (hash du texte),
    puis on avance d'un cran par jour : aucune variante ne revient avant d'avoir épuisé toute la banque du scénario.
    Avec une mémoire (cost), on prend la variante la moins redondante avec ce qui a déjà été lu ; la rotation départage les ex æquo."""
    ok = [v for v in pool if all(vars_.get(f) not in (None, "") for f in _fields(v))]
    ok = ok or [v for v in pool if not _fields(v)]
    if not ok:
        return ""
    ok.sort(key=lambda t: hashlib.md5(t.encode("utf-8")).hexdigest())
    start = (_ord(date_str) + _h("", salt)) % len(ok)
    clean = {k: ("" if x is None else x) for k, x in vars_.items()}
    if cost is None or len(ok) == 1:
        return ok[start].format_map(clean)
    best = None
    for j in range(len(ok)):
        t = ok[(start + j) % len(ok)].format_map(clean)
        c = cost(t)
        if best is None or c < best[0] - 1e-9: best = (c, t)
    return best[1]


def _name_pick(lst, date_str, salt, used, cost=None):
    """Surnom ou insulte choisi par hash, sans répétition dans le même paragraphe (et, avec une mémoire, le moins utilisé récemment)."""
    start = (_ord(date_str) * 7 + _h("", salt)) % len(lst)
    cands = [lst[(start + k) % len(lst)] for k in range(len(lst))]
    cands = [v for v in cands if v not in used] or [lst[start]]
    v = cands[0] if cost is None else min(cands, key=cost)       # min : à coût égal, le premier de la rotation
    used.add(v)
    return v


def perf_level(score):
    return None if score is None else "hi" if score >= 14 else "mid" if score >= 10 else "lo"


def score_band(score):
    return "tres_bas" if score < 7 else "bas" if score < 10 else "moyen" if score < 13 else "bon" if score < 16 else "tres_bon" if score < 18 else "elite"


def state_level(profile):
    return "ok" if profile in STATE_OK else "ko" if profile in STATE_KO else "neutral"


def goal_class(ret, target):
    if not ret or not target:
        return "none"
    r = ret / target
    return "ahead" if r <= 1.0 else "close" if r <= 1.03 else "mid" if r <= 1.08 else "far"


def count_class(days):
    return "taper" if days <= 14 else "near" if days <= 45 else "mid" if days <= 120 else "far"


def compose(sig, date_str, key, mem=None):
    """Assemble le paragraphe. `sig` : dictionnaire de signaux calculés par analysis.bilan_signals().
    Retourne {"text", "parts": [(bloc, scénario, texte)], "scenario": {...}}."""
    score = sig.get("score")
    prof = sig.get("profile") or "données_insuffisantes"
    win = WIN.get(key, "sur la période")
    lvl = perf_level(score)
    st_lvl = state_level(prof)
    allow_ins = prof not in NO_INSULT_PROFILES
    used_n, used_i = set(), set()
    base = {"name": NAME, "win": win, "score": None if score is None else f"{score:.1f}".replace(".", ","), "nick": None, "ins": None}
    base.update(sig.get("vars") or {})

    def V(salt, **extra):
        v = dict(base)
        v.update(extra)
        wc = (lambda w: mem.cost_word(w, key)) if mem else None
        v["nick"] = _name_pick(NICK, date_str, f"{key}:nick:{salt}", used_n, wc)
        v["ins"] = _name_pick(INS, date_str, f"{key}:ins:{salt}", used_i, wc)
        return v

    def pool_ok(pool):         # écarte les variantes avec insulte quand l'état ne le permet pas
        return pool if allow_ins else [t for t in pool if "{ins}" not in t]

    parts = []

    n_aside = [0]
    aside_lvl = "ko" if st_lvl == "ko" else (lvl or "mid")

    def add(block, scen, pool, salt, **extra):
        v = V(salt, **extra)
        so_far = [R.profile(p[2]) for p in parts] if mem else ()
        cost = (lambda t: mem.cost(t, key, so_far)) if mem else None
        txt = _pick(pool_ok(pool), date_str, f"{key}:{block}:{scen}", v, cost)
        if txt and block in ("STRONG", "WEAK", "GOAL", "STATE") and n_aside[0] < 2 and txt[-1] == "." and _h(date_str, f"{key}:aside:{block}") % 100 < 45:
            a = _pick(pool_ok(ASIDE[aside_lvl]), date_str, f"{key}:aside:{block}:{scen}", v, (lambda t: mem.cost(t, key, so_far)) if mem else None)
            if a:
                txt = txt[:-1] + f" ({a})."
                n_aside[0] += 1
        if txt:
            parts.append((block, scen, _cap(txt)))

    # 0. Salutation (contexte : état mauvais > niveau de la période)
    gk = "ko" if st_lvl == "ko" else (lvl or "mid")
    add("GREET", gk, GREET[gk], "greet")
    if sig.get("stale") in STALE:
        add("STALE", sig["stale"], STALE[sig["stale"]], "stale")

    def trans(block, salt, pct=40):         # transition humoristique optionnelle, déterministe
        if _h(date_str, f"{key}:trans:{salt}") % 100 < pct:
            add("TRANS", salt, TRANS[salt], f"tr{salt}")
    # 1. Accroche
    if score is not None:
        add("OPENER", score_band(score), OPENER[score_band(score)], "open")
    else:
        parts.append(("OPENER", "none", f"{NAME}, pas assez de données {win} pour te noter : la montre ne m'a pas donné grand-chose à me mettre sous la dent."))
    # 2. Piliers
    trans("TRANS", "pilier")
    pil = {k: v for k, v in (sig.get("pillars") or {}).items() if v.get("score") is not None}
    if len(pil) >= 2:
        best = max(pil, key=lambda k: pil[k]["score"]); worst = min(pil, key=lambda k: pil[k]["score"])
        sb, sw_ = pil[best]["score"], pil[worst]["score"]
        mean_ = sum(v["score"] for v in pil.values()) / len(pil)
        fm = lambda x: f"{x:.1f}".replace(".", ",")
        pv = lambda k: dict(sig.get("pillar_vars", {}).get(k, {}), sc=fm(pil[k]["score"]), pname=pil[k]["name"])
        if sb - sw_ < 0.9:
            add("BALANCED", "hi" if mean_ >= 2.8 else "lo" if mean_ < 2.0 else "mid", BALANCED["hi" if mean_ >= 2.8 else "lo" if mean_ < 2.0 else "mid"], "bal")
        else:
            if sb >= 2.0: add("STRONG", best, STRONG[best], "strong", **pv(best))
            else: add("BEST_LOW", best, BEST_LOW, "bestlow", **pv(best))
            if sw_ < 3.0:
                wk = worst if worst != "load" else ("load_high" if sig.get("load_dir") == "high" else "load_low")
                add("WEAK", wk, WEAK[wk], "weak", **pv(worst))
            else: add("WORST_HIGH", worst, WORST_HIGH, "worsthigh", **pv(worst))
    # 3. Objectif
    trans("TRANS", "goal")
    g = sig.get("goal") or {}
    gc = goal_class(g.get("ret"), g.get("target"))
    add("GOAL", gc, GOAL[gc], "goal", **{k: g.get(k) for k in ("glabel", "gret", "gtarget", "ggap", "gpct")})
    # 4. Forme du moment + modificateur
    trans("TRANS", "state")
    add("STATE", prof, STATE[prof], "state")
    m = sig.get("mod")
    if m and m in MOD:
        add("MOD", m, MOD[m], "mod")
    # 5. Blague puis conclusion
    if lvl is not None:
        scen = f"{lvl}_{st_lvl}"
        add("JOKE", scen, JOKE[scen], "joke")
        trans("TRANS", "closer", 30)
        add("CLOSER", scen, CLOSER[scen], "closer")
    # 6. Tendance ou compte à rebours (alternance par hash, selon disponibilité)
    tail = []
    if sig.get("trend") in TREND: tail.append(("TREND", sig["trend"], TREND[sig["trend"]]))
    if sig.get("days_to_race") is not None: tail.append(("COUNT", count_class(sig["days_to_race"]), COUNT[count_class(sig["days_to_race"])]))
    if tail:
        b, s, p = tail[_h(date_str, f"{key}:tail") % len(tail)]
        add(b, s, p, "tail")
    text = " ".join(p[2] for p in parts)
    # Version courte (affichée par défaut) : accroche + point fort + point faible + conclusion, sans apartés.
    keep = ("OPENER", "STRONG", "BALANCED", "BEST_LOW", "WEAK", "WORST_HIGH", "CLOSER")
    short = " ".join(re.sub(r" \([^()]*\)\.$", ".", p[2]) for p in parts if p[0] in keep)
    return {"text": text, "short": short or text, "parts": [list(p) for p in parts],
            "scenario": {"band": score_band(score) if score is not None else None, "perf": lvl, "state": prof, "state_level": st_lvl}}


def library_size():
    """Nombre de phrases par banque et total (hors surnoms)."""
    def n(b): return sum(len(x) if isinstance(x, list) else n(x) for x in b.values()) if isinstance(b, dict) else len(b)
    banks = {"STALE": STALE, "ASIDE": ASIDE, "GREET": GREET, "TRANS": TRANS, "JOKE": JOKE, "OPENER": OPENER, "STRONG": STRONG, "WEAK": WEAK, "BALANCED": BALANCED, "BEST_LOW": BEST_LOW, "WORST_HIGH": WORST_HIGH,
             "GOAL": GOAL, "STATE": STATE, "MOD": MOD, "CLOSER": CLOSER, "TREND": TREND, "COUNT": COUNT}
    return {k: n(v) for k, v in banks.items()}


# Phrases supplémentaires (mêmes banques, mêmes règles) : bilan_plus1.py à bilan_plus3.py
import bilan_plus1
import bilan_plus2
import bilan_plus3
import sys as _sys
for _m in (bilan_plus1, bilan_plus2, bilan_plus3): _m.etendre(_sys.modules[__name__])
