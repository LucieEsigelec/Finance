# Cahier des charges fonctionnel (CdCF v2.0)

> Transcription texte du PDF du groupe, mise en page conservée. Le document de référence est `sources/01_cahier_des_charges_v2.pdf` : en cas de doute (tableaux), lire le PDF.

```text
     CAHIER DES CHARGES FONCTIONNEL (CdCF)

     Application d'aide à la décision pour la gestion active d'un
     portefeuille actions de 500 000 €
     Version 2.0 • Recueil des besoins client intégré • 24 novembre 2026




                                                                              Garde-fou
    Capital à investir    Horizon de placement      Profil de risque                                Univers cible
                                                                              hebdomadaire

                          1 an (allers-retours      Élevé (objectif ~10 % /   Perte max 10 % /
    500 000 €                                                                                       5 actions CAC 40
                          actifs)                   sem.)                     semaine




1. Contexte, profil client et objectifs

1.1 Contexte et profil de l'investisseur
Le client dispose d'un capital de 500 000 € à investir en bourse et possède déjà une expérience préalable de
l'investissement. Il n'a pas besoin de disposer de ces fonds à court terme et se positionne sur un horizon de
placement d'un an.
Son profil est clairement orienté vers une gestion active et dynamique :
•      Objectif principal : maximiser la croissance du capital en réalisant de nombreux allers-retours (achats et
       reventes fréquents).
•      Profil de risque : risque élevé, avec une dynamique de performance visée autour de 10 % sur une semaine.
•      Garde-fou financier : la perte maximale tolérée est fixée à 10 % sur une semaine (soit 50 000 € sur le capital
       initial de 500 000 €).
•      Posture utilisateur : le client ne souhaite pas manipuler la mécanique mathématique du modèle, mais
       disposer d'une interface soignée lui permettant d'investir lui-même et d'effectuer ses allers-retours en
       s'appuyant sur des conseils argumentés.

1.2 Livrables du projet
Ce document constitue le premier des quatre livrables attendus dans le cadre du projet :
1. Cahier de charges (présent document) : expression du besoin client, périmètre fonctionnel et règles de
   gestion.
2. Dossier de conception : architecture logicielle, flux de données et modèle de base de données.
3. Dossier de spécification : formules des indicateurs, algorithmes de pondération, prévision hebdomadaire et
   maquettes d'interfaces.
4. Applications : outil exécutable répondant aux besoins d'investissement actif du client.


2. Univers d'investissement et périmètre

2.1 Panier de valeurs
Le portefeuille de 500 000 € porte sur les 5 actions françaises suivantes :

    Action                       Ticker (Euronext Paris)   Secteur                        Remarque client

--- page suivante ---
                                                   Cahier des Charges Fonctionnel | Gestion active de portefeuille actions (500 000 €)


 Action                          Ticker (Euronext Paris)     Secteur                            Remarque client

                                                                                                Valeur spécifiquement citée
 Dassault Systèmes               DSY.PA                      Logiciels industriels
                                                                                                par le client

 Hermès                          RMS.PA                      Luxe                               —

 Capgemini                       CAP.PA                      Services numériques / IT           —

 Air Liquide                     AI.PA                       Gaz industriels / Chimie           —

 TotalEnergies (TOTAL)           TTE.PA                      Énergie / Pétrole & Gaz            —



2.2 Périmètre et hors périmètre

 Inclus dans le périmètre (V1)                                      Hors périmètre (V1)

 Aide à la décision argumentée (Achat, Vente, Rien) sur les
                                                                    Passage d'ordres automatisé connecté à un courtier réel
 5 valeurs

 Prévision des variations sur un horizon hebdomadaire (1            Gestion fiscale automatisée (PEA / Compte-Titres
 semaine)                                                           Ordinaire)

 Simulation interactive d'allers-retours (choix d'action +
                                                                    Produits dérivés, effet de levier ou cryptomonnaies
 montant)

 Estimation des dividendes et veille d'informations par             Modification manuelle des formules du modèle par le
 action                                                             client final




3. Moteur d'aide à la décision (en coulisses)
Bien que le client n'interagisse pas avec les formules internes, l'application s'appuie sur un moteur de scoring et
de prévision hebdomadaire combinant quatre piliers pondérés, dont le pilier Informations détient le poids le
plus important :

 Pilier                       Priorité                Indicateurs intégrés

                                                      Actualités financières, annonces d'entreprises, contexte sectoriel et
 1. Informations              Pilier majoritaire
                                                      score d'impact récent.

                                                      Tendances, Moyennes Mobiles, MACD, Bandes de Bollinger, RSI
 2. Analyse graphique         Pondéré
                                                      (calibrés pour capter les mouvements court terme / hebdomadaires).

 3. Ratios financiers         Pondéré                 Chiffre d'affaires (CA), dividende par action, rendement.

                                                      Facteur aléatoire contrôlé simulant l'imprévisibilité des marchés sur
 4. Hasard                    Pondéré
                                                      une semaine.




4. Exigences fonctionnelles de l'application

4.1 Tableau de bord principal et vue globale des 5 actions
L'interface doit être esthétique, fluide et lisible, et proposer dès l'écran d'accueil :

                                                                                                             Version 2.0 • Page 2 / 4

--- page suivante ---
                                                    Cahier des Charges Fonctionnel | Gestion active de portefeuille actions (500 000 €)

•        Suivi du capital : visualisation du capital total (500 000 €), de la part investie, des liquidités disponibles et de
         la performance hebdomadaire (avec indicateur d'alerte par rapport au seuil de -10 %).
•        Recommandations complètes : affichage des 5 actions avec, pour chacune d'entre elles, une
         recommandation couvrant toutes les possibilités : Achat, Vente ou Rien (conserver / attendre).
•        Prévision hebdomadaire : estimation de la variation attendue sur la semaine pour chaque titre.

4.2 Module interactif « Simulateur de décision / Aller-retour »
Pour répondre au souhait du client d'investir lui-même et d'effectuer des allers-retours, l'application intègre un
parcours d'interaction direct en quatre étapes :
5. Sélection : l'utilisateur coche une ou plusieurs actions parmi les 5 proposées.
6. Montant : l'utilisateur saisit le montant en euros qu'il envisage d'investir (ou de vendre).
7. Conseil et argumentation : l'algorithme évalue instantanément l'opération proposée et retourne un conseil
   clair (valider l'achat, privilégier la vente ou ne rien faire) accompagné des raisons détaillées issues des 4
   piliers.
8. Exécution simulée : l'utilisateur peut valider l'aller-retour dans son portefeuille virtuel pour suivre ses
   positions sur l'horizon d'un an.

4.3 Fiche détaillée par action (avec onglet Informations)
En cliquant sur n'importe laquelle des 5 valeurs (dont Dassault Systèmes), l'utilisateur accède à une vue dédiée
comprenant :
•        Bloc Recommandation & Argumentaire : si le signal est à l'achat (ou à la vente), l'application explique de
         manière synthétique pourquoi (actualité positive, signal RSI/MACD, dynamique de tendance, etc.).
•        Prévision hebdomadaire : projection de la variation attendue sur la semaine à venir (scénario favorable,
         central et défavorable).
•        Estimation des dividendes : calcul automatique du dividende estimé par action et du montant total attendu
         selon le capital engagé sur le titre.
•        Onglet « Infos sur l'action » : espace dédié regroupant les actualités clés, le profil de l'entreprise, son chiffre
         d'affaires, son rendement et l'impact des dernières informations sur le score.


5. Règles de gestion clés

    ID            Règle de gestion                Description

                                                  Si la perte latente ou réalisée sur une semaine approche ou atteint 10 %
                  Alerte perte maximale
    RG-01                                         (soit 50 000 € sur 500 000 €), le système déclenche une alerte visuelle
                  hebdomadaire
                                                  prioritaire et recommande un allègement ou une vente.

                                                  Pour chacune des 5 actions, le moteur doit systématiquement statuer
    RG-02         Exhaustivité des décisions
                                                  parmi les 3 états : Achat, Vente ou Rien.

                                                  Aucune recommandation (en particulier à l'achat ou lors d'une saisie action
    RG-03         Obligation d'argumentation      + montant) ne peut être affichée sans ses raisons justificatives lisibles en
                                                  langage clair.

                                                  Dans le calcul interne du modèle, le poids du pilier Informations reste
                  Prépondérance des
    RG-04                                         strictement supérieur à celui de l'analyse graphique, des ratios et du
                  informations
                                                  hasard.

                                                  Le montant engagé sur une opération ne peut excéder les liquidités
                  Cohérence budgétaire et
    RG-05                                         disponibles ; le nombre d'actions est calculé en titres entiers et le reliquat
                  titres entiers
                                                  reste en cash.


                                                                                                              Version 2.0 • Page 3 / 4

--- page suivante ---
                                                     Cahier des Charges Fonctionnel | Gestion active de portefeuille actions (500 000 €)


    ID            Règle de gestion                Description

                                                  Les historiques de performance, d'allers-retours et d'estimation de
    RG-06         Horizon de suivi
                                                  dividendes sont consolidés sur un horizon glissant de 1 an.




6. Exigences non fonctionnelles et critères d'acceptation

6.1 Exigences non fonctionnelles
•        Ergonomie et design : interface moderne, épurée et intuitive (« jolie »), masquant la complexité
         mathématique (MACD, Bollinger, pondérations) derrière des explications compréhensibles.
•        Réactivité : le conseil et l'argumentaire après sélection d'une action (case à cocher) et saisie d'un montant
         doivent s'afficher en moins de 2 secondes.
•        Transparence : affichage systématique d'une mention précisant que les prévisions hebdomadaires et les
         conseils constituent des outils d'aide à la décision ne garantissant pas les performances futures.

6.2 Critères de recette fonctionnelle (Validation)
L'application sera considérée comme validée lorsque les quatre scénarios suivants seront concluants :
9. Vue des 5 valeurs : Hermès, Capgemini, Air Liquide, Dassault Systèmes et TotalEnergies affichent chacune
    une recommandation (Achat, Vente ou Rien), une prévision de variation sur la semaine et une estimation de
    dividende.
10. Parcours interactif : l'utilisateur peut cocher une action, saisir un montant, obtenir immédiatement un
    conseil argumenté par l'algorithme et enregistrer des allers-retours dans son portefeuille de 500 000 €.
11. Fiche valeur et transparence : chaque fiche dispose d'un onglet d'informations dédié et justifie
    explicitement toute recommandation d'achat.
12. Contrôle du risque : le garde-fou RG-01 se déclenche correctement dès qu'une simulation de baisse atteint -
    10 % sur une semaine.

    Avertissement de conformité
    L'application spécifiée dans ce Cahier des Charges est un outil d'aide à la décision et de simulation. Les prévisions
    hebdomadaires, recommandations et estimations de dividendes ne constituent pas un conseil en investissement
    financier réglementé et ne garantissent en aucun cas les performances futures.




                                                                                                               Version 2.0 • Page 4 / 4

--- page suivante ---

```
