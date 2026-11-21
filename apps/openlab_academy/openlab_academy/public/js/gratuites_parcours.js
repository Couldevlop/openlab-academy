// Fiche d'un parcours : « Inscrits et gratuités ». Un tableau des inscrits, leur état de paiement, et un
// bouton par ligne pour offrir le parcours ou le rendre payant. Les droits sont tenus par le serveur ; cet
// écran ne fait que montrer et demander.
frappe.ui.form.on("LMS Course", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("Inscrits et gratuités"), () => ouvrir(frm.doc.name));
	},
});

function ouvrir(cours) {
	const dialogue = new frappe.ui.Dialog({
		title: __("Inscrits et gratuités"),
		size: "large",
		fields: [
			{
				fieldname: "apprenant",
				fieldtype: "Link",
				options: "User",
				label: __("Offrir le parcours à"),
				description: __("Cherchez une personne qui n'est pas encore inscrite : elle s'inscrira sans payer."),
			},
			{ fieldname: "motif", fieldtype: "Data", label: __("Motif"), placeholder: __("Bourse, partenariat…") },
			{ fieldname: "offrir", fieldtype: "Button", label: __("Offrir") },
			{ fieldtype: "Section Break", label: __("Compte d'essai") },
			{
				fieldname: "creer",
				fieldtype: "Button",
				label: __("Créer un compte apprenant"),
				description: __("Pour un test utilisateur : le compte naît actif, sans courriel de bienvenue."),
			},
			{ fieldname: "liste", fieldtype: "HTML" },
		],
	});
	dialogue.fields_dict.offrir.$input.on("click", () => {
		const apprenant = dialogue.get_value("apprenant");
		if (apprenant) basculer(dialogue, cours, apprenant, 1, dialogue.get_value("motif") || "");
	});
	dialogue.fields_dict.creer.$input.on("click", () => creer(dialogue, cours));
	dialogue.show();
	charger(dialogue, cours);
}

function charger(dialogue, cours) {
	frappe.call({
		method: "openlab_academy.entrypoints.gratuites.inscrits",
		args: { cours },
		callback: (r) => afficher(dialogue, cours, r.message || { lignes: [] }),
	});
}

function basculer(dialogue, cours, apprenant, offert, motif) {
	frappe.call({
		method: "openlab_academy.entrypoints.gratuites.basculer",
		args: { cours, apprenant, offert, motif: motif || "" },
		freeze: true,
		callback: (r) => {
			if (!r.message) return;
			afficher(dialogue, cours, r.message);
			frappe.show_alert({
				message: offert ? __("Parcours offert à {0}", [apprenant]) : __("Parcours redevenu payant pour {0}", [apprenant]),
				indicator: "green",
			});
		},
	});
}

function inscrire(dialogue, cours, apprenant) {
	frappe.call({
		method: "openlab_academy.entrypoints.gratuites.inscrire",
		args: { cours, apprenant },
		freeze: true,
		callback: (r) => {
			if (!r.message) return;
			afficher(dialogue, cours, r.message);
			frappe.show_alert({ message: __("{0} est inscrit, sans paiement", [apprenant]), indicator: "green" });
		},
	});
}

function creer(parent, cours) {
	// Un compte d'essai naît actif, sans courriel de bienvenue : les comptes d'envoi de production ne sont
	// pas en service, et un compte qui attendrait son courriel serait inutilisable.
	const formulaire = new frappe.ui.Dialog({
		title: __("Créer un compte apprenant"),
		fields: [
			{ fieldname: "courriel", fieldtype: "Data", options: "Email", label: __("Adresse électronique"), reqd: 1 },
			{ fieldname: "nom", fieldtype: "Data", label: __("Nom"), reqd: 1 },
			{ fieldname: "prenom", fieldtype: "Data", label: __("Prénom") },
			{
				fieldname: "mot_de_passe",
				fieldtype: "Password",
				label: __("Mot de passe"),
				description: __("Laissez vide pour qu'un mot de passe soit tiré et affiché une seule fois."),
			},
		],
		primary_action_label: __("Créer"),
		primary_action: (valeurs) => {
			frappe.call({
				method: "openlab_academy.entrypoints.gratuites.creer_apprenant",
				args: valeurs,
				freeze: true,
				callback: (r) => {
					if (!r.message) return;
					formulaire.hide();
					annoncer(r.message);
					// le compte peut maintenant recevoir le parcours : on prépare le geste suivant
					parent.set_value("apprenant", r.message.apprenant);
					charger(parent, cours);
				},
			});
		},
	});
	formulaire.show();
}

function annoncer(reponse) {
	const qui = frappe.utils.escape_html(reponse.apprenant);
	if (!reponse.cree) {
		frappe.msgprint({
			title: __("Compte déjà existant"),
			message: __("{0} a déjà un compte : il est repris tel quel, son mot de passe n'a pas été touché.", [qui]),
			indicator: "orange",
		});
		return;
	}
	if (!reponse.mot_de_passe) {
		frappe.show_alert({ message: __("Compte créé pour {0}", [qui]), indicator: "green" });
		return;
	}
	// affiché une seule fois : le serveur ne le rendra plus, et rien ne le conserve en clair
	frappe.msgprint({
		title: __("Compte créé"),
		message: `<p>${__("Notez ce mot de passe maintenant : il ne sera plus affiché.")}</p>
			<p><b>${qui}</b><br><code>${frappe.utils.escape_html(reponse.mot_de_passe)}</code></p>`,
		indicator: "green",
	});
}

function montant(valeur) {
	// même écriture que les messages de l'intendance : milliers séparés d'une espace, FCFA en suffixe
	return `${String(Math.round(valeur)).replace(/\B(?=(\d{3})+(?!\d))/g, " ")} ${__("FCFA")}`;
}

function afficher(dialogue, cours, donnees) {
	// la charte (openlab.css) tient la mise en forme ; le script ne pose que les classes
	const zone = dialogue.fields_dict.liste.$wrapper.empty().addClass("ol-gratuites");
	zone.append('<div class="ol-filet" aria-hidden="true"></div>');
	if (donnees.gratuit_pour_tous) {
		zone.append(
			`<p class="ol-vide">${__("Ce parcours est gratuit pour tout le monde (MOOC) : la gratuité par apprenant est sans objet.")}</p>`
		);
		return;
	}
	const lignes = donnees.lignes || [];
	if (!lignes.length) {
		zone.append(`<p class="ol-vide">${__("Aucun inscrit pour le moment.")}</p>`);
		return;
	}
	const tableau = $(`<table>
			<thead><tr>
				<th>${__("Apprenant")}</th><th>${__("Inscrit")}</th><th>${__("État")}</th>
				<th class="ol-montant">${__("Reste dû")}</th><th></th>
			</tr></thead><tbody></tbody></table>`);
	const corps = tableau.find("tbody");
	lignes.forEach((ligne) => {
		const teinte = ligne.offert ? "ol-etat-offert" : ligne.reste ? "ol-etat-du" : "";
		const rangee = $(`<tr>
				<td><div class="ol-nom">${frappe.utils.escape_html(ligne.nom)}</div>
					<div class="ol-courriel">${frappe.utils.escape_html(ligne.apprenant)}</div></td>
				<td>${ligne.inscrit ? __("Oui") : __("Pas encore")}</td>
				<td><span class="ol-etat ${teinte}">${ligne.offert ? __("Offert") : frappe.utils.escape_html(ligne.etat || "")}</span></td>
				<td class="ol-montant">${ligne.reste ? montant(ligne.reste) : "—"}</td>
				<td class="ol-actions"></td>
			</tr>`);
		const actions = rangee.find("td").last();
		$(`<button class="ol-action ${ligne.offert ? "" : "ol-action-forte"}">
				${ligne.offert ? __("Rendre payant") : __("Offrir")}</button>`)
			.on("click", () => basculer(dialogue, cours, ligne.apprenant, ligne.offert ? 0 : 1, dialogue.get_value("motif")))
			.appendTo(actions);
		// le LMS ferme l'auto-inscription des parcours payants : l'inscription part donc d'ici
		if (ligne.offert && !ligne.inscrit) {
			$(`<button class="ol-action ol-action-forte">${__("Inscrire")}</button>`)
				.on("click", () => inscrire(dialogue, cours, ligne.apprenant))
				.appendTo(actions);
		}
		corps.append(rangee);
	});
	zone.append(tableau);
}
