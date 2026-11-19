/* Lecture d'un carnet Jupyter, sans dépendance : le fichier .ipynb devient une liste de cellules, et
 * les cellules modifiées redeviennent un .ipynb valide.
 *
 * Ces fonctions sont pures, donc vérifiables sans navigateur : c'est là que vit tout le raisonnement
 * sur le format, et l'atelier n'en garde que l'affichage. Le texte des cellules de présentation est
 * rendu ici aussi, et il est échappé avant toute mise en forme : un carnet est un fichier de données,
 * et un titre qui contiendrait une balise ne doit pas devenir du code dans la page (OWASP A03).
 */
(function (racine) {
  "use strict";

  var ENTITES = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };

  function echapper(valeur) {
    return String(valeur === undefined || valeur === null ? "" : valeur)
      .replace(/[&<>"']/g, function (caractere) { return ENTITES[caractere]; });
  }

  function texteDe(source) {
    /* Jupyter écrit la source d'une cellule tantôt en liste de lignes, tantôt en une seule chaîne. */
    return Array.isArray(source) ? source.join("") : String(source === undefined || source === null ? "" : source);
  }

  function lire(contenu) {
    var brut = JSON.parse(contenu);
    if (!brut || !Array.isArray(brut.cells)) {
      throw new Error("Ce carnet est illisible : aucune cellule.");
    }
    if (Number(brut.nbformat) !== 4) {
      throw new Error("Carnet au format " + brut.nbformat + " : l'atelier lit le format 4.");
    }
    return brut.cells.map(function (cellule, rang) {
      return {
        rang: rang,
        type: (cellule || {}).cell_type === "code" ? "code" : "presentation",
        source: texteDe((cellule || {}).source)
      };
    });
  }

  function ecrire(contenu, cellules) {
    /* Rend le carnet avec les sources modifiées, et rien d'autre : les sorties enregistrées par
     * Jupyter, les métadonnées et l'ordre des cellules du fichier d'origine sont conservés. */
    var brut = JSON.parse(contenu);
    cellules.forEach(function (cellule) {
      var cible = brut.cells[cellule.rang];
      if (cible) { cible.source = cellule.source; }
    });
    return JSON.stringify(brut, null, 1);
  }

  function liens(ligne) {
    /* Seuls http(s) et les adresses du site : « javascript: » dans un carnet ne devient pas un lien. */
    return ligne.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, function (tout, texte, adresse) {
      return /^(?:https?:\/\/|\/)[^\s"']*$/.test(adresse)
        ? '<a href="' + adresse + '" rel="noopener noreferrer">' + texte + "</a>"
        : tout;
    });
  }

  function enligne(ligne) {
    return liens(ligne
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/(^|[^*])\*([^*]+)\*/g, "$1<em>$2</em>"));
  }

  function html(markdown) {
    /* Mise en forme minimale : titres, listes, blocs de code, et le reste en paragraphes. */
    var lignes = echapper(markdown).split("\n");
    var sortie = [];
    var liste = null;
    var paragraphe = [];
    var bloc = null;

    function fermerListe() {
      if (liste) { sortie.push("</" + liste + ">"); liste = null; }
    }

    function fermerParagraphe() {
      if (paragraphe.length) { sortie.push("<p>" + enligne(paragraphe.join(" ")) + "</p>"); paragraphe = []; }
    }

    lignes.forEach(function (ligne) {
      if (/^\s*```/.test(ligne)) {
        if (bloc === null) { fermerParagraphe(); fermerListe(); bloc = []; } else {
          sortie.push("<pre><code>" + bloc.join("\n") + "</code></pre>");
          bloc = null;
        }
        return;
      }
      if (bloc !== null) { bloc.push(ligne); return; }

      var titre = /^(#{1,6})\s+(.*)$/.exec(ligne);
      if (titre) {
        fermerParagraphe(); fermerListe();
        sortie.push("<h" + titre[1].length + ">" + enligne(titre[2]) + "</h" + titre[1].length + ">");
        return;
      }
      var puce = /^\s*[-*]\s+(.*)$/.exec(ligne);
      var numero = /^\s*\d+[.)]\s+(.*)$/.exec(ligne);
      if (puce || numero) {
        fermerParagraphe();
        var voulue = puce ? "ul" : "ol";
        if (liste !== voulue) { fermerListe(); sortie.push("<" + voulue + ">"); liste = voulue; }
        sortie.push("<li>" + enligne((puce || numero)[1]) + "</li>");
        return;
      }
      if (!ligne.trim()) { fermerParagraphe(); fermerListe(); return; }
      paragraphe.push(ligne.trim());
    });

    if (bloc !== null) { sortie.push("<pre><code>" + bloc.join("\n") + "</code></pre>"); }
    fermerParagraphe();
    fermerListe();
    return sortie.join("\n");
  }

  racine.Carnet = { lire: lire, ecrire: ecrire, html: html, echapper: echapper };
}(typeof globalThis !== "undefined" ? globalThis : window));
