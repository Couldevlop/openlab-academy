/* Atelier de code : Python s'exécute dans le navigateur de l'apprenant, jamais sur le serveur.
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

  function charger(nom) {
    if (ouvert) {
      ouvert.contenu = elements.code.value;
      garder(ouvert.nom, ouvert.contenu);
    }
    ouvert = fichiers.filter(function (f) { return f.nom === nom; })[0] || null;
    elements.code.value = ouvert ? ouvert.contenu : "";
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
    if (ouvert) {
      ouvert.contenu = elements.code.value;
      garder(ouvert.nom, ouvert.contenu);
    }
    deposerFichiers();
  }

  function occuper(occupe) {
    elements.executer.disabled = occupe;
    elements.tester.disabled = occupe;
  }

  function executer() {
    if (!python || !ouvert) { return; }
    if (!ouvert.nom.endsWith(".py")) {
      vider();
      ecrire("Ce fichier n'est pas un programme Python : ouvrez un fichier .py pour l'exécuter.");
      return;
    }
    vider();
    occuper(true);
    synchroniser();
    var nom = ouvert.nom;
    python.runPythonAsync(
      "import runpy, sys, os\n" +
      "os.chdir('" + DOSSIER + "')\n" +
      "sys.path.insert(0, '" + DOSSIER + "')\n" +
      "runpy.run_path(" + JSON.stringify(DOSSIER + "/" + nom) + ", run_name='__main__')\n"
    ).then(function () {
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
      return python.runPythonAsync(
        "import os, sys, pytest\n" +
        "os.chdir('" + DOSSIER + "')\n" +
        "sys.path.insert(0, '" + DOSSIER + "')\n" +
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
    var zone = elements.code;
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
