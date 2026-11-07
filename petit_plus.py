"""« Le petit plus du coach » : une anecdote, une citation, une blague, un adage ou une devinette sportive par jour.

Bibliothèque de plus de 600 entrées, 100 % déterministe (aucune IA, aucun accès réseau).
Types d'entrées : Citation, Anecdote, Record, Fait historique, Anecdote insolite, Le saviez-vous, Adage, Blague, Devinette.

Règles de sélection (fonction du_jour) :
- une entrée par jour, identique quelle que soit la période d'analyse (1 semaine, 1 mois, 3 mois) : elle ne dépend que de la date ;
- aucune entrée ne revient dans les 60 jours qui suivent sa dernière apparition (la bibliothèque est découpée en blocs d'au moins 60 entrées ;
  chaque cycle passe tous les blocs, dans un ordre et un mélange qui changent d'un cycle à l'autre ; le premier bloc d'un cycle et le dernier
  du précédent sont toujours distincts) ;
- deux jours de suite ne proposent pas le même type d'entrée tant que c'est possible.

Sources et prudence : les citations sont traduites en français ; quand l'attribution est d'usage mais non démontrée, la mention « attribué à » est affichée.
Les chiffres et dates des faits sont ceux de références courantes (comités sportifs, fédérations, presse spécialisée) au moment de la rédaction.
"""
import hashlib
import random
from datetime import date

KIND_LABEL = {"citation": "Citation", "anecdote": "Anecdote", "record": "Record", "histoire": "Fait historique", "insolite": "Anecdote insolite",
              "science": "Le saviez-vous", "adage": "Adage", "blague": "Blague", "devinette": "Devinette"}

# ---------------------------------------------------------------------------------------------
# CITATIONS (texte, auteur) : sportifs, philosophes, écrivains, aventuriers, commentateurs, personnages historiques, répliques de films
# ---------------------------------------------------------------------------------------------
CITATIONS = [
    ("Si tu veux courir, cours un mile. Si tu veux changer ta vie, cours un marathon.", "attribué à Emil Zátopek, athlète tchécoslovaque"),
    ("L'oiseau vole, le poisson nage, l'homme court.", "attribué à Emil Zátopek, athlète tchécoslovaque"),
    ("La douleur est inévitable. La souffrance est facultative.", "Haruki Murakami, écrivain et coureur de fond"),
    ("Seuls ceux qui sont disciplinés sont libres dans la vie.", "Eliud Kipchoge, marathonien"),
    ("Aucun être humain n'est limité.", "Eliud Kipchoge, marathonien"),
    ("Je détestais chaque minute d'entraînement, mais je me disais : n'abandonne pas. Souffre maintenant et vis le reste de ta vie en champion.", "Muhammad Ali, boxeur"),
    ("Vole comme un papillon, pique comme une abeille.", "Muhammad Ali, boxeur"),
    ("Les champions ne se fabriquent pas dans les salles de sport. Ils naissent de quelque chose qu'ils ont au fond d'eux : un désir, un rêve, une vision.", "Muhammad Ali, boxeur"),
    ("J'ai raté plus de 9 000 tirs dans ma carrière. J'ai perdu près de 300 matchs. Vingt-six fois, on m'a confié le tir de la victoire et je l'ai manqué. J'ai échoué encore et encore, et c'est pourquoi je réussis.", "Michael Jordan, basketteur"),
    ("Le talent gagne des matchs, mais le travail d'équipe et l'intelligence gagnent des championnats.", "Michael Jordan, basketteur"),
    ("Tu rates 100 % des tirs que tu ne tentes pas.", "Wayne Gretzky, joueur de hockey"),
    ("La pression est un privilège.", "Billie Jean King, joueuse de tennis"),
    ("Commence là où tu es, utilise ce que tu as, fais ce que tu peux.", "Arthur Ashe, joueur de tennis"),
    ("Le baseball, c'est 90 % mental. L'autre moitié, c'est physique.", "Yogi Berra, joueur de baseball"),
    ("Ce n'est pas fini tant que ce n'est pas fini.", "Yogi Berra, joueur de baseball"),
    ("Certains pensent que le football est une question de vie ou de mort. Je peux vous assurer que c'est bien plus sérieux que ça.", "Bill Shankly, entraîneur de Liverpool"),
    ("Jouer au football est simple, mais jouer un football simple est la chose la plus difficile.", "Johan Cruyff, footballeur et entraîneur"),
    ("Chaque désavantage a son avantage.", "Johan Cruyff, footballeur et entraîneur"),
    ("Quand les mouettes suivent un chalutier, c'est qu'elles pensent que des sardines seront jetées à la mer.", "Éric Cantona, footballeur (1995)"),
    ("Ce que je sais de plus sûr sur la morale et les obligations des hommes, c'est au football que je le dois.", "Albert Camus, écrivain"),
    ("Dans le football, tout est compliqué par la présence de l'équipe adverse.", "Jean-Paul Sartre, philosophe"),
    ("Si vous avez un corps, vous êtes un athlète.", "Bill Bowerman, entraîneur et cofondateur de Nike"),
    ("Donner moins que son maximum, c'est sacrifier le don.", "Steve Prefontaine, coureur de fond"),
    ("Si vous perdez foi en la nature humaine, allez regarder un marathon.", "Kathrine Switzer, première femme à courir Boston avec un dossard"),
    ("Parce qu'elle est là.", "George Mallory, alpiniste, à qui l'on demandait pourquoi gravir l'Everest (1923)"),
    ("Ce n'est pas la montagne que nous conquérons, mais nous-mêmes.", "attribué à Edmund Hillary, alpiniste"),
    ("Plus je m'entraîne, plus j'ai de chance.", "attribué à Gary Player, golfeur"),
    ("Ne laisse pas ce que tu ne peux pas faire t'empêcher de faire ce que tu peux faire.", "John Wooden, entraîneur de basket"),
    ("Sois rapide, mais ne te précipite pas.", "John Wooden, entraîneur de basket"),
    ("Roule autant ou aussi peu que tu veux, aussi longtemps ou aussi brièvement que tu veux. Mais roule.", "attribué à Eddy Merckx, cycliste"),
    ("La vie, c'est comme faire du vélo : pour garder l'équilibre, il faut avancer.", "Albert Einstein, dans une lettre à son fils (1930)"),
    ("Sur mes 1 500 matchs, j'en ai gagné près de 80 %. Mais sur l'ensemble des points joués, je n'en ai gagné que 54 %.", "Roger Federer, discours à l'université de Dartmouth (2024)"),
    ("Le succès n'est pas un accident. C'est du travail acharné, de la persévérance, de l'apprentissage, du sacrifice et, surtout, de l'amour pour ce que l'on fait.", "attribué à Pelé, footballeur"),
    ("La perfection n'est pas atteignable, mais si nous la poursuivons, nous pouvons atteindre l'excellence.", "attribué à Vince Lombardi, entraîneur de football américain"),
    ("Tout ce qui est négatif, la pression, les défis, est pour moi une occasion de m'élever.", "Kobe Bryant, basketteur"),
    ("On ne peut mettre de limite à rien. Plus on rêve, plus on va loin.", "Michael Phelps, nageur"),
    ("Nous avons tous des rêves. Mais pour les réaliser, il faut beaucoup de détermination, de dévouement, de discipline et d'efforts.", "Jesse Owens, athlète"),
    ("Ne sous-estimez jamais le pouvoir des rêves ni la force de l'esprit humain.", "Wilma Rudolph, sprinteuse"),
    ("L'important dans la vie, ce n'est point le triomphe, mais le combat ; l'essentiel, ce n'est pas d'avoir vaincu, mais de s'être bien battu.", "Pierre de Coubertin, rénovateur des Jeux olympiques"),
    ("Le sport va chercher la peur pour la dominer, la fatigue pour en triompher, la difficulté pour la vaincre.", "Pierre de Coubertin, rénovateur des Jeux olympiques"),
    ("Plus vite, plus haut, plus fort.", "Henri Didon, dominicain, devise olympique (1894)"),
    ("Être fort pour être utile.", "Georges Hébert, officier de marine, devise de la méthode naturelle"),
    ("Il faut demander aux dieux un esprit sain dans un corps sain.", "Juvénal, poète latin, Satires"),
    ("Nous sommes ce que nous répétons chaque jour. L'excellence n'est donc pas un acte, mais une habitude.", "Will Durant, résumant la pensée d'Aristote"),
    ("Ce n'est pas parce que les choses sont difficiles que nous n'osons pas, c'est parce que nous n'osons pas qu'elles sont difficiles.", "Sénèque, Lettres à Lucilius"),
    ("Nous souffrons plus souvent en imagination qu'en réalité.", "Sénèque, Lettres à Lucilius"),
    ("Ce qui entrave l'action fait avancer l'action ; ce qui barre le chemin devient le chemin.", "Marc Aurèle, Pensées"),
    ("Ce ne sont pas les choses qui troublent les hommes, mais les jugements qu'ils portent sur elles.", "Épictète, Manuel"),
    ("Ce qui ne me tue pas me rend plus fort.", "Friedrich Nietzsche, Le Crépuscule des idoles"),
    ("Toutes les pensées véritablement grandes sont conçues en marchant.", "Friedrich Nietzsche, Le Crépuscule des idoles"),
    ("Il faut porter en soi un chaos pour pouvoir enfanter une étoile qui danse.", "Friedrich Nietzsche, Ainsi parlait Zarathoustra"),
    ("Je ne puis méditer qu'en marchant ; sitôt que je m'arrête, je ne pense plus.", "Jean-Jacques Rousseau, Les Confessions"),
    ("Mes pensées dorment si je les assois.", "Michel de Montaigne, Essais"),
    ("Avant tout, ne perds pas ton envie de marcher : chaque jour, je marche jusqu'à mon bien-être et je m'éloigne de toute maladie.", "Søren Kierkegaard, lettre à sa nièce Henriette (1847)"),
    ("Un voyage de mille lieues commence toujours par un premier pas.", "Lao-Tseu, Tao Te King"),
    ("Notre nature est dans le mouvement ; le repos entier est la mort.", "Blaise Pascal, Pensées"),
    ("Déjà essayé. Déjà échoué. Peu importe. Essaie encore. Échoue encore. Échoue mieux.", "Samuel Beckett, Cap au pire"),
    ("Ce n'est pas le critique qui compte, ni celui qui montre comment l'homme fort a trébuché. L'honneur revient à celui qui est réellement dans l'arène, le visage couvert de poussière, de sueur et de sang.", "Theodore Roosevelt, discours de la Sorbonne (1910)"),
    ("Nous choisissons d'aller sur la Lune, non parce que c'est facile, mais parce que c'est difficile.", "John F. Kennedy, discours de l'université Rice (1962)"),
    ("Voyageur, il n'y a pas de chemin : le chemin se fait en marchant.", "Antonio Machado, poète espagnol"),
    ("Deux routes se séparaient dans un bois, et moi j'ai pris celle qui était la moins fréquentée, et cela a fait toute la différence.", "Robert Frost, La Route non prise (1916)"),
    ("Le mieux est l'ennemi du bien.", "Voltaire, La Bégueule"),
    ("Rien ne sert de courir ; il faut partir à point.", "Jean de La Fontaine, Le Lièvre et la Tortue"),
    ("Patience et longueur de temps font plus que force ni que rage.", "Jean de La Fontaine, Le Lion et le Rat"),
    ("Hâtez-vous lentement, et sans perdre courage, vingt fois sur le métier remettez votre ouvrage.", "Nicolas Boileau, L'Art poétique"),
    ("Il faut imaginer Sisyphe heureux.", "Albert Camus, Le Mythe de Sisyphe"),
    ("La lutte elle-même vers les sommets suffit à remplir un cœur d'homme.", "Albert Camus, Le Mythe de Sisyphe"),
    ("Pour ce qui est de l'avenir, il ne s'agit pas de le prévoir, mais de le rendre possible.", "Antoine de Saint-Exupéry, Citadelle"),
    ("Le hasard ne favorise que les esprits préparés.", "Louis Pasteur, leçon inaugurale à Lille (1854)"),
    ("Je n'ai pas échoué. J'ai simplement trouvé dix mille solutions qui ne marchent pas.", "attribué à Thomas Edison, inventeur"),
    ("Dans la vie, rien n'est à craindre, tout est à comprendre.", "attribué à Marie Curie, physicienne"),
    ("Les deux guerriers les plus puissants sont la patience et le temps.", "Léon Tolstoï, Guerre et Paix"),
    ("Le courage, c'est la grâce sous la pression.", "Ernest Hemingway, écrivain"),
    ("Le héros et le lâche ressentent la même chose : la peur. Le héros s'en sert.", "attribué à Cus D'Amato, entraîneur de boxe"),
    ("Le fer se rouille faute de s'en servir ; l'eau stagnante perd sa pureté. L'inaction sape de même la vigueur de l'esprit.", "attribué à Léonard de Vinci"),
    ("Marcher est le meilleur remède de l'homme.", "attribué à Hippocrate, médecin grec"),
    ("Le manque d'activité détruit la bonne condition de tout être humain, tandis que le mouvement et l'exercice méthodique la sauvent et la préservent.", "attribué à Platon"),
    ("Ce que tu cherches te cherche aussi.", "attribué à Rumi, poète persan"),
    ("Le sport a le pouvoir de changer le monde. Il a le pouvoir d'inspirer, il a le pouvoir d'unir les gens comme peu d'autres choses.", "Nelson Mandela, discours aux Laureus Awards (2000)"),
    ("Cela paraît toujours impossible, jusqu'à ce qu'on le fasse.", "attribué à Nelson Mandela"),
    ("La victoire attend celui qui a tout mis en ordre. Les gens appellent cela la chance.", "attribué à Roald Amundsen, explorateur polaire"),
    ("Tout ce qu'un homme est capable d'imaginer, d'autres hommes seront capables de le réaliser.", "attribué à Jules Verne"),
    ("Une vie n'a d'importance que par l'impact qu'elle a sur d'autres vies.", "Jackie Robinson, joueur de baseball"),
    ("Je ne suis pas un modèle.", "Charles Barkley, basketteur, dans une publicité Nike (1993)"),
    ("Cours quand tu peux, marche si tu dois, rampe si tu y es obligé ; mais n'abandonne jamais.", "Dean Karnazes, ultramarathonien"),
    ("Tout le monde est un athlète. Seuls certains d'entre nous sont à l'entraînement.", "attribué à George Sheehan, cardiologue et coureur"),
    ("Ne priez pas pour une vie facile, priez pour avoir la force de supporter une vie difficile.", "attribué à Bruce Lee"),
    ("Je ne crains pas l'homme qui a pratiqué dix mille coups différents une fois, mais celui qui a pratiqué un seul coup dix mille fois.", "attribué à Bruce Lee"),
    ("Tout le monde a un plan, jusqu'à ce qu'il prenne un coup de poing en pleine figure.", "Mike Tyson, boxeur (2012)"),
    ("Ce n'est pas de savoir combien tu frappes fort, mais combien tu peux encaisser et continuer d'avancer.", "Sylvester Stallone, dans Rocky Balboa (2006)"),
    ("Quand je cours, je sens Son plaisir.", "Eric Liddell, dans Les Chariots de feu (1981)"),
    ("Fais-le ou ne le fais pas. Il n'y a pas d'essai.", "Yoda, dans L'Empire contre-attaque (1980)"),
    ("Ça ne devient jamais plus facile : tu vas simplement plus vite.", "Greg LeMond, vainqueur du Tour de France"),
    ("Le bien se fait, il ne se dit pas. Certaines médailles s'accrochent à l'âme, pas à la veste.", "attribué à Gino Bartali, cycliste"),
    ("N'abandonne jamais. N'abandonne jamais. N'abandonne jamais.", "Jim Valvano, entraîneur de basket, discours des ESPY (1993)"),
    ("Tout peut arriver en Formule 1, et cela arrive généralement.", "Murray Walker, commentateur de Formule 1"),
    ("Certains spectateurs sont sur le terrain, ils pensent que c'est fini. Et maintenant, c'est fini !", "Kenneth Wolstenholme, commentateur de la finale de la Coupe du monde 1966"),
    ("Allez les petits !", "Roger Couderc, commentateur de rugby"),
    ("Campioni del mondo ! Campioni del mondo ! Campioni del mondo !", "Nando Martellini, commentateur de la finale de la Coupe du monde 1982"),
    ("Croyez-vous aux miracles ? Oui !", "Al Michaels, commentateur du « Miracle sur glace » de Lake Placid (1980)"),
    ("Frazier est à terre ! Frazier est à terre !", "Howard Cosell, commentateur du combat Foreman-Frazier (1973)"),
    ("Les conquérants de l'inutile.", "Lionel Terray, alpiniste, titre de son livre (1961)"),
    ("Chaque fois que l'envie me prend de faire de l'exercice, je m'allonge jusqu'à ce qu'elle me passe.", "attribué à Robert Hutchins, souvent prêté à Mark Twain"),
    ("Le succès n'est pas définitif, l'échec n'est pas fatal : c'est le courage de continuer qui compte.", "attribué à Winston Churchill"),
    ("Le meilleur moment pour planter un arbre était il y a vingt ans. Le deuxième meilleur moment, c'est maintenant.", "proverbe attribué à la Chine"),
    ("Peu importe la lenteur à laquelle tu avances, du moment que tu ne t'arrêtes pas.", "attribué à Confucius"),
    ("Chi va piano va sano e va lontano. Qui va doucement va sainement et va loin.", "proverbe italien"),
    ("Tombe sept fois, relève-toi huit.", "proverbe japonais"),
    ("Si tu veux aller vite, marche seul. Si tu veux aller loin, marchons ensemble.", "proverbe africain"),
    ("L'avenir a plusieurs noms : pour les faibles, c'est l'impossible ; pour les timides, c'est l'inconnu ; pour les vaillants, c'est l'idéal.", "Victor Hugo, écrivain"),
    ("Le talent, ça n'existe pas. Le talent, c'est d'avoir envie de faire quelque chose.", "Jacques Brel, chanteur"),
]

# ---------------------------------------------------------------------------------------------
# RECORDS : performances chiffrées (athlétisme, natation, cyclisme, endurance, aventure)
# ---------------------------------------------------------------------------------------------
RECORDS = [
    "Le 6 mai 1954 à Oxford, Roger Bannister devient le premier homme à courir un mile en moins de quatre minutes : 3 min 59 s 4. John Landy le battait déjà moins de deux mois plus tard, en 3 min 57 s 9.",
    "En août 2009, aux championnats du monde de Berlin, Usain Bolt établit les records du monde du 100 m (9 s 58) et du 200 m (19 s 19).",
    "Aux Jeux de Mexico en 1968, Bob Beamon saute 8,90 m en longueur, soit 55 cm de plus que l'ancien record du monde. Il faudra attendre 1991 et les 8,95 m de Mike Powell pour le voir tomber.",
    "En 1988, Florence Griffith-Joyner court le 100 m en 10 s 49 et le 200 m en 21 s 34. Ces marques sont restées inégalées pendant plus de trente ans.",
    "Le 26 juillet 1983 à Munich, la Tchécoslovaque Jarmila Kratochvílová court le 800 m en 1 min 53 s 28. Ce record du monde a résisté plus de quarante ans.",
    "En 1996 à Iéna, le Tchèque Jan Železný lance son javelot à 98,48 m, un record du monde qui n'a jamais été approché depuis.",
    "Sergueï Bubka a battu 35 records du monde de saut à la perche, et il est le premier homme à franchir six mètres, à Paris en juillet 1985.",
    "En 2020 à Toruń, le Suédois Armand Duplantis franchit 6,17 m en salle : le premier d'une longue série de records du monde qu'il a ensuite repoussés centimètre par centimètre.",
    "Le 12 octobre 2019 à Vienne, Eliud Kipchoge est le premier homme à courir un marathon en moins de deux heures : 1 h 59 min 40 s. L'exploit n'est pas homologué, car il a été réalisé avec des lièvres relayés et une voiture-guide.",
    "À Berlin en septembre 2022, Eliud Kipchoge établit un record du monde officiel du marathon en 2 h 01 min 09 s.",
    "À Chicago en octobre 2023, le Kényan Kelvin Kiptum devient le premier à descendre sous 2 h 01 au marathon : 2 h 00 min 35 s.",
    "Le record du monde féminin du marathon de Paula Radcliffe, 2 h 15 min 25 s à Londres en 2003, a tenu seize ans avant d'être battu en 2019.",
    "Haile Gebrselassie a battu 27 records du monde en carrière, et couru le marathon de Berlin en 2 h 03 min 59 s en 2008.",
    "En 1960 à Rome, Abebe Bikila gagne le marathon olympique pieds nus, en 2 h 15 min 16 s, un record du monde. Quatre ans plus tard à Tokyo, chaussé cette fois, il gagne à nouveau et améliore le record en 2 h 12 min 11 s.",
    "À Toronto en 2011, Fauja Singh termine un marathon à 100 ans. Faute d'acte de naissance officiel, son âge n'a pas été homologué par le Guinness des records.",
    "Le Canadien Ed Whitlock a couru en 2004 un marathon en 2 h 54 min 48 s à 73 ans, premier septuagénaire sous les trois heures.",
    "Aux Jeux de Los Angeles en 1984, Joan Benoit gagne le premier marathon olympique féminin de l'histoire, en 2 h 24 min 52 s.",
    "La Norvégienne Grete Waitz a remporté neuf fois le marathon de New York, entre 1978 et 1988.",
    "Kenenisa Bekele avait établi en 2004 le record du monde du 5 000 m (12 min 37 s 35) puis en 2005 celui du 10 000 m (26 min 17 s 53). Ces deux marques ont tenu plus de quinze ans, jusqu'à ce que l'Ougandais Joshua Cheptegei les efface en 2020.",
    "Hicham El Guerrouj a couru le 1 500 m en 3 min 26 s à Rome en 1998, puis le mile en 3 min 43 s 13 en 1999. Ces deux records du monde ont tenu plus de vingt-cinq ans.",
    "Dick Fosbury remporte l'or olympique de saut en hauteur à Mexico en 1968 avec 2,24 m, en franchissant la barre sur le dos : le « Fosbury flop » est né.",
    "Aux Jeux de 1972, le Finlandais Lasse Virén tombe en plein 10 000 m, se relève, gagne et bat le record du monde. Il enchaînera avec l'or sur 5 000 m, et refera le doublé quatre ans plus tard.",
    "Le Finlandais Paavo Nurmi a remporté neuf médailles d'or olympiques entre 1920 et 1928, en courant souvent avec un chronomètre à la main pour gérer son allure.",
    "Carl Lewis a gagné neuf médailles d'or olympiques entre 1984 et 1996, en 100 m, 200 m, relais 4 × 100 m et saut en longueur.",
    "Le 25 mai 1935, en 45 minutes, Jesse Owens bat trois records du monde et en égale un quatrième lors d'une réunion universitaire à Ann Arbor.",
    "Aux Jeux de Berlin en 1936, Jesse Owens remporte quatre médailles d'or : 100 m, 200 m, longueur et relais 4 × 100 m.",
    "Michael Phelps a remporté 23 médailles d'or olympiques et 28 médailles au total. À Pékin en 2008, il gagne huit titres en huit jours.",
    "Aux Jeux de Munich en 1972, Mark Spitz gagne sept médailles d'or, chacune avec un record du monde.",
    "Johnny Weissmuller est le premier nageur à descendre sous la minute sur 100 m nage libre, en 1922. Il deviendra ensuite le Tarzan du cinéma.",
    "En 2023 à Fukuoka, Léon Marchand bat le record du monde du 400 m quatre nages détenu depuis 2008 par Michael Phelps : 4 min 02 s 50.",
    "Aux Jeux de Paris en 2024, Léon Marchand remporte quatre titres olympiques individuels : 200 m papillon, 200 m brasse, 200 m et 400 m quatre nages.",
    "En 1972 à Mexico, Eddy Merckx établit le record de l'heure à 49,431 km. Cinquante ans plus tard, en octobre 2022 à Granges, Filippo Ganna le porte à 56,792 km.",
    "En 1989, Greg LeMond remporte le Tour de France avec huit secondes d'avance sur Laurent Fignon, après le contre-la-montre final des Champs-Élysées : le plus petit écart de l'histoire.",
    "Mark Cavendish a remporté en 2024 sa 35e étape sur le Tour de France, battant le record de 34 étapes d'Eddy Merckx.",
    "Eddy Merckx a remporté cinq Tours de France, cinq Tours d'Italie et un Tour d'Espagne. En 1969, il gagne le Tour avec les maillots jaune, vert et à pois.",
    "Marie-José Pérec remporte à Atlanta en 1996 le doublé 200 m - 400 m, après son titre sur 400 m de 1992 : trois médailles d'or olympiques en athlétisme.",
    "Colette Besson remporte le 400 m des Jeux de Mexico en 1968 en remontant ses adversaires dans les derniers mètres.",
    "Jean-Claude Killy remporte les trois épreuves de ski alpin aux Jeux de Grenoble en 1968 : descente, slalom géant et slalom.",
    "Martin Fourcade a remporté cinq médailles d'or olympiques en biathlon, de 2014 à 2018.",
    "Tony Estanguet a remporté trois titres olympiques de canoë slalom, en 2000, 2004 et 2012, avant de présider le comité d'organisation des Jeux de Paris 2024.",
    "Teddy Riner a remporté onze titres de champion du monde de judo et trois titres olympiques, à Londres, Rio et Paris.",
    "Renaud Lavillenie saute 6,16 m à Donetsk en février 2014 et bat le record de Bubka en salle, vieux de vingt et un ans.",
    "Christophe Lemaitre est en 2010 le premier athlète blanc à descendre sous les 10 secondes sur 100 m, avec 9 s 98 à Valence.",
    "Julien Absalon a remporté deux titres olympiques de VTT cross-country (2004 et 2008) et cinq titres de champion du monde.",
    "François D'Haene a gagné quatre fois l'Ultra-Trail du Mont-Blanc, en 2012, 2014, 2017 et 2021.",
    "L'Américaine Courtney Dauwalter a gagné l'Ultra-Trail du Mont-Blanc à plusieurs reprises, dès 2019.",
    "En mai 2017, Kilian Jornet gravit l'Everest deux fois en une semaine, sans oxygène ni corde fixe.",
    "Alex Honnold a réalisé en juin 2017 l'ascension en solo intégral, sans corde, de la face d'El Capitan dans le Yosemite en 3 h 56.",
    "Ellen MacArthur boucle en 2005 un tour du monde en solitaire sans escale en 71 jours, 14 heures et 18 minutes, un record battu depuis.",
    "Chrissie Wellington a remporté quatre fois l'Ironman d'Hawaï et n'a jamais perdu de course sur distance Ironman.",
    "Paula Newby-Fraser a remporté huit fois l'Ironman d'Hawaï, un record chez les femmes.",
    "Mark Allen a gagné six fois l'Ironman d'Hawaï, après des années à finir derrière Dave Scott. Leur duel de 1989, résolu à 58 secondes, est resté célèbre sous le nom d'« Iron War ».",
    "En 2016 à Roth, en Allemagne, Jan Frodeno boucle un triathlon sur distance Ironman en 7 h 35 min 39 s, la meilleure performance jamais réalisée sur cette distance à l'époque.",
    "Aux Jeux de Sydney en 2000, le triathlon fait son entrée olympique : les premiers champions sont le Canadien Simon Whitfield et la Suissesse Brigitte McMahon.",
    "L'Ö till Ö, le swimrun mythique de l'archipel de Stockholm, relie Sandhamn à Utö en 75 km : environ 65 km de course à pied et 10 km de natation, répartis sur 26 îles.",
    "Le Britannique Matthew Webb est en 1875 le premier homme à traverser la Manche à la nage : 21 h 45.",
    "En 1926, l'Américaine Gertrude Ederle traverse la Manche à la nage en un peu plus de 14 h 30, plus vite que les hommes qui l'avaient fait avant elle.",
    "En 1987, l'Américaine Lynne Cox traverse à la nage le détroit de Béring, entre l'Alaska et l'URSS, dans une eau à environ 4 °C.",
    "Aux Jeux de Mexico en 1968, l'Éthiopien Mamo Wolde gagne le marathon, et le Tanzanien John Stephen Akhwari termine bon dernier, blessé, plus d'une heure après le vainqueur, en disant : « Mon pays ne m'a pas envoyé à 5 000 miles pour commencer la course, mais pour la finir. »",
    "À Wimbledon en 2010, John Isner et Nicolas Mahut jouent un match de 11 h 05 min réparti sur trois jours, avec un cinquième set remporté 70-68 par l'Américain.",
    "Rafael Nadal a remporté quatorze fois Roland-Garros entre 2005 et 2022.",
    "Roger Federer a remporté huit fois Wimbledon, entre 2003 et 2017.",
    "Just Fontaine a marqué 13 buts en six matchs pendant la Coupe du monde 1958, un record jamais égalé depuis.",
    "Miroslav Klose a marqué 16 buts en quatre Coupes du monde, entre 2002 et 2014.",
    "Le Turc Hakan Şükür marque après 11 secondes lors du match pour la troisième place de la Coupe du monde 2002 : le but le plus rapide de l'histoire de la compétition.",
    "Pelé est le seul joueur à avoir remporté trois Coupes du monde, en 1958, 1962 et 1970.",
    "Michel Platini a marqué 9 buts en 5 matchs à l'Euro 1984, un record pour une seule édition.",
    "À 42 ans, le Camerounais Roger Milla marque lors de la Coupe du monde 1994 : le plus vieux buteur de l'histoire de la compétition.",
    "Lionel Messi a remporté huit Ballons d'or, en 2009, 2010, 2011, 2012, 2015, 2019, 2021 et 2023.",
    "Le 2 mars 1962 à Hershey, Wilt Chamberlain inscrit 100 points dans un match de NBA, un record encore inégalé.",
    "Bill Russell a remporté onze titres NBA en treize saisons avec les Boston Celtics.",
    "Michael Jordan a remporté six titres NBA avec les Chicago Bulls, et a été élu à chaque fois meilleur joueur des finales.",
    "À la fin de la prolongation de la finale de la Coupe du monde de rugby 2003, Jonny Wilkinson passe un drop du pied droit qui offre le titre à l'Angleterre face à l'Australie.",
    "Le 30 octobre 1974 à Kinshasa, Muhammad Ali bat George Foreman par K.-O. à la huitième reprise, après avoir encaissé ses coups sur les cordes : la tactique du « rope-a-dope ».",
    "Jim Thorpe a remporté le pentathlon et le décathlon aux Jeux de Stockholm en 1912. Déchu de ses titres en 1913 pour avoir joué au baseball professionnel, il a été officiellement rétabli seul vainqueur par le CIO en 2022.",
]

# ---------------------------------------------------------------------------------------------
# FAITS HISTORIQUES : origines, institutions, premières fois
# ---------------------------------------------------------------------------------------------
HISTOIRE = [
    "Les premiers Jeux olympiques de l'Antiquité dont la trace est conservée datent de 776 av. J.-C. à Olympie. La seule épreuve était alors une course à pied d'un stade, environ 190 mètres, remportée par le cuisinier Koroibos.",
    "Aux Jeux de l'Antiquité, les athlètes concouraient nus. Le mot « gymnase » vient du grec gymnos, qui signifie « nu ».",
    "Le mot « athlète » vient du grec athlos, l'effort, le combat. Le mot « triathlon » associe tri, trois, et athlon, l'épreuve.",
    "Le mot « sport » vient de l'ancien français desport, qui désignait le divertissement. Il est passé en anglais avant de nous revenir avec un autre sens.",
    "Les premiers Jeux olympiques modernes ont lieu à Athènes en 1896, à l'initiative de Pierre de Coubertin. Le Grec Spyridon Louis y remporte le marathon.",
    "En 1896, les vainqueurs olympiques recevaient une médaille d'argent et une branche d'olivier. Les médailles d'or n'apparaissent qu'aux Jeux de 1904.",
    "La devise olympique « Citius, Altius, Fortius » (plus vite, plus haut, plus fort) a été complétée en 2021 par « Communiter », qui veut dire « ensemble ».",
    "Aux Jeux de Paris en 1900, plusieurs épreuves de natation se sont déroulées dans la Seine. En 2024, le triathlon et le marathon de natation y sont revenus.",
    "La distance officielle du marathon, 42,195 km, date des Jeux de Londres en 1908 : le parcours partait du château de Windsor et finissait devant la loge royale du stade. Elle n'a été fixée définitivement qu'en 1921.",
    "Selon la légende, le soldat Philippidès aurait couru de Marathon à Athènes en 490 av. J.-C. pour annoncer la victoire sur les Perses, avant de s'effondrer. Les historiens doutent de la course, mais la légende a donné son nom à l'épreuve.",
    "Aux Jeux de Londres en 1908, l'Italien Dorando Pietri arrive le premier dans le stade, épuisé, tombe plusieurs fois et est aidé à se relever. Il est disqualifié, mais la reine lui offre une coupe dorée. Le compositeur Irving Berlin lui a même consacré une chanson.",
    "Le 19 avril 1967, Kathrine Switzer prend le départ du marathon de Boston avec le dossard 261, malgré un organisateur qui tente de l'arracher. Les femmes n'auront le droit officiel de s'y inscrire qu'en 1972.",
    "Le marathon olympique féminin n'apparaît qu'aux Jeux de Los Angeles en 1984.",
    "Le marathon de New York est né en 1970 avec 127 participants, dont 55 ont terminé, en tournant quatre fois dans Central Park. Il est aujourd'hui l'un des plus grands du monde, avec plus de cinquante mille arrivants certaines années.",
    "En 1978 à Hawaï, quinze hommes prennent le départ du premier Ironman, né d'un pari entre sportifs sur qui était le plus complet : 3,8 km de natation, 180 km de vélo et un marathon. Douze l'ont terminé, le vainqueur Gordon Haller en 11 h 46.",
    "L'Ironman est né de la proposition du commandant John Collins : combiner la natation de Waikiki, le tour de l'île à vélo et le marathon d'Honolulu en une seule épreuve.",
    "En 1982, à Hawaï, Julie Moss mène l'Ironman jusqu'à quelques mètres de l'arrivée, tombe et termine à quatre pattes. L'image diffusée à la télévision américaine a fait connaître l'épreuve dans le monde entier.",
    "Le swimrun est né en 2002 en Suède d'un pari entre amis : relier Sandhamn à Utö, dans l'archipel de Stockholm, en courant sur les îles et en nageant entre elles. « Ö till Ö » signifie « d'île en île ».",
    "Le triathlon moderne est né à San Diego en 1974, lors d'une course organisée par le Club d'athlétisme de San Diego : quelques dizaines de participants enchaînent course, vélo et natation.",
    "Le premier Tour de France part en 1903, organisé par le journal L'Auto pour relancer ses ventes. Soixante coureurs au départ, vingt et un à l'arrivée, vainqueur : Maurice Garin.",
    "Le maillot jaune du Tour de France est apparu en 1919. Il est jaune parce que le journal L'Auto, organisateur de la course, était imprimé sur du papier jaune.",
    "Le maillot à pois du meilleur grimpeur a été créé en 1975. Il rend hommage, par son motif, aux emballages d'un sponsor de chocolat.",
    "En 1910, dans le col d'Aubisque, Octave Lapize lance aux organisateurs du Tour : « Vous êtes des assassins ! », en raison de la difficulté des étapes pyrénéennes, ajoutées cette année-là.",
    "La « lanterne rouge » désigne le dernier du classement du Tour de France. L'expression vient de la lanterne rouge qui signalait le dernier wagon d'un train.",
    "Le mot « peloton » vient du français « pelote » : une petite boule, puis un groupe serré. Il est passé en anglais pour désigner le groupe principal de coureurs.",
    "L'ancêtre du vélo, la draisienne, est inventée en 1817 par l'Allemand Karl Drais. Elle n'avait pas de pédales : on se poussait avec les pieds.",
    "Les pédales apparaissent vers 1861 sur le vélocipède de Pierre Michaux. En 1888, John Dunlop invente le pneu gonflable, qui rend le vélo plus confortable.",
    "La première course cycliste officielle est Paris-Rouen, en 1869, gagnée par l'Anglais James Moore.",
    "Le Tour de France 2024 s'est terminé à Nice et non à Paris, une première dans l'histoire de la course, pour laisser la capitale à la préparation des Jeux olympiques.",
    "L'Alpe d'Huez compte vingt et un virages, numérotés en décroissant du bas vers le haut. La première arrivée du Tour y date de 1952, avec la victoire de Fausto Coppi.",
    "Le basket-ball a été inventé en décembre 1891 par James Naismith, professeur d'éducation physique à Springfield dans le Massachusetts, avec un ballon de football et deux paniers à pêches.",
    "Selon la légende, le rugby serait né en 1823 quand William Webb Ellis, élève du collège de Rugby, aurait pris le ballon à la main pendant un match de football. L'histoire est probablement embellie, mais le trophée de la Coupe du monde porte son nom.",
    "Le volley-ball a été inventé en 1895 par William Morgan, un éducateur de l'Association chrétienne de jeunes gens, comme une alternative moins brutale au basket.",
    "Le badminton tire son nom de Badminton House, un domaine du duc de Beaufort, en Angleterre, où le jeu s'est répandu à partir de 1873.",
    "Le premier match de football entre équipes nationales a eu lieu en 1872 à Glasgow : Écosse-Angleterre, 0-0.",
    "La première Coupe du monde de football se déroule en 1930 en Uruguay, et c'est le pays hôte qui la remporte. Treize équipes seulement y participent.",
    "La première Coupe du monde de rugby a lieu en 1987, en Nouvelle-Zélande et en Australie. Les All Blacks la remportent.",
    "La France remporte sa première Coupe du monde de football en 1998, à domicile, en battant le Brésil 3-0 en finale au Stade de France, avec deux têtes de Zinédine Zidane.",
    "Le tennis moderne est né en 1874 avec le major Walter Wingfield, qui dépose un brevet pour un jeu qu'il appelle « sphairistikè ». Le nom n'a pas survécu, le jeu oui.",
    "Le tournoi de Wimbledon existe depuis 1877. Il se joue sur gazon, et les joueurs y sont toujours vêtus de blanc.",
    "Le stade Roland-Garros, inauguré en 1928, porte le nom de Roland Garros, aviateur pionnier de la traversée de la Méditerranée en avion, mort au combat en 1918.",
    "Les Jeux paralympiques trouvent leur origine dans les Jeux de Stoke Mandeville, organisés en 1948 par le neurologue Ludwig Guttmann pour des soldats blessés. Les premiers Jeux paralympiques officiels ont eu lieu à Rome en 1960.",
    "Aux Jeux de Berlin en 1936, Jesse Owens a remporté quatre médailles d'or sous les yeux d'Adolf Hitler, démentant ainsi les théories racistes que le régime voulait illustrer.",
    "Le « Miracle sur glace » de 1980 voit une équipe américaine d'étudiants battre l'URSS en hockey sur glace aux Jeux de Lake Placid, avant de remporter le titre olympique.",
    "Aux Jeux de Mexico en 1968, les sprinteurs américains Tommie Smith et John Carlos lèvent un poing ganté de noir sur le podium du 200 m pour dénoncer le racisme. Le Blanc Peter Norman, deuxième, portait un badge de soutien.",
    "Le premier Paris-Dakar part le 26 décembre 1978 de Paris, à l'initiative de Thierry Sabine, qui s'était perdu dans le désert libyen lors d'un rallye.",
    "Le Marathon des Sables est né en 1986 sous l'impulsion de Patrick Bauer, qui avait traversé seul 350 km du désert du Sahara en transportant sa nourriture en 1984. La première édition a réuni 23 coureurs.",
    "L'Ultra-Trail du Mont-Blanc a été créé en 2003 : il fait le tour du massif en passant par la France, l'Italie et la Suisse, sur plus de 170 km et environ 10 000 m de dénivelé positif.",
    "La course d'ultra-trail Western States, aux États-Unis, est née en 1974 quand Gordy Ainsleigh, dont le cheval boitait pendant la course équestre Tevis Cup, a parcouru à pied les 100 miles en moins de 24 heures.",
    "La Barkley Marathons, course d'ultra-trail du Tennessee, s'inspire de l'évasion en 1977 de James Earl Ray de la prison de Brushy Mountain : il avait été repris après 55 heures de cavale, à seulement quelques kilomètres. Très peu de coureurs en sont venus à bout.",
    "En 2024, la Britannique Jasmin Paris devient la première femme à terminer la Barkley Marathons, avec moins de deux minutes d'avance sur la limite de temps de soixante heures.",
    "Terry Fox, amputé d'une jambe à cause d'un cancer, entreprend en 1980 son « Marathon de l'espoir » : il court d'est en ouest à travers le Canada, plus de 5 000 km en 143 jours, avant de devoir s'arrêter près de Thunder Bay.",
    "Le père et le fils Dick et Rick Hoyt ont terminé ensemble 32 marathons de Boston et six Ironman, le père courant, nageant ou pédalant pour entraîner son fils, atteint de paralysie cérébrale.",
    "En 2006, l'ultramarathonien Dean Karnazes a couru 50 marathons en 50 jours, un dans chaque État américain.",
    "En 1953, le 29 mai, le Néo-Zélandais Edmund Hillary et le sherpa Tenzing Norgay atteignent le sommet de l'Everest, à 8 849 m.",
    "En 1978, Reinhold Messner et Peter Habeler atteignent le sommet de l'Everest sans oxygène supplémentaire, ce que beaucoup de médecins jugeaient impossible.",
    "En 1986, Reinhold Messner devient le premier homme à gravir les quatorze sommets de plus de 8 000 mètres.",
    "Éric Tabarly remporte la Transat anglaise en 1964 sur Pen Duick II, devenant un héros national et lançant la voile de compétition en France.",
    "Le décathlon entre au programme olympique en 1912 à Stockholm, et Jim Thorpe en remporte le premier titre.",
    "Le mot « stade » vient du grec stadion, une unité de longueur d'environ 180 à 190 mètres, la longueur de la piste d'Olympie.",
    "Le premier championnat du monde d'athlétisme a lieu à Helsinki en 1983. Auparavant, les Jeux olympiques servaient de référence.",
    "Le premier Tour de France féminin officiel a lieu en 1984 ; il sera relancé sous le nom de Tour de France Femmes avec Zwift en 2022.",
    "Les premières baskets modernes datent de 1917 avec les Converse All Star, et le terme « sneaker » vient de leur semelle de caoutchouc silencieuse.",
    "Bill Bowerman, entraîneur d'athlétisme et cofondateur de Nike, aurait coulé du caoutchouc dans le gaufrier de sa femme au début des années 1970 pour créer la fameuse semelle « waffle ».",
    "Aux Jeux de Los Angeles en 1932, les temps sont pour la première fois mesurés au centième de seconde.",
    "La photo-finish a été utilisée pour la première fois aux Jeux olympiques de 1948 à Londres.",
    "Les blocs de départ apparaissent à la fin des années 1920 ; avant eux, les sprinteurs creusaient des trous dans la cendrée pour appuyer leurs pieds.",
]

# ---------------------------------------------------------------------------------------------
# ANECDOTES : histoires de sportifs et de courses
# ---------------------------------------------------------------------------------------------
ANECDOTES = [
    "Aux Jeux d'Helsinki en 1952, Emil Zátopek gagne le 5 000 m et le 10 000 m, puis s'aligne au marathon, qu'il n'avait jamais couru. Selon la légende, il demande à l'un des favoris si l'allure est assez rapide ; on lui répond qu'elle est trop lente, il accélère et gagne.",
    "Aux Jeux de Melbourne en 1956, Alain Mimoun remporte le marathon. Emil Zátopek, qui l'avait battu trois fois en 1948 et 1952 et finit sixième, est le premier à le féliciter.",
    "En 1992 à Barcelone, Derek Redmond se déchire les ischio-jambiers en demi-finale du 400 m. Son père descend des tribunes et l'aide à finir la course, sous les applaudissements de 65 000 spectateurs.",
    "Aux Jeux de Sydney en 2000, Eric Moussambani, de Guinée équatoriale, nage son 100 m nage libre seul, ses adversaires ayant été disqualifiés. Il avait appris à nager huit mois plus tôt. Il termine en 1 min 52 s 72, le plus lent de l'histoire olympique, sous les ovations.",
    "En 1988 à Calgary, le Britannique Eddie « l'Aigle » Edwards, seul sauteur à ski de son pays, termine dernier au tremplin de 70 m comme à celui de 90 m, et devient une star. Le CIO a depuis durci les critères de qualification.",
    "En 1988 à Calgary, l'équipe de bobsleigh de la Jamaïque, la première de son histoire, chute en bob à quatre. Son aventure a inspiré le film Rasta Rockett en 1993.",
    "Lors du 3 000 m des Jeux de Los Angeles en 1984, l'Américaine Mary Decker et la Sud-Africaine Zola Budd, qui courait pieds nus, entrent en contact. Decker tombe, Budd, huée, finit loin.",
    "Roger Bannister n'était pas coureur professionnel : étudiant en médecine, il ne s'entraînait qu'environ une demi-heure par jour. Ses lièvres, Chris Brasher et Chris Chataway, l'ont mené vers son record le 6 mai 1954.",
    "Eliud Kipchoge vit dans un camp d'entraînement austère à Kaptagat, au Kenya : les athlètes y font eux-mêmes leur ménage et leur cuisine, champion du monde compris.",
    "En 2005 au marathon de Londres, Paula Radcliffe s'arrête quelques secondes au bord de la route pour un besoin pressant, repart et gagne. L'image est devenue l'une des plus célèbres de la course.",
    "Raymond Poulidor n'a jamais porté le maillot jaune du Tour de France, mais il est monté huit fois sur le podium final et reste l'un des coureurs les plus aimés du public.",
    "En 1964 dans la montée du Puy de Dôme, Jacques Anquetil et Raymond Poulidor roulent « coude à coude » sur plusieurs kilomètres. Anquetil, qui aura résisté, remporte son cinquième Tour.",
    "En 1913, au Tour de France, Eugène Christophe casse sa fourche dans la descente du Tourmalet. Il marche jusqu'à un village, la répare lui-même dans une forge, mais reçoit dix minutes de pénalité car un enfant a actionné le soufflet.",
    "Pendant la Seconde Guerre mondiale, le champion cycliste italien Gino Bartali a caché des faux papiers dans le cadre de son vélo pour aider des Juifs persécutés, en prétextant ses entraînements. Il a été reconnu Juste parmi les nations en 2013.",
    "La photo de Fausto Coppi et Gino Bartali se passant un bidon d'eau lors du Tour de France 1952 est célèbre : personne n'a jamais su précisément qui tendait la bouteille à l'autre.",
    "Lors du Tour de France 1975, Eddy Merckx est frappé au foie par un spectateur dans la montée du Puy de Dôme. Il continue, mais doit abandonner son rêve d'un sixième Tour.",
    "En 1987, Greg LeMond est blessé par une cartouche de chevrotine pendant une partie de chasse, avec plusieurs dizaines de plombs dans le corps. Il revient et gagne le Tour de France en 1989, puis en 1990.",
    "En 1980, Bernard Hinault remporte Liège-Bastogne-Liège sous la neige, avec une avance d'environ neuf minutes. Il en ressort avec des doigts gelés, qui garderont des séquelles.",
    "Aux Jeux de Tokyo en 1964, l'Américain Billy Mills, un Lakota presque inconnu, remporte le 10 000 m par surprise en battant le record olympique.",
    "Haile Gebrselassie a grandi en courant dix kilomètres pour aller à l'école, et dix kilomètres pour revenir, avec ses livres sous le bras.",
    "Iten, au Kenya, à environ 2 400 m d'altitude, est surnommée « la ville des champions » : de nombreux athlètes de classe mondiale s'y entraînent ou en sont originaires.",
    "En 1986, l'Argentin Diego Maradona marque contre l'Angleterre en quart de finale de la Coupe du monde un but de la main, qu'il appellera « la main de Dieu », puis, quatre minutes plus tard, un but en solitaire après un slalom de soixante mètres, élu but du siècle.",
    "En 1950, le Brésil perd contre l'Uruguay 2-1 en finale décisive de la Coupe du monde au Maracanã, devant près de 200 000 spectateurs. Cette défaite est restée dans l'histoire sous le nom de « Maracanazo ».",
    "En 1954, l'Allemagne de l'Ouest bat la Hongrie 3-2 en finale de la Coupe du monde, le « miracle de Berne », alors que les Hongrois avaient gagné 8-3 contre elle en phase de poules.",
    "En 2016, le petit club anglais de Leicester City remporte le championnat d'Angleterre de football, alors que les bookmakers lui donnaient une chance sur cinq mille.",
    "En 1999, en finale de la Ligue des champions, Manchester United est mené 1-0 par le Bayern Munich jusqu'à la 90e minute, puis marque deux buts dans les arrêts de jeu, signés Sheringham et Solskjær.",
    "En 2005 à Istanbul, Liverpool est mené 3-0 à la mi-temps de la finale de la Ligue des champions contre l'AC Milan, égalise en six minutes en seconde période, puis gagne aux tirs au but.",
    "En 1958, Raymond Kopa devient le premier Français à recevoir le Ballon d'or, après sa saison au Real Madrid.",
    "En 1995, à Johannesburg, Nelson Mandela, vêtu du maillot des Springboks, remet la Coupe du monde de rugby au capitaine François Pienaar : un geste qui a marqué la réconciliation sud-africaine.",
    "En 1999, en demi-finale de la Coupe du monde de rugby, la France, menée 24-10 par les All Blacks, renverse la partie et gagne 43-31 à Twickenham.",
    "Le haka « Ka Mate » est exécuté par les équipes néo-zélandaises avant les matchs internationaux depuis la tournée des « Originals » en 1905.",
    "En 1973, la Américaine Billie Jean King bat Bobby Riggs 6-4, 6-3, 6-3 devant 90 millions de téléspectateurs lors de la « bataille des sexes », un match devenu un symbole de l'égalité dans le sport.",
    "En 1967, Muhammad Ali refuse d'être incorporé pour la guerre du Vietnam. Il est déchu de son titre de champion du monde et suspendu de boxe pendant plus de trois ans.",
    "En 1996 à Atlanta, Muhammad Ali, atteint de la maladie de Parkinson, allume la vasque olympique, dans l'un des moments les plus émouvants de l'histoire des Jeux.",
    "En 1997, Michael Jordan joue le cinquième match des finales de la NBA, malgré une forte gastro-entérite, et marque 38 points. Ce match est resté célèbre sous le nom de « flu game ».",
    "Au lycée, Michael Jordan n'a pas été retenu dans l'équipe première en deuxième année : il a joué avec l'équipe réserve avant de s'imposer l'année suivante.",
    "Le 22 janvier 2006, Kobe Bryant marque 81 points contre les Raptors de Toronto, la deuxième meilleure performance de l'histoire de la NBA après les 100 points de Wilt Chamberlain.",
    "En 1997, Tiger Woods remporte le Masters d'Augusta à 21 ans avec douze coups d'avance, le plus jeune vainqueur de l'histoire du tournoi.",
    "À Pékin en 2008, Michael Phelps remporte le 100 m papillon pour un centième de seconde devant Milorad Čavić, un écart que seule la plaque tactile permet de départager.",
    "En 1976 à Montréal, Nadia Comăneci obtient la première note de 10 de l'histoire de la gymnastique olympique. Le tableau d'affichage, qui n'avait que trois chiffres, affiche 1.00.",
    "En 1922, Alice Milliat organise à Paris les premiers Jeux mondiaux féminins, car les femmes étaient quasiment exclues des Jeux olympiques d'athlétisme.",
    "Le cœur de Pierre de Coubertin, mort en 1937, repose dans une stèle à Olympie, en Grèce.",
    "En 2017, Serena Williams gagne l'Open d'Australie alors qu'elle est enceinte de huit semaines, sans l'avoir annoncé.",
    "Rafael Nadal est naturellement droitier : c'est son oncle Toni, son entraîneur, qui l'a encouragé enfant à jouer de la main gauche pour en faire un atout.",
    "Après sa victoire à Wimbledon en 2011, Novak Djokovic a mangé un peu de l'herbe du court central, un geste devenu rituel.",
    "En 1904, le Tour de France est entaché de tricheries et de violences de supporters. Après enquête, les premiers du classement sont déclassés et Henri Cornet, cinquième sur la route, est déclaré vainqueur à 19 ans, le plus jeune de l'histoire.",
    "Au Tour de France 1903, la première étape part à 15 heures et se termine le lendemain matin : les coureurs roulent une nuit entière sur des routes non éclairées.",
    "En 1980 au marathon de Boston, Rosie Ruiz franchit la ligne d'arrivée comme première femme, mais on découvre qu'elle avait pris le métro pour sauter une partie du parcours. Elle est disqualifiée.",
    "En 1912 à Stockholm, le Japonais Shizo Kanakuri abandonne le marathon, épuisé, après avoir été invité dans un jardin par une famille suédoise. Il est resté officiellement « disparu » pendant 54 ans, jusqu'à ce qu'il termine la course lors d'une cérémonie en 1967.",
    "En 1904 à Saint-Louis, le marathon olympique se court par plus de 30 °C, et le vainqueur, l'Américain Thomas Hicks, a reçu pendant la course de la strychnine et du cognac. Le Cubain Félix Carvajal, facteur, s'est arrêté pour manger des pommes et finit quatrième.",
    "En 1904 toujours, deux Tswanas venus à l'Exposition universelle courent le marathon olympique. L'un d'eux, Len Taunyane, est pris en chasse par des chiens et doit faire un détour ; il termine neuvième.",
    "Le marathon de Boston, créé en 1897, est le plus ancien marathon annuel du monde.",
    "En 1970, Fred Lebow, un organisateur d'origine roumaine, lance le marathon de New York en quatre boucles dans Central Park. Il le fera passer dans les cinq quartiers de la ville en 1976.",
    "Pendant le marathon de Londres en 1981, Dick Beardsley et Inge Simonsen franchissent la ligne main dans la main, à égalité, sans se départager.",
    "Le Suédois Gösta Holmér a inventé le fartlek en 1937 : « jeu de vitesse », une façon d'alterner allures rapides et lentes au gré du terrain, sans chronomètre.",
    "Abebe Bikila, quand on lui demande pourquoi il court pieds nus à Rome en 1960, répond que les chaussures qu'on lui a données lui faisaient mal, et qu'il avait l'habitude de courir ainsi.",
]

# ---------------------------------------------------------------------------------------------
# ANECDOTES INSOLITES : sports étonnants, épreuves farfelues, objets et traditions
# ---------------------------------------------------------------------------------------------
INSOLITE = [
    "Le tir à la corde a été une épreuve olympique de 1900 à 1920. La Grande-Bretagne, la Suède et les États-Unis s'y sont partagé les médailles.",
    "Aux Jeux de Paris en 1900, une épreuve de cricket a opposé deux équipes seulement, la Grande-Bretagne et la France. Les Britanniques ont gagné et sont restés l'unique champion olympique de la discipline.",
    "De 1912 à 1948, les Jeux olympiques ont organisé des concours d'art : peinture, sculpture, architecture, littérature, musique. Pierre de Coubertin lui-même a remporté l'or en littérature en 1912, sous un pseudonyme, avec son « Ode au sport ».",
    "En 1900, la natation olympique comprenait une course d'obstacles dans la Seine : les nageurs devaient grimper sur des bateaux et passer dessous.",
    "La grimpe à la corde a été une épreuve olympique à plusieurs reprises entre 1896 et 1932.",
    "Entre 1900 et 1912, les Jeux comptaient des épreuves de saut en longueur et en hauteur sans élan, ainsi, en 1904, qu'un « plongeon pour la distance ».",
    "En Finlande, le championnat du monde de course en portant sa femme est une vraie compétition : le vainqueur reçoit son poids de sa partenaire en bière.",
    "À Cooper's Hill, en Angleterre, on lance chaque année un fromage de 3 à 4 kilos du haut d'une pente très raide, et des coureurs se précipitent à sa poursuite. Le fromage peut atteindre plus de 100 km/h.",
    "Au pays de Galles, le championnat du monde de « bog snorkelling » consiste à nager le plus vite possible dans un fossé de tourbe avec masque, tuba et palmes.",
    "Le « chessboxing » alterne des rounds de boxe et des parties d'échecs : on gagne par K.-O., par mat ou aux points.",
    "Le curling est surnommé « les échecs sur glace » en raison de sa part de stratégie.",
    "À Savonlinna, en Finlande, a lieu chaque année un championnat du monde de lancer de téléphone portable.",
    "En 1966, le trophée de la Coupe du monde de football, volé à Londres avant le tournoi, est retrouvé une semaine plus tard sous une haie par un chien nommé Pickles.",
    "En 1983, le trophée Jules Rimet, définitivement remis au Brésil après sa troisième victoire, a été volé à Rio de Janeiro. Il n'a jamais été retrouvé, fondu selon la police.",
    "La balle de golf compte entre 300 et 500 alvéoles. Elles lui permettent d'aller deux fois plus loin qu'une balle lisse : on l'a découvert en remarquant que les balles abîmées volaient mieux.",
    "Le ballon de rugby est ovale parce qu'il était à l'origine fabriqué avec des vessies de porc, gonflées à la bouche.",
    "Au hockey sur glace, la rondelle est conservée gelée avant le match pour qu'elle rebondisse moins.",
    "Une balle de baseball réglementaire comporte exactement 108 doubles coutures rouges.",
    "Les balles de tennis de Wimbledon étaient blanches jusqu'en 1986. Elles sont jaunes depuis, pour être mieux visibles à la télévision.",
    "Au tennis, le zéro se dit « love ». L'explication la plus répandue est qu'il vient du français « l'œuf », par ressemblance avec le zéro, mais l'origine reste débattue.",
    "À Wimbledon, plus de vingt tonnes de fraises sont servies chaque année pendant la quinzaine, avec de la crème.",
    "Le plus long match de cricket de l'histoire date de 1939 : un « test » entre l'Afrique du Sud et l'Angleterre a duré dix jours avant d'être arrêté, car l'équipe anglaise devait prendre le bateau du retour.",
    "La pétanque est née en 1907 à La Ciotat : Jules Lenoir, atteint de rhumatismes, ne pouvait plus courir pour lancer sa boule. On a inventé un jeu où l'on reste les pieds immobiles, les « pieds tanqués ».",
    "Le Mondial La Marseillaise à pétanque, créé en 1962, réunit chaque année des milliers de joueurs sur les allées de Marseille.",
    "Le ballon de football à 32 pièces, noir et blanc, a été conçu en 1970 pour être mieux repéré à la télévision en noir et blanc.",
    "La balle de ping-pong, au départ, s'appelait « Gossima », et le jeu portait le nom de « whiff-whaff ». Le nom « ping-pong » vient du bruit de la balle.",
    "Au début, les Jeux d'hiver n'existaient pas : le patinage artistique et le hockey sur glace étaient présentés aux Jeux d'été avant la création des Jeux d'hiver à Chamonix en 1924.",
    "Le sumo se pratique sur un cercle de 4,55 m de diamètre. Avant chaque combat, les lutteurs jettent du sel pour purifier l'aire.",
    "Le biathlon descend d'une tradition scandinave de chasse sur skis. Il est aux Jeux d'hiver depuis 1960.",
    "La planche à voile était un sport de plage de la région de Los Angeles dans les années 1960, avant de devenir olympique en 1984.",
    "Le skeleton, où l'on dévale une piste de glace à plat ventre la tête la première, tirerait son nom de la forme du traîneau, qui évoquait un squelette.",
    "Au ski de bosses, les skieurs enchaînent des virages sur une piste de bosses et des sauts. Le sport est devenu olympique en 1992 à Albertville.",
    "Le rugby à XIII est né en 1895 d'une scission du rugby, causée par un conflit sur le remboursement des journées de travail perdues par les joueurs ouvriers du nord de l'Angleterre.",
    "Au baseball, le « seventh-inning stretch » est une tradition : à la septième manche, les spectateurs se lèvent et chantent.",
    "Dans un match de rugby, le terme « mêlée » vient de « mêler » et désigne la poussée collective : les avants se lient en trois rangées, huit par équipe.",
    "Le mot « slalom » vient du norvégien slalåm, « piste en pente ». Le premier slalom officiel date de 1922 à Mürren, en Suisse.",
    "Le mot « marathon » est devenu un nom commun : on parle de « marathon de négociations », de « marathon de séries ». Le sport lui a prêté son nom, né d'une bataille gagnée en 490 av. J.-C.",
    "Selon l'explication la plus répandue, le mot « dopage » vient de « dop », un alcool que buvaient les guerriers zoulous, passé à l'anglais « dope ». Il désigne aujourd'hui toute substance ou méthode interdite pour améliorer la performance.",
    "Dans les courses de six jours sur piste, les coureurs se relaient jour et nuit pendant six jours, à l'origine en continu : le premier Six Jours de Paris date de 1913.",
    "Le Tour de France compte une étape appelée « étape reine » : la plus dure, souvent en haute montagne.",
    "Le « bidon » désigne en cyclisme la bouteille d'eau fixée au cadre. Le mot est entré dans l'argot sportif et se retrouve dans le « bidon » du coureur.",
    "À vélo, le « domestique » est le coureur qui se sacrifie pour son leader, en lui apportant à boire ou en l'abritant du vent. Le terme date du début du siècle dernier.",
    "Lors de Paris-Rouen en 1869, les participants roulent sur des vélocipèdes en bois et en fer, avec des pédales fixées sur la roue avant.",
    "Le mot « sprint » désigne une course courte à vitesse maximale. Il vient d'un verbe scandinave signifiant « jaillir ».",
    "En 1966, Bill Bowerman publie « Jogging », un livre né de ce qu'il a observé en Nouvelle-Zélande : des groupes de gens ordinaires qui trottent ensemble, sans compétition. Il a contribué à lancer le jogging aux États-Unis.",
    "Les premiers Jeux paralympiques d'hiver ont lieu en 1976 à Örnsköldsvik, en Suède.",
    "Le skateboard a fait son apparition aux Jeux de Tokyo en 2021, comme l'escalade sportive, le surf et le karaté. La breakdance est entrée au programme de Paris 2024.",
    "À Paris en 2024, les Jeux ont inauguré une cérémonie d'ouverture sur la Seine : les athlètes ont défilé en bateau, un fait sans précédent depuis 1896.",
]

SCIENCE = [
    "Le cœur d'un sportif d'endurance bien entraîné peut descendre à 35-45 battements par minute au repos : à chaque battement, il éjecte plus de sang qu'un cœur sédentaire.",
    "Un muscle ne grossit pas pendant la séance mais pendant la récupération : l'effort crée de microlésions, et c'est la réparation, nourrie par le repos et les protéines, qui renforce la fibre.",
    "La VO2 max désigne le volume maximal d'oxygène que l'organisme peut utiliser par minute et par kilo. Elle dépend à la fois de la génétique et de l'entraînement, et elle baisse lentement avec l'âge si l'on n'entretient pas.",
    "Les fibres musculaires lentes (type I) sont économes et résistantes, idéales pour l'endurance ; les rapides (type II) sont puissantes mais se fatiguent vite. La proportion de chacune est en grande partie héritée.",
    "Le « mur » du marathon correspond souvent à l'épuisement du glycogène, la réserve de glucides des muscles et du foie. S'alimenter pendant l'effort et bien s'entraîner à l'endurance repousse ce moment.",
    "Le corps humain stocke environ 2 000 kilocalories de glycogène, de quoi tenir à peu près 30 à 35 kilomètres à allure de marathon sans apport extérieur, très approximativement.",
    "Le sommeil est le premier outil de récupération : c'est pendant le sommeil profond que la sécrétion d'hormone de croissance est la plus importante.",
    "L'hydratation compte, mais boire trop est aussi un danger : l'hyponatrémie, une dilution du sodium dans le sang, a touché des marathoniens qui avaient bu bien au-delà de leur soif.",
    "La cadence idéale de course n'existe pas, mais beaucoup de coureurs efficaces tournent entre 170 et 190 foulées par minute. Augmenter légèrement sa cadence réduit souvent l'impact à chaque pas.",
    "Le principe de surcompensation explique qu'après un effort bien dosé et une récupération suffisante, le corps se reconstruit un peu au-dessus de son niveau de départ.",
    "La règle des 10 % — n'augmenter son volume hebdomadaire que d'environ 10 % — est une aide de bon sens, pas une loi scientifique. L'important, c'est la progressivité et l'écoute des signaux du corps.",
    "Un échauffement progressif augmente la température musculaire, accélère la conduction nerveuse et prépare les articulations. Il améliore la performance sans garantir à lui seul l'absence de blessure.",
    "La fréquence cardiaque maximale baisse avec l'âge, mais une formule comme « 220 moins l'âge » reste très approximative : l'écart individuel peut dépasser dix battements par minute.",
    "La variabilité de la fréquence cardiaque mesure les petits écarts de temps entre deux battements. Plus le système nerveux est reposé, plus elle est souvent élevée ; la fatigue la fait baisser.",
    "Les courbatures ne viennent pas de l'acide lactique, éliminé en une heure environ : elles proviennent des microlésions musculaires, surtout après des efforts excentriques comme une descente.",
    "Le lactate n'est pas un déchet : les muscles et le cœur l'utilisent comme carburant. Le seuil lactique est le niveau d'effort à partir duquel il s'accumule plus vite qu'il n'est évacué.",
    "La chaleur augmente nettement le coût d'un effort : le corps détourne du sang vers la peau pour se refroidir, ce qui fait grimper la fréquence cardiaque à allure égale. S'acclimater prend de 10 à 14 jours.",
    "En altitude, l'air contient autant d'oxygène mais à plus basse pression : le corps compense en produisant plus de globules rouges, un effet utilisé par de nombreux athlètes d'endurance.",
    "Un entraînement polarisé place environ 80 % du volume à faible intensité et 20 % à haute intensité. Beaucoup d'athlètes d'élite fonctionnent ainsi, avec peu de séances « moyennement dures ».",
    "Dormir moins de six heures par nuit pendant plusieurs jours dégrade les temps de réaction, la motivation et la récupération musculaire, même chez les sportifs aguerris.",
    "L'os est un tissu vivant qui se renforce avec les contraintes mécaniques : la course, les sauts et la musculation augmentent la densité osseuse, alors que la natation y contribue peu.",
    "Un muscle immobilisé commence à perdre de la force en quelques jours, mais la mémoire musculaire permet de retrouver un niveau perdu bien plus vite qu'il n'a été construit.",
    "Les glucides pendant l'effort permettent d'aller plus loin : les recommandations courantes vont de 30 à 60 grammes par heure, jusqu'à 90 grammes pour les athlètes entraînés à l'absorption digestive.",
    "Le tendon d'Achille peut supporter à la course plusieurs fois le poids du corps à chaque appui. Il s'adapte lentement, ce qui explique pourquoi il faut une progression prudente des volumes.",
    "Les chaussures à plaque carbone et mousse à haut rendement ont fait baisser les chronos de plusieurs pourcents d'économie de course en laboratoire, au point de réécrire de nombreux records.",
    "Pédaler à haute cadence sollicite plus le cœur et moins les muscles ; pédaler à basse cadence fait l'inverse. Les cyclistes expérimentés choisissent souvent 85 à 100 tours de pédale par minute.",
    "Dans l'eau, la traînée représente la majorité de l'effort du nageur : une bonne position à plat, la tête alignée, vaut parfois plus que mille mouvements de bras supplémentaires.",
    "Le cerveau limite l'effort bien avant l'épuisement physique : c'est la théorie du « gouverneur central », qui voit la fatigue comme une protection plus qu'une panne mécanique.",
    "Le café peut améliorer légèrement la performance d'endurance : une dose de 3 à 6 mg de caféine par kilo, prise une heure avant, est l'une des aides ergogéniques les mieux documentées.",
    "Le taper, ou affûtage, consiste à réduire le volume avant une compétition en maintenant un peu d'intensité. Il améliore souvent les performances de 2 à 3 % par rapport à une préparation sans repos.",
    "Les bonnes semaines d'entraînement incluent des semaines plus légères : toutes les trois ou quatre semaines, alléger le volume permet d'assimiler la charge au lieu de s'enliser.",
    "Courir en descente sollicite surtout les quadriceps en freinage, un effort dit excentrique : il produit peu de souffle mais beaucoup de dommages musculaires. D'où des courbatures parfois spectaculaires.",
    "La respiration nasale pendant un effort facile aide à rester dans une zone aérobie. Dès qu'on ne peut plus tenir une conversation, on passe en général au-dessus du premier seuil.",
    "Le renforcement musculaire réduit le risque de blessure et améliore l'économie de course, même chez les coureurs de fond. Deux séances hebdomadaires suffisent souvent à voir un effet.",
    "Un sportif adulte a besoin d'environ 1,2 à 2 grammes de protéines par kilo et par jour, répartis sur les repas, selon l'intensité de l'entraînement et les objectifs.",
    "L'effet des étirements avant l'effort est discuté : de longs étirements statiques juste avant une course peuvent légèrement diminuer la force, alors que des mouvements dynamiques préparent mieux.",
    "Le fer est essentiel au transport de l'oxygène. Une carence, plus fréquente chez les femmes et les sportifs d'endurance, provoque fatigue, essoufflement et baisse de performance, d'où l'intérêt d'un bilan.",
    "Les crampes à l'effort ne sont pas expliquées par une simple perte de sel : la fatigue neuromusculaire joue un rôle central, d'où leur apparition en fin de course, quand on dépasse son niveau habituel.",
    "L'entraînement par intervalles à haute intensité améliore la VO2 max plus vite que le footing facile, mais il demande bien plus de récupération. L'équilibre entre les deux fait les progrès durables.",
    "La température idéale pour courir un marathon se situe autour de 10 °C ; au-delà, chaque degré supplémentaire coûte quelques secondes par kilomètre, très approximativement.",
    "À vélo, la résistance de l'air représente l'essentiel de l'effort au-delà de 30 km/h. Se mettre en aspiration derrière un autre cycliste peut économiser jusqu'à 30 % d'énergie.",
    "La nage en eau libre en combinaison néoprène améliore la flottabilité et la vitesse de quelques secondes aux 100 mètres chez de nombreux nageurs, surtout ceux dont les jambes coulent.",
    "En triathlon, la transition d'un vélo à la course à pied donne souvent la sensation de « jambes de bois » : le corps doit changer de schéma moteur et réadapter la circulation du sang vers les muscles.",
    "Le glycogène se reconstitue plus vite dans la demi-heure à deux heures qui suivent l'effort. D'où le conseil de manger glucides et protéines assez tôt après une séance longue.",
    "La proprioception, la perception de la position du corps dans l'espace, s'entraîne : travailler l'équilibre sur une jambe réduit le risque d'entorse de cheville.",
    "Un coureur au sol de plus en plus fatigué raccourcit sa foulée et pose le pied plus longtemps : c'est pourquoi la technique de course se dégrade souvent en fin de marathon.",
    "Boire avant d'avoir soif est parfois conseillé en forte chaleur, mais le meilleur indicateur reste la soif elle-même. Une urine jaune clair est un repère simple pour l'hydratation au quotidien.",
    "Le muscle le plus puissant du corps humain, par sa taille, est le grand fessier : il extend la hanche et propulse la course, la montée et le saut. Le renforcer aide la performance.",
    "Après une séance d'effort, l'organisme continue de brûler un peu plus de calories pendant plusieurs heures : c'est l'effet « post-combustion », bien réel mais plus modeste qu'on ne le dit.",
    "La régularité l'emporte sur l'héroïsme : trois séances modérées par semaine pendant un an apportent plus de progrès que deux mois d'entraînement acharné suivis d'une blessure.",
    "La fatigue mentale réduit la performance physique : des études ont montré qu'un effort cognitif intense avant l'exercice rend la même allure plus pénible à tenir.",
    "Se visualiser en train de réussir son effort active en partie les mêmes zones du cerveau que l'effort réel. Beaucoup d'athlètes d'élite répètent mentalement leur course avant le départ.",
    "La musique accélère légèrement le rythme et rend l'effort perçu plus facile à intensité modérée : un tempo de 120 à 140 battements par minute convient bien au footing.",
    "Une course à pied de 30 minutes à intensité modérée suffit pour augmenter la sécrétion d'endorphines et de dopamine : c'est ce qu'on appelle parfois, un peu abusivement, le « runner's high ».",
    "Le renforcement du pied et de la cheville, en marchant pieds nus sur un sol sûr, développe de nombreux petits muscles et peut améliorer la stabilité du coureur.",
    "Le muscle contient environ 75 % d'eau : une perte de 2 % du poids du corps en sueur peut déjà diminuer sensiblement la performance en endurance.",
    "Lors d'un effort long, le corps brûle un mélange de graisses et de glucides : plus l'entraînement en endurance est régulier, plus la part de graisses utilisée à une allure donnée augmente.",
]

ADAGES = [
    ("Rien ne sert de courir ; il faut partir à point.", "Jean de La Fontaine, « Le Lièvre et la Tortue »"),
    ("Qui veut voyager loin ménage sa monture.", "proverbe français"),
    ("Petit à petit, l'oiseau fait son nid.", "proverbe français"),
    ("C'est en forgeant qu'on devient forgeron.", "proverbe français"),
    ("Un esprit sain dans un corps sain.", "Juvénal, « mens sana in corpore sano »"),
    ("Patience et longueur de temps font plus que force ni que rage.", "Jean de La Fontaine"),
    ("Celui qui a la santé a l'espoir, et celui qui a l'espoir a tout.", "proverbe arabe"),
    ("Le meilleur moment pour planter un arbre était il y a vingt ans. Le deuxième meilleur moment, c'est maintenant.", "proverbe chinois"),
    ("Un voyage de mille lieues commence toujours par un premier pas.", "Lao-tseu"),
    ("Tomber sept fois, se relever huit.", "proverbe japonais"),
    ("La fortune sourit aux audacieux.", "proverbe latin, « audentes fortuna iuvat »"),
    ("Mieux vaut tard que jamais.", "proverbe français"),
    ("On n'a rien sans rien.", "proverbe français"),
    ("À cœur vaillant rien d'impossible.", "Jacques Cœur, devise attribuée"),
    ("Ce qui ne me tue pas me rend plus fort.", "Friedrich Nietzsche"),
    ("La répétition est la mère de l'apprentissage.", "adage latin, « repetitio mater studiorum est »"),
    ("L'exercice est le meilleur des médecins.", "adage, souvent attribué à Hippocrate"),
    ("Mieux vaut prévenir que guérir.", "proverbe français"),
    ("Qui va piano va sano, qui va sano va lontano.", "proverbe italien"),
    ("Les petits ruisseaux font les grandes rivières.", "proverbe français"),
    ("Goutte à goutte, l'eau creuse la pierre.", "Ovide, « gutta cavat lapidem »"),
    ("Le courage n'est pas l'absence de peur, mais la capacité de la dépasser.", "Nelson Mandela"),
    ("Plutôt que de maudire l'obscurité, allume une bougie.", "proverbe chinois"),
    ("Ce n'est pas la montagne que l'on conquiert, mais soi-même.", "Edmund Hillary"),
    ("Le chemin est le but.", "proverbe zen"),
    ("Qui trop embrasse mal étreint.", "proverbe français"),
    ("Il faut cultiver son jardin.", "Voltaire, « Candide »"),
    ("À vaincre sans péril, on triomphe sans gloire.", "Pierre Corneille, « Le Cid »"),
    ("La nuit porte conseil.", "proverbe français"),
    ("Aide-toi, le ciel t'aidera.", "Jean de La Fontaine"),
    ("Pas de pain sans peine.", "proverbe français"),
    ("Celui qui déplace la montagne commence par déplacer de petites pierres.", "proverbe chinois, attribué à Confucius"),
    ("Il n'y a point de vent favorable pour qui ne sait où il va.", "Sénèque"),
    ("Ce qui compte n'est pas de gagner, mais de participer.", "devise olympique, d'après le discours de l'évêque Ethelbert Talbot en 1908"),
    ("Citius, altius, fortius : plus vite, plus haut, plus fort.", "devise olympique, proposée par Pierre de Coubertin et le père Henri Didon"),
    ("Qui court deux lièvres à la fois n'en prend aucun.", "proverbe français"),
    ("Après la pluie, le beau temps.", "proverbe français"),
    ("L'habitude est une seconde nature.", "proverbe, d'après Aristote"),
    ("Il vaut mieux faire que dire.", "proverbe français"),
    ("Le temps ne respecte pas ce qui se fait sans lui.", "proverbe français"),
    ("Un homme averti en vaut deux.", "proverbe français"),
    ("Le mieux est l'ennemi du bien.", "Voltaire"),
    ("Un tiens vaut mieux que deux tu l'auras.", "proverbe français"),
]

BLAGUES = [
    "Mon coach m'a dit de courir comme si quelqu'un me poursuivait. Alors j'ai couru… vers le frigo.",
    "Pourquoi le nageur est-il toujours de bonne humeur ? Parce qu'il est dans son élément.",
    "Le footing, c'est l'art de transpirer pour justifier le croissant d'après.",
    "Qu'est-ce qu'un triathlète à la boulangerie ? Quelqu'un qui hésite entre trois sports et un éclair.",
    "Pourquoi les coureurs aiment-ils les montres connectées ? Parce que si la course n'est pas sur Strava, elle n'a pas eu lieu.",
    "Mon plan d'entraînement est parfait. Il ne manque que mon entraînement.",
    "Le trail, c'est la preuve qu'on peut payer pour souffrir et dire merci à l'arrivée.",
    "Pourquoi le vélo ne tient-il pas debout tout seul ? Parce qu'il est deux-pneus fatigué.",
    "Un kilomètre, ça va. Dix kilomètres, bonjour la douleur. Quarante-deux, bonjour les amis.",
    "J'ai une excellente endurance : je peux rester sur mon canapé pendant des heures.",
    "Un cycliste entre dans un café : « Un expresso, s'il vous plaît, sans quoi je ne finis pas la côte. »",
    "Les gens disent que le sport, c'est la santé. Je réponds que le canapé, c'est la longévité.",
    "Au départ d'un marathon, tout le monde est optimiste. Au 35e kilomètre, tout le monde est philosophe.",
    "Le coureur à son entraîneur : « Je n'ai pas le temps de m'étirer. » L'entraîneur : « Alors vous aurez le temps d'être blessé. »",
    "Il y a deux types de coureurs : ceux qui disent aimer les côtes, et ceux qui sont honnêtes.",
    "Que dit un coureur qui se lève à 5 heures du matin ? « Je suis en pleine forme », et il se recouche à 5 heures et quart.",
    "Un entraîneur à son athlète : « Quand je dis de te donner à fond, ça ne veut pas dire de te donner à tout le monde. »",
    "Pourquoi le vélo est-il le meilleur ami de l'homme ? Parce que lui, au moins, il ne se plaint jamais dans les côtes.",
    "Mon podomètre a fait 10 000 pas aujourd'hui. Dont 8 000 vers le frigo.",
    "Pourquoi les coureurs de relais sont-ils sympathiques ? Parce qu'ils savent passer le témoin.",
    "Les trois étapes d'un triathlon : l'eau, la route, et le canapé.",
    "Mon coach me dit que la douleur est temporaire. Mon kiné me dit que la facture est permanente.",
    "Un cycliste à un autre : « Tu as vu mon nouveau vélo ? Il est tellement léger que je dois le retenir pour qu'il ne s'envole pas. »",
    "Le plus dur dans la course à pied, ce n'est pas le kilomètre 30. C'est la porte d'entrée.",
    "On dit que le sport donne de l'énergie. Moi, il me donne surtout faim.",
    "Le coureur à son miroir : « Je vois un champion. » Le miroir : « Je vois un type en retard pour sa séance. »",
    "Quelle est la différence entre un coureur du dimanche et un professionnel ? Le professionnel est payé pour avoir mal.",
    "Que dit le chronomètre au coureur ? « Je ne mens jamais, moi. »",
    "Mon objectif de la saison : arriver. Mon objectif de l'an prochain : arriver plus vite. Mon objectif de toujours : arriver avec un croissant.",
    "Quelle est la différence entre un coureur et un escargot ? L'escargot, lui, ne dit pas qu'il a battu son record.",
    "Dans un triathlon, il y a trois disciplines et une vraie question : où ai-je laissé mes lunettes de natation ?",
    "Pourquoi les sportifs aiment-ils les escaliers ? Parce qu'ils savent que le succès se gravit marche après marche.",
    "J'ai décidé de courir tous les jours. J'ai tenu la promesse pendant la première minute de mon premier jour.",
    "Le conseil d'un coureur à un débutant : « Commence doucement. » Le débutant : « Je suis déjà à 3 minutes au kilomètre de retard. »",
    "La différence entre un footing et un marathon ? Environ quarante kilomètres, et le droit de se plaindre.",
    "Que dit le sac de sport à son propriétaire ? « Tu m'as encore oublié dans le coffre. »",
    "Un coureur croise un ami : « Tu cours quelle distance ? » « Aucune, je suis en retard. »",
    "Il y a un secret pour finir un marathon : ne pas s'arrêter. Il y a un secret pour le commencer : s'inscrire avant d'avoir réfléchi.",
    "La séance de fractionné, c'est quand tu cours vite pour avoir le droit de marcher.",
    "Le footing du matin, c'est quand ton réveil sonne et que ton lit te retient par la main.",
    "Mon chronomètre et moi, on a un accord : il compte les secondes, je compte les excuses.",
    "Qu'est-ce qu'un coureur dit à sa montre GPS ? « Fais-moi croire que je suis rapide. »",
    "J'ai couru 5 km ce matin. Enfin, 3 en courant, 2 en marchant, et 1 à chercher mon souffle.",
]

DEVINETTES = [
    ("Combien de disciplines compte un triathlon classique ?", "Trois : natation, vélo et course à pied."),
    ("Quelle est la distance officielle d'un marathon ?", "42,195 kilomètres."),
    ("Dans quelle ville a eu lieu la première édition des Jeux olympiques modernes, en 1896 ?", "Athènes."),
    ("Quel est le pays d'origine du judo ?", "Le Japon."),
    ("Combien de joueurs compte une équipe de rugby à XV sur le terrain ?", "Quinze."),
    ("Quelle couleur porte le leader du Tour de France ?", "Le maillot jaune."),
    ("Combien de tours de piste dans un 5 000 mètres sur une piste de 400 mètres ?", "Douze tours et demi."),
    ("Quel est le sport qui se joue avec un volant ?", "Le badminton."),
    ("Quelle distance parcourt-on à la nage dans un Ironman ?", "3,8 kilomètres."),
    ("Combien de kilomètres à vélo dans un Ironman ?", "180 kilomètres."),
    ("Quel est le nom du plus célèbre col pyrénéen du Tour, haut de 2 115 mètres ?", "Le col du Tourmalet."),
    ("Dans quelle ville se déroule le marathon le plus ancien du monde, créé en 1897 ?", "Boston."),
    ("Quel athlète jamaïcain détient les records du monde du 100 et du 200 mètres ?", "Usain Bolt."),
    ("Combien de médailles d'or Michael Phelps a-t-il remportées aux Jeux olympiques ?", "Vingt-trois."),
    ("Quel est le nom de la célèbre course de montagne d'environ 170 kilomètres autour du massif du Mont-Blanc ?", "L'Ultra-Trail du Mont-Blanc."),
    ("De quelle couleur est le gazon du tournoi de Wimbledon ?", "Verte."),
    ("Quelle est la capitale du pays qui a organisé les Jeux de 2024 ?", "Paris."),
    ("Comment s'appelle le tournoi de tennis sur terre battue qui se joue à Paris ?", "Roland-Garros."),
    ("Quel est le sport où l'on pratique le « crawl », le « dos », la « brasse » et le « papillon » ?", "La natation."),
    ("Combien de points vaut un panier à trois points au basket ?", "Trois."),
    ("Combien y a-t-il d'anneaux sur le drapeau olympique ?", "Cinq."),
    ("Quel est le surnom des joueurs de l'équipe de France de football en 2018 ?", "Les Bleus."),
    ("Combien de joueurs par équipe sur un terrain de volley-ball ?", "Six."),
    ("Quel sport associe ski de fond et tir à la carabine ?", "Le biathlon."),
    ("Quel est le surnom donné au maillot du meilleur sprinteur du Tour de France ?", "Le maillot vert."),
    ("Je suis un outil de nageur : on m'enfile aux pieds pour aller plus vite. Qui suis-je ?", "Les palmes."),
    ("Combien de temps dure un match de football, hors arrêts de jeu ?", "Quatre-vingt-dix minutes."),
    ("Quelle est la discipline olympique où l'on court, saute et lance sur dix épreuves ?", "Le décathlon."),
    ("Quel pays a remporté le plus de Coupes du monde de football ?", "Le Brésil, avec cinq victoires."),
    ("Dans quel sport est-il question d'un « ace » ?", "Le tennis."),
    ("Quel est le nom du circuit où se court le Grand Prix de Formule 1 de Monaco ?", "Le circuit de Monaco, dans les rues de Monte-Carlo."),
    ("Quelle est la discipline du sport qui se pratique sur des skis et dans laquelle on s'élance depuis un tremplin ?", "Le saut à ski."),
    ("Dans quel sport peut-on faire un « strike » ?", "Le bowling."),
    ("Comment appelle-t-on l'épreuve de natation, de vélo puis de course à pied ?", "Le triathlon."),
    ("Quel nom donne-t-on à un coureur qui se place derrière un autre pour s'abriter du vent ?", "Il « prend la roue » ou « se met en aspiration »."),
    ("Dans quelle discipline utilise-t-on un « témoin » ?", "Le relais en athlétisme."),
    ("Combien de joueurs sur la glace pour une équipe de hockey, gardien compris ?", "Six."),
    ("Quelle matière compose la piste en tartan ?", "Une matière synthétique, à base de polyuréthane."),
    ("Quel est le sport national du Japon, avec des lutteurs de forte corpulence ?", "Le sumo."),
    ("Quel sport se pratique sur une table avec une balle de 40 mm ?", "Le tennis de table."),
    ("Quelle est la longueur d'un bassin olympique ?", "Cinquante mètres."),
    ("Quel est le nom de l'épreuve de ski où l'on descend entre des piquets ?", "Le slalom."),
    ("Dans quelle ville est né le mouvement olympique moderne, à l'initiative de Pierre de Coubertin ?", "Paris, avec le Congrès de la Sorbonne en 1894."),
]

CITATIONS += [
    ("Un champion se définit non pas par ses victoires, mais par sa capacité à se relever quand il tombe.", "attribué à Serena Williams"),
    ("L'esprit est tout. Les muscles ne sont que des morceaux de caoutchouc. Tout ce que je suis, je le dois à mon esprit.", "attribué à Paavo Nurmi"),
    ("Celui qui sait se dépasser quand l'effort devient douloureux est celui qui gagnera.", "attribué à Roger Bannister"),
    ("Le succès n'est pas un accident. C'est le travail acharné, la persévérance, l'étude, le sacrifice et surtout l'amour de ce que l'on fait.", "attribué à Pelé"),
    ("Il y a d'autres Annapurna dans la vie des hommes.", "Maurice Herzog, « Annapurna, premier 8 000 »"),
    ("Il faut être léger comme l'oiseau, et non comme la plume.", "Paul Valéry"),
    ("On ne se baigne jamais deux fois dans le même fleuve.", "Héraclite"),
    ("Le sport sérieux n'a rien à voir avec le fair-play : c'est la guerre, moins les coups de feu.", "George Orwell, « L'esprit sportif », 1945"),
    ("Le chemin vaut mieux que l'auberge.", "Miguel de Cervantès, « Don Quichotte »"),
    ("Le véritable voyage de découverte ne consiste pas à chercher de nouveaux paysages, mais à avoir de nouveaux yeux.", "Marcel Proust, « La Prisonnière »"),
    ("Le succès, c'est d'aller d'échec en échec sans perdre son enthousiasme.", "attribué à Winston Churchill"),
    ("Que vous pensiez pouvoir ou ne pas pouvoir, vous avez raison.", "attribué à Henry Ford"),
    ("Le golf est une bonne promenade gâchée.", "attribué à Mark Twain"),
    ("Il est honteux pour un homme de vieillir sans avoir vu de quoi son corps est capable.", "attribué à Socrate, d'après Xénophon"),
    ("Je préfère regretter les risques qui n'ont pas marché que les chances que je n'ai pas saisies.", "attribué à Simone Biles"),
    ("Je peux accepter l'échec, tout le monde échoue à quelque chose. Mais je ne peux pas accepter de ne pas essayer.", "attribué à Michael Jordan"),
    ("Faites de chaque jour votre chef-d'œuvre.", "John Wooden"),
    ("Le marathon est une affaire de mental autant que de jambes : il faut apprendre à parler à son corps sans l'écouter.", None),
]
CITATIONS = [c for c in CITATIONS if c[1]]

RECORDS += [
    "En octobre 2024 à Chicago, la Kényane Ruth Chepngetich devient la première femme à courir un marathon en moins de 2 h 10 min.",
    "Le marathon de Berlin, plat et rapide, a vu tomber de nombreux records du monde masculins et féminins depuis les années 2000.",
    "Le Britannique Mo Farah a remporté le 5 000 et le 10 000 mètres aux Jeux de Londres en 2012 puis de Rio en 2016 : un doublé répété sur deux olympiades.",
    "Le Tour de France compte souvent plus de 3 300 kilomètres sur environ vingt et une étapes, avec deux jours de repos pour les coureurs.",
    "Sur piste, l'Italien Filippo Ganna a battu en octobre 2022 le record de l'heure sur le vélodrome de Grenchen, en parcourant plus de 56 kilomètres.",
    "Le Suédois Armand Duplantis a porté à plusieurs reprises le record du monde du saut à la perche au-dessus de 6,20 m, centimètre après centimètre.",
    "Le Norvégien Karsten Warholm court le 400 mètres haies en 45 secondes et quelques centièmes, soit plus de huit mètres par seconde malgré dix haies à franchir.",
    "Michael Johnson a réalisé en 1996 le doublé 200-400 mètres aux Jeux d'Atlanta, avec un record du monde du 200 mètres à 19 s 32.",
    "Sur 100 mètres, un sprinteur de classe mondiale effectue environ 41 foulées, soit une foulée tous les 2,4 mètres.",
    "Au saut en longueur, le record du monde masculin de Mike Powell, 8,95 m, tient depuis 1991 : plus de trente-cinq ans sans que personne ne l'égale.",
    "Le record du monde du lancer du marteau féminin est détenu par la Polonaise Anita Włodarczyk, qui a dépassé 82 mètres.",
    "En 1987, la Soviétique Natalia Lisovskaya réalise un lancer de poids de plus de 22 mètres, un record qui tient toujours chez les femmes.",
]

ANECDOTES += [
    "Sir Mo Farah est né à Mogadiscio en Somalie, a grandi à Londres et est devenu quadruple champion olympique. Il a dit avoir découvert le sport à l'école grâce à un professeur de sport.",
    "Le nageur Duke Kahanamoku, champion olympique en 1912 et 1920, a fait connaître le surf à travers le monde, en le pratiquant lors de ses voyages.",
    "À 41 ans, Haile Gebrselassie courait encore des marathons, après avoir battu vingt-sept records du monde pendant sa carrière.",
    "Le skieur de fond norvégien Bjørn Dæhlie compte huit titres olympiques et douze médailles olympiques au total, un record pour les Jeux d'hiver à l'époque.",
    "La coureuse Joan Benoit remporte en 1984 le premier marathon olympique féminin, à Los Angeles, devant un stade acclamant sa foulée régulière.",
    "Vendée Globe, Route du Rhum, Transat Jacques Vabre : la voile française doit beaucoup à des marins comme Éric Tabarly, qui a inspiré toute une génération de navigateurs.",
    "L'alpiniste Reinhold Messner a gravi les quatorze sommets de plus de 8 000 mètres, sans oxygène artificiel, entre 1970 et 1986.",
    "Marie Marvingt, aviatrice, alpiniste, nageuse et cycliste, est surnommée « la fiancée du danger » et a tenté de s'inscrire au Tour de France cycliste en 1908.",
    "Le coureur Abebe Bikila a gagné le marathon olympique de Rome en 1960 pieds nus, puis celui de Tokyo en 1964 avec des chaussures.",
    "En 1936, Jesse Owens remporte quatre médailles d'or aux Jeux de Berlin, devant Adolf Hitler, au cœur d'une cérémonie conçue pour glorifier le régime nazi.",
]

INSOLITE += [
    "Sur la ligne de départ d'un marathon, les coureurs utilisent parfois des sacs-poubelles pour se protéger du froid, avant de les jeter quelques minutes après le coup de pistolet.",
    "Dans les courses cyclistes, on appelle « bidon » la bouteille qu'on lance aux spectateurs en fin de ravitaillement, devenue un souvenir très prisé des supporters.",
    "Les chaussures de running ont une durée de vie moyenne de 600 à 800 kilomètres, après quoi l'amorti s'affaisse même si l'extérieur paraît encore neuf.",
    "En 1971, l'astronaute Alan Shepard frappe deux balles de golf sur la Lune, avec un club de fortune et une combinaison épaisse.",
    "Le plus long match de tennis jamais joué, en 2010 à Wimbledon, a duré 11 heures et 5 minutes, entre l'Américain John Isner et le Français Nicolas Mahut, sur trois jours.",
    "Au baseball, une balle lancée à plus de 160 km/h met moins de 0,4 seconde pour atteindre le batteur, qui décide de frapper avant même de bien la voir.",
    "Sur un 10 km, la différence entre 42 minutes et 41 minutes représente seulement 6 secondes par kilomètre : de quoi montrer qu'une toute petite accélération suffit à changer de catégorie.",
    "Le premier sac à dos d'hydratation pour coureurs a été imaginé à la fin des années 1980 par Michael Eidson, un secouriste texan, pour pouvoir boire sans s'arrêter pendant une course cycliste.",
    "Les orteils d'un coureur de trail peuvent perdre leurs ongles après un long effort en descente : un souvenir de course que beaucoup de traileurs portent comme une médaille.",
]

HISTOIRE += [
    "Les Jeux olympiques modernes se sont tenus pour la première fois en 1896 à Athènes, avec 14 nations et environ 240 athlètes, tous des hommes.",
    "En 1900 à Paris, les femmes participent pour la première fois aux Jeux olympiques : la Britannique Charlotte Cooper devient la première championne olympique, en tennis.",
    "Le Tour de France est né en 1903, créé par le journal L'Auto pour relancer ses ventes. Le premier vainqueur est Maurice Garin.",
    "Le maillot jaune a été introduit en 1919 : il rappelle la couleur du papier sur lequel L'Auto était imprimé.",
    "La première édition des 24 Heures du Mans a lieu en 1923, sur un circuit de routes ouvertes à la circulation en dehors de la course.",
    "Le premier Ironman a lieu en 1978 à Hawaï avec quinze participants, dont douze ont franchi la ligne. Le vainqueur est Gordon Haller.",
    "Le triathlon est entré au programme des Jeux olympiques à Sydney, en 2000.",
    "Le premier championnat du monde d'athlétisme a lieu à Helsinki en 1983.",
    "Les Jeux olympiques d'hiver ont commencé en 1924 à Chamonix, en France, sous l'appellation de « Semaine internationale des sports d'hiver ».",
    "Le basket-ball a été inventé en 1891 par James Naismith, qui avait accroché des paniers à pêches à une balustrade de gymnase.",
    "Le volley-ball a été inventé en 1895 par William G. Morgan, aux États-Unis, comme une alternative moins brutale au basket-ball.",
    "Le rugby aurait été inventé en 1823 par William Webb Ellis qui, au collège de Rugby, se serait mis à courir avec le ballon dans les mains. L'anecdote est contestée par les historiens.",
    "Le football moderne naît à Londres en 1863, avec la fondation de la Football Association et la rédaction des premières règles communes.",
    "La première Coupe du monde de football a lieu en 1930 en Uruguay, qui l'emporte à domicile devant l'Argentine.",
    "Les Jeux paralympiques d'été sont nés à Rome en 1960, sous l'impulsion du docteur Ludwig Guttmann, qui avait organisé les premiers jeux pour blessés de guerre à Stoke Mandeville en 1948.",
    "La première ascension de l'Everest, en 1953, est réussie par Edmund Hillary et Tenzing Norgay, qui atteignent le sommet le 29 mai.",
    "Le premier homme à avoir couru un mile en moins de quatre minutes est Roger Bannister, en 3 min 59 s 4, le 6 mai 1954 à Oxford.",
    "Les Jeux de Mexico en 1968 ont marqué l'histoire du saut en longueur avec le bond de Bob Beamon à 8,90 m, qui a dépassé l'ancien record de près de 55 centimètres.",
    "Les premiers Championnats du monde de cyclisme sur route ont eu lieu en 1921 à Copenhague.",
    "Le Tour de France féminin, interrompu pendant des décennies, a retrouvé sa place avec « Tour de France Femmes avec Zwift » en 2022.",
    "L'Ultra-Trail du Mont-Blanc, créé en 2003, est devenu l'un des rendez-vous majeurs du trail mondial, avec plusieurs courses réparties sur une semaine à Chamonix.",
    "Le slalom en ski alpin a été inventé par le Britannique Arnold Lunn, qui organise la première épreuve en 1922 à Mürren, en Suisse.",
    "Les Jeux de Moscou en 1980 et de Los Angeles en 1984 ont été boycottés en pleine guerre froide : plus de soixante pays absents à Moscou, une quinzaine à Los Angeles.",
    "En 1900 et 1904, les épreuves des Jeux olympiques ont duré plusieurs mois, étalées sur toute la durée de l'Exposition universelle.",
    "Le premier marathon moderne a été couru lors des Jeux d'Athènes en 1896, remporté par le Grec Spyridon Louis en 2 h 58 min.",
    "Le tennis de table a été popularisé en Angleterre à la fin du XIXe siècle comme jeu de salon, sous le nom de « ping-pong ».",
    "Le judo a été fondé par Jigoro Kano en 1882 au Japon, qui voulait en faire une pratique d'éducation physique et morale.",
    "Le marathon féminin est devenu olympique en 1984, après des années de campagne de coureuses comme Kathrine Switzer.",
]


# ---------------------------------------------------------------------------
# Bibliothèque unifiée et sélection du jour
# ---------------------------------------------------------------------------
def _build():
    lib, seen = [], set()

    def add(kind, text, author=None, answer=None):
        key = " ".join(text.split()).lower()
        if key in seen:
            return
        seen.add(key)
        lib.append({"kind": kind, "label": KIND_LABEL[kind], "text": text.strip(),
                    "author": author, "answer": answer})

    for t, a in CITATIONS:
        add("citation", t, a)
    for kind, items in (("record", RECORDS), ("histoire", HISTOIRE), ("anecdote", ANECDOTES),
                        ("insolite", INSOLITE), ("science", SCIENCE), ("blague", BLAGUES)):
        for t in items:
            add(kind, t)
    for t, a in ADAGES:
        add("adage", t, a)
    for q, r in DEVINETTES:
        add("devinette", q, None, r)
    return lib


LIB = _build()
N = len(LIB)
GAP = 60                     # aucune entrée ne revient avant 60 jours
EPOCH = date(2026, 1, 1).toordinal()
_PERM = {}


def _perm(c):
    """Ordre des N entrées pour le cycle c (mémoïsé, déterministe)."""
    if c in _PERM:
        return _PERM[c]
    order = list(range(N))
    random.Random(f"petit-plus-{c}").shuffle(order)
    tail = set(_perm(c - 1)[-(GAP - 1):]) if c > 0 else set()
    # 1) aucune entrée de la fin du cycle précédent dans les GAP-1 premières places
    head = order[:GAP - 1]
    bad = [x for x in head if x in tail]
    if bad:
        rest = [x for x in order if x not in bad]
        k = len(rest) - (GAP - 1)
        order = rest[:GAP - 1] + [x for x in rest[GAP - 1:]]
        # réinsère les entrées écartées après la zone sensible, à des places pseudo-aléatoires
        rnd = random.Random(f"petit-plus-ins-{c}")
        for x in bad:
            order.insert(rnd.randint(GAP - 1, len(order)), x)
    # 2) pas plus de deux entrées de même nature d'affilée (échange vers l'avant)
    def ok_at(pos, idx):
        return not (pos < GAP - 1 and idx in tail)
    for i in range(2, N):
        if LIB[order[i]]["kind"] == LIB[order[i - 1]]["kind"] == LIB[order[i - 2]]["kind"]:
            for j in range(i + 1, N):
                if LIB[order[j]]["kind"] != LIB[order[i]]["kind"] and ok_at(i, order[j]):
                    order[i], order[j] = order[j], order[i]
                    break
    _PERM[c] = order
    return order


def du_jour(day=None):
    """Entrée du jour, identique pour toutes les périodes glissantes.
    `day` : date, chaîne ISO « AAAA-MM-JJ » ou None (aujourd'hui)."""
    if day is None:
        day = date.today()
    elif isinstance(day, str):
        day = date.fromisoformat(day[:10])
    n = day.toordinal() - EPOCH
    c, i = divmod(n, N)
    if c < 0:                              # dates antérieures au 01/01/2026 : sans contrainte de raccord
        order = list(range(N))
        random.Random(f"petit-plus-{c}").shuffle(order)
    else:
        order = _perm(c)
    e = LIB[order[i]]
    return {"kind": e["kind"], "label": e["label"], "text": e["text"],
            "author": e["author"], "answer": e["answer"]}
