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
			{ fieldname: "liste", fieldtype: "HTML" },
		],
	});
	dialogue.fields_dict.offrir.$input.on("click", () => {
		const apprenant = dialogue.get_value("apprenant");
		if (apprenant) basculer(dialogue, cours, apprenant, 1, dialogue.get_value("motif") || "");
	});
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

function afficher(dialogue, cours, donnees) {
	const zone = dialogue.fields_dict.liste.$wrapper.empty();
	if (donnees.gratuit_pour_tous) {
		zone.append(
			`<p class="text-muted">${__("Ce parcours est gratuit pour tout le monde (MOOC) : la gratuité par apprenant est sans objet.")}</p>`
		);
		return;
	}
	const lignes = donnees.lignes || [];
	if (!lignes.length) {
		zone.append(`<p class="text-muted">${__("Aucun inscrit pour le moment.")}</p>`);
		return;
	}
	const tableau = $(`<table class="table table-bordered" style="margin-top:1rem">
			<thead><tr>
				<th>${__("Apprenant")}</th><th>${__("Inscrit")}</th><th>${__("État")}</th>
				<th>${__("Reste dû")}</th><th></th>
			</tr></thead><tbody></tbody></table>`);
	const corps = tableau.find("tbody");
	lignes.forEach((ligne) => {
		const rangee = $(`<tr>
				<td>${frappe.utils.escape_html(ligne.nom)}<div class="text-muted small">${frappe.utils.escape_html(ligne.apprenant)}</div></td>
				<td>${ligne.inscrit ? __("Oui") : __("Pas encore")}</td>
				<td>${ligne.offert ? `<span class="indicator-pill green">${__("Offert")}</span>` : frappe.utils.escape_html(ligne.etat || "")}</td>
				<td>${ligne.reste ? frappe.format(ligne.reste, { fieldtype: "Int" }) : "—"}</td>
				<td></td>
			</tr>`);
		const actions = rangee.find("td").last();
		$(`<button class="btn btn-xs ${ligne.offert ? "btn-default" : "btn-primary"}">
				${ligne.offert ? __("Rendre payant") : __("Offrir")}</button>`)
			.on("click", () => basculer(dialogue, cours, ligne.apprenant, ligne.offert ? 0 : 1, dialogue.get_value("motif")))
			.appendTo(actions);
		// le LMS ferme l'auto-inscription des parcours payants : l'inscription part donc d'ici
		if (ligne.offert && !ligne.inscrit) {
			$(`<button class="btn btn-xs btn-primary" style="margin-left:.4rem">${__("Inscrire")}</button>`)
				.on("click", () => inscrire(dialogue, cours, ligne.apprenant))
				.appendTo(actions);
		}
		corps.append(rangee);
	});
	zone.append(tableau);
}
