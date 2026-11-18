/* Atelier de code : Python s'exécute dans le navigateur de l'apprenant, jamais sur le serveur.
 *
 * Un fichier .py s'édite et s'exécute d'un bloc ; un carnet .ipynb s'ouvre cellule par cellule, et
 * chaque cellule s'exécute dans le même interpréteur, dans l'ordre que l'apprenant choisit — c'est
 * Jupyter, sans serveur et sans installation. La lecture du format vit dans carnet.js.
 *
 * Le serveur ne fait que remettre les fichiers du dépôt du jour. Ce que l'apprenant écrit reste
 * sur sa machine : le brouillon est gardé dans le stockage local du navigateur, et rien n'est
 * renvoyé. L'exécution a donc lieu hors du site, dans le bac à sable du moteur WebAssembly.
 */
(function () {
  "use strict";

  var PYODIDE = "https://cdn.jsdelivr.net/pyodide/v0.28.3/full/";
  var DOSSIER = "/depot";
  var elements = {};
  var fichiers = [];
  var ouvert = null;
  var python = null;
  var lecon = window.atelier_lecon || "";
  var cellules = [];  // cellules du carnet ouvert ; vide dès qu'un fichier de code est ouvert
  var execution = 0;  // compteur d'exécutions du carnet, affiché dans l'invite In [n]
  var paquetsDuDepot = null;  // promesse unique du chargement des paquets dont le dépôt dépend

  function texte(valeur) {
    return String(valeur === undefined || valeur === null ? "" : valeur);
  }

  function etat(message, erreur) {
    elements.etat.textContent = message;
    elements.etat.classList.toggle("erreur", Boolean(erreur));
  }

  function ecrire(message) {
    elements.sortie.textContent += texte(message) + "\n";
    elements.sortie.scrollTop = elements.sortie.scrollHeight;
  }

  function vider() {
    elements.sortie.textContent = "";
  }

  function cle(nom) {
    return "atelier:" + lecon + ":" + nom;
  }

  function brouillon(nom, contenu) {
    try {
      var garde = window.localStorage.getItem(cle(nom));
      return garde === null ? contenu : garde;
    } catch (erreur) {
      return contenu;
    }
  }

  function garder(nom, contenu) {
    try {
      window.localStorage.setItem(cle(nom), contenu);
    } catch (erreur) {
      /* stockage plein ou refusé : le travail reste à l'écran, rien de plus à faire */
    }
  }

  function estCarnet(fichier) {
    return Boolean(fichier) && fichier.nom.endsWith(".ipynb");
  }

  function enregistrerOuvert() {
    /* Un carnet se garde cellule par cellule, à la frappe : rien à reprendre dans la zone de texte. */
    if (!ouvert || estCarnet(ouvert)) { return; }
    ouvert.contenu = elements.code.value;
    garder(ouvert.nom, ouvert.contenu);
  }

  function garderCarnet() {
    if (!ouvert) { return; }
    try {
      ouvert.contenu = window.Carnet.ecrire(ouvert.contenu, cellules);
    } catch (erreur) {
      return;  /* carnet illisible : il n'était pas affiché, il n'y a rien à garder */
    }
    garder(ouvert.nom, ouvert.contenu);
  }

  function hauteur(zone) {
    zone.rows = Math.min(40, Math.max(2, zone.value.split("\n").length));
  }

  function corpsDe(enfants) {
    var corps = document.createElement("div");
    corps.className = "cellule-corps";
    enfants.forEach(function (enfant) { corps.appendChild(enfant); });
    return corps;
  }

  function blocPresentation(cellule) {
    var texteRendu = document.createElement("div");
    texteRendu.className = "presentation";
    /* contenu échappé par Carnet.html : un carnet est une donnée, pas du code de la page */
    texteRendu.innerHTML = window.Carnet.html(cellule.source);
    var invite = document.createElement("div");
    invite.className = "invite";  // colonne vide, pour que le texte s'aligne sur le code
    var pile = document.createDocumentFragment();
    pile.appendChild(invite);
    pile.appendChild(corpsDe([texteRendu]));
    return pile;
  }

  function blocCode(cellule) {
    var invite = document.createElement("div");
    invite.className = "invite";
    var numero = document.createElement("span");
    numero.className = "invite-entree";
    numero.textContent = "In [ ]:";
    var lancer = document.createElement("button");
    lancer.type = "button";
    lancer.className = "lancer";
    lancer.title = "Exécuter cette cellule";
    lancer.setAttribute("aria-label", "Exécuter la cellule " + (cellule.rang + 1));
    lancer.textContent = "▶";
    lancer.addEventListener("click", function () { executerCellule(cellule); });
    invite.appendChild(numero);
    invite.appendChild(lancer);

    var zone = document.createElement("textarea");
    zone.className = "zone-code";
    zone.spellcheck = false;
    zone.value = cellule.source;
    hauteur(zone);
    zone.addEventListener("keydown", tabulation);
    zone.addEventListener("input", function () {
      cellule.source = zone.value;
      hauteur(zone);
      garderCarnet();
    });

    var sortie = document.createElement("pre");
    sortie.className = "cellule-sortie";
    sortie.hidden = true;

    cellule.zone = zone;
    cellule.sortie = sortie;
    cellule.lancer = lancer;
    cellule.numero = numero;

    var pile = document.createDocumentFragment();
    pile.appendChild(invite);
    pile.appendChild(corpsDe([zone, sortie]));
    return pile;
  }

  function afficherCarnet() {
    elements.code.hidden = true;
    elements.carnet.hidden = false;
    elements.carnet.textContent = "";
    elements.executer.textContent = "Exécuter tout le carnet";
    /* le carnet prend le fond sombre et toute la largeur : c'est un carnet, pas un éditeur de
     * fichier avec sa console à côté, et la sortie de chaque cellule tient sous la cellule */
    document.body.classList.add("carnet-ouvert");
    try {
      cellules = window.Carnet.lire(ouvert.contenu);
    } catch (erreur) {
      cellules = [];
      etat(texte(erreur.message || erreur), true);
      return;
    }
    cellules.forEach(function (cellule) {
      var article = document.createElement("article");
      article.className = "cellule cellule-" + cellule.type;
      article.appendChild(cellule.type === "code" ? blocCode(cellule) : blocPresentation(cellule));
      elements.carnet.appendChild(article);
    });
  }

  function afficherFichier() {
    cellules = [];
    document.body.classList.remove("carnet-ouvert");
    elements.carnet.hidden = true;
    elements.carnet.textContent = "";
    elements.code.hidden = false;
    elements.executer.textContent = "Exécuter le fichier";
    elements.code.value = ouvert ? ouvert.contenu : "";
  }

  function charger(nom) {
    enregistrerOuvert();
    ouvert = fichiers.filter(function (f) { return f.nom === nom; })[0] || null;
    if (estCarnet(ouvert)) { afficherCarnet(); } else { afficherFichier(); }
    Array.prototype.forEach.call(elements.liste.querySelectorAll("button"), function (bouton) {
      bouton.setAttribute("aria-current", bouton.dataset.nom === nom ? "true" : "false");
    });
  }

  function lister() {
    elements.liste.textContent = "";
    fichiers.forEach(function (fichier) {
      var ligne = document.createElement("li");
      var bouton = document.createElement("button");
      bouton.type = "button";
      bouton.textContent = fichier.nom;
      bouton.dataset.nom = fichier.nom;
      bouton.addEventListener("click", function () { charger(fichier.nom); });
      ligne.appendChild(bouton);
      elements.liste.appendChild(ligne);
    });
  }

  function premierProgramme() {
    /* Le carnet est le fil de la séance : s'il y en a un, c'est lui qui s'ouvre. */
    var carnets = fichiers.filter(function (f) { return f.nom.endsWith(".ipynb"); });
    if (carnets.length) { return carnets[0].nom; }
    var candidats = fichiers.filter(function (f) {
      return f.nom.endsWith(".py") && f.nom.indexOf("tests/") !== 0;
    });
    return candidats.length ? candidats[0].nom : (fichiers[0] || {}).nom;
  }

  function appeler(methode, parametres) {
    var adresse = "/api/method/" + methode + "?" + new URLSearchParams(parametres).toString();
    return fetch(adresse, {
      credentials: "same-origin",
      headers: { Accept: "application/json", "X-Frappe-CSRF-Token": window.csrf_token || "" }
    }).then(function (reponse) {
      if (!reponse.ok) {
        throw new Error(reponse.status === 403
          ? "Cette leçon ne vous est pas ouverte."
          : "Le dépôt du jour n'a pas pu être lu (" + reponse.status + ").");
      }
      return reponse.json();
    }).then(function (corps) { return corps.message; });
  }

  function deposerFichiers() {
    python.FS.mkdirTree(DOSSIER);
    fichiers.forEach(function (fichier) {
      var chemin = DOSSIER + "/" + fichier.nom;
      var separateur = chemin.lastIndexOf("/");
      python.FS.mkdirTree(chemin.slice(0, separateur));
      python.FS.writeFile(chemin, fichier.contenu, { encoding: "utf8" });
    });
  }

  function synchroniser() {
    enregistrerOuvert();
    deposerFichiers();
  }

  function dossierDe(nom) {
    var coupe = nom.lastIndexOf("/");
    return coupe === -1 ? DOSSIER : DOSSIER + "/" + nom.slice(0, coupe);
  }

  function preparer(nom) {
    /* Le fichier ouvert s'exécute depuis son propre dossier : les chemins relatifs du cours (data/,
     * contracts/) et les modules livrés à côté se résolvent comme sur la machine de l'apprenant. */
    var dossier = JSON.stringify(dossierDe(nom));
    return python.runPythonAsync(
      "import os, sys\n"
      + "_dossier = " + dossier + "\n"
      + "os.chdir(_dossier)\n"
      + "if _dossier not in sys.path:\n"
      + "    sys.path.insert(0, _dossier)\n"
    );
  }

  function occuper(occupe) {
    elements.executer.disabled = occupe;
    elements.tester.disabled = occupe;
  }

  function chargerPaquetsDuDepot() {
    /* Une cellule qui importe un module du dépôt tire avec lui les paquets dont ce module dépend, et
     * Pyodide ne les voit pas dans le code de la cellule : il les cherche dans ce qu'il lit. On lui
     * donne donc les fichiers du dépôt, une fois pour la page. Un fichier que l'apprenant n'a pas
     * encore écrit ne se lit pas : son échec de lecture ne doit pas arrêter les autres. */
    if (paquetsDuDepot) { return paquetsDuDepot; }
    paquetsDuDepot = fichiers.filter(function (fichier) {
      return fichier.nom.endsWith(".py");
    }).reduce(function (suite, fichier) {
      return suite.then(function () {
        return python.loadPackagesFromImports(fichier.contenu).catch(function () { return null; });
      });
    }, Promise.resolve());
    return paquetsDuDepot;
  }

  function verserDans(cellule) {
    return function (message) {
      cellule.sortie.textContent += texte(message) + "\n";
    };
  }

  function afficherValeur(cellule, valeur, numero) {
    /* Comme dans Jupyter : la valeur de la dernière expression de la cellule s'affiche, précédée
     * de son numéro de sortie. */
    if (valeur === undefined || valeur === null) { return; }
    var lisible = (typeof valeur === "object" && typeof valeur.toString === "function")
      ? valeur.toString() : valeur;
    cellule.sortie.textContent += "Out[" + numero + "]: " + texte(lisible) + "\n";
    if (typeof valeur === "object" && typeof valeur.destroy === "function") { valeur.destroy(); }
  }

  function executerCellule(cellule) {
    if (!python || !ouvert) { return Promise.resolve(false); }
    occuper(true);
    /* numéro d'exécution, comme dans Jupyter : il compte les exécutions, pas les cellules, et une
     * cellule relancée reprend donc le numéro suivant */
    execution += 1;
    var numero = execution;
    cellule.numero.textContent = "In [*]:";
    cellule.sortie.hidden = false;
    cellule.sortie.textContent = "";
    cellule.sortie.classList.remove("erreur");
    synchroniser();
    var verser = verserDans(cellule);
    python.setStdout({ batched: verser });
    python.setStderr({ batched: verser });
    var code = cellule.zone.value;
    return preparer(ouvert.nom).then(chargerPaquetsDuDepot).then(function () {
      /* les paquets importés par la cellule sont chargés à la demande : un paquet absent se dira à
       * l'exécution, avec son nom, ce qui est plus clair qu'un échec de chargement anonyme */
      return python.loadPackagesFromImports(code).catch(function () { return null; });
    }).then(function () {
      return python.runPythonAsync(code);
    }).then(function (valeur) {
      afficherValeur(cellule, valeur, numero);
      return true;
    }, function (erreur) {
      verser(texte(erreur.message || erreur));
      cellule.sortie.classList.add("erreur");
      return false;
    }).then(function (reussi) {
      python.setStdout({ batched: ecrire });
      python.setStderr({ batched: ecrire });
      cellule.numero.textContent = "In [" + numero + "]:";
      occuper(false);
      return reussi;
    });
  }

  function executerCarnet() {
    var aExecuter = cellules.filter(function (cellule) { return cellule.type === "code"; });
    if (!aExecuter.length) {
      etat("Ce carnet n'a aucune cellule de code.", true);
      return;
    }
    etat("Exécution du carnet, cellule par cellule…");
    var suite = Promise.resolve(true);
    aExecuter.forEach(function (cellule) {
      suite = suite.then(function (continuer) {
        return continuer ? executerCellule(cellule) : false;
      });
    });
    suite.then(function (jusquAuBout) {
      etat(jusquAuBout
        ? "Carnet exécuté de bout en bout. Modifiez une cellule et relancez-la seule si vous voulez."
        : "Une cellule s'est arrêtée sur une erreur : lisez sa sortie, corrigez, relancez-la.",
        !jusquAuBout);
    });
  }

  function executer() {
    if (!python || !ouvert) { return; }
    if (estCarnet(ouvert)) { executerCarnet(); return; }
    if (!ouvert.nom.endsWith(".py")) {
      vider();
      ecrire("Ce fichier n'est pas un programme Python : ouvrez un fichier .py pour l'exécuter.");
      return;
    }
    vider();
    occuper(true);
    synchroniser();
    var nom = ouvert.nom;
    preparer(nom).then(function () {
      return python.runPythonAsync(
        "import runpy\n"
        + "runpy.run_path(" + JSON.stringify(DOSSIER + "/" + nom) + ", run_name='__main__')\n"
      );
    }).then(function () {
      ecrire("\n— fin de " + nom + " —");
    }).catch(function (erreur) {
      ecrire(texte(erreur.message || erreur));
    }).then(function () {
      occuper(false);
    });
  }

  function tester() {
    if (!python) { return; }
    vider();
    occuper(true);
    etat("Exécution des tests du jour…");
    synchroniser();
    python.loadPackage("pytest").then(function () {
      /* les tests du jour vivent à côté du fichier ouvert : on les lance depuis son dossier */
      return preparer(ouvert ? ouvert.nom : "");
    }).then(function () {
      return python.runPythonAsync(
        "import sys, pytest\n" +
        "for module in [m for m in list(sys.modules) if m.startswith('test_')]:\n" +
        "    del sys.modules[module]\n" +
        "pytest.main(['-q', '--no-header', '-p', 'no:cacheprovider', 'tests'])\n"
      );
    }).then(function () {
      etat("Tests terminés. Lisez la sortie à droite.");
    }).catch(function (erreur) {
      ecrire(texte(erreur.message || erreur));
      etat("Les tests n'ont pas pu être lancés.", true);
    }).then(function () {
      occuper(false);
    });
  }

  function demarrerPython() {
    etat("Préparation de Python dans votre navigateur… (une poignée de secondes la première fois)");
    return window.loadPyodide({ indexURL: PYODIDE }).then(function (instance) {
      python = instance;
      python.setStdout({ batched: ecrire });
      python.setStderr({ batched: ecrire });
      deposerFichiers();
      occuper(false);
      etat("Python est prêt. Votre travail reste dans ce navigateur ; rien n'est envoyé au serveur.");
    });
  }

  function chargerPyodide() {
    return new Promise(function (resoudre, rejeter) {
      var balise = document.createElement("script");
      balise.src = PYODIDE + "pyodide.js";
      balise.onload = resoudre;
      balise.onerror = function () {
        rejeter(new Error("Le moteur Python n'a pas pu être chargé. "
          + "Vérifiez votre connexion, ou travaillez avec le dépôt téléchargé."));
      };
      document.head.appendChild(balise);
    });
  }

  function tabulation(evenement) {
    if (evenement.key !== "Tab") { return; }
    evenement.preventDefault();
    var zone = evenement.target;
    var debut = zone.selectionStart;
    zone.value = zone.value.slice(0, debut) + "    " + zone.value.slice(zone.selectionEnd);
    zone.selectionStart = zone.selectionEnd = debut + 4;
  }

  function demarrer() {
    elements.titre = document.getElementById("titre");
    elements.archive = document.getElementById("archive");
    elements.etat = document.getElementById("etat");
    elements.liste = document.getElementById("liste");
    elements.code = document.getElementById("code");
    elements.carnet = document.getElementById("carnet");
    elements.sortie = document.getElementById("sortie");
    elements.executer = document.getElementById("executer");
    elements.tester = document.getElementById("tester");
    elements.retour = document.getElementById("retour");

    elements.executer.addEventListener("click", executer);
    elements.tester.addEventListener("click", tester);
    elements.code.addEventListener("keydown", tabulation);
    elements.code.addEventListener("input", function () {
      if (ouvert) { garder(ouvert.nom, elements.code.value); }
    });

    if (!lecon) {
      etat("Aucune leçon demandée : ouvrez l'atelier depuis le lien de votre leçon.", true);
      return;
    }

    appeler("openlab_academy.entrypoints.atelier_api.ouvrir", { lecon: lecon })
      .then(function (donnees) {
        elements.titre.textContent = donnees.titre;
        elements.archive.textContent = donnees.archive;
        document.title = donnees.titre + " — Atelier de code";
        fichiers = donnees.fichiers.map(function (fichier) {
          return { nom: fichier.nom, contenu: brouillon(fichier.nom, fichier.contenu) };
        });
        lister();
        charger(premierProgramme());
        return chargerPyodide().then(demarrerPython);
      })
      .catch(function (erreur) {
        etat(texte(erreur.message || erreur), true);
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", demarrer);
  } else {
    demarrer();
  }
}());
