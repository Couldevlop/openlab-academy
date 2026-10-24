// Console (bureau Frappe) : « Simuler l'impact » sur les réglages d'évaluation et les surcharges. Le formulaire, même
// non enregistré, est envoyé au simulateur ; rien n'est enregistré. Textes échappés avant affichage.
frappe.provide("openlab_academy");

openlab_academy.liste_impact = function (titre, valeurs) {
	if (!valeurs.length) return "";
	const e = frappe.utils.escape_html;
	return `<p><b>${e(titre)}</b> : ${valeurs.map(e).join(", ")}</p>`;
};

openlab_academy.simuler_impact = function (frm, cible) {
	frappe.call({
		method: "openlab_academy.entrypoints.evaluation_api.simuler_impact",
		args: { cible, doc: frm.doc },
		freeze: true,
		freeze_message: __("Simulation en cours…"),
		callback: ({ message: r }) => {
			const n = r.copies.length;
			const resume = n
				? `Ce changement toucherait ${n} copie(s) en cours, dans ${r.exercices.length} exercice(s)` +
				  ` et ${r.cohortes.length} cohorte(s).`
				: "Ce changement ne toucherait aucune copie en cours de correction.";
			const secours = r.secours.length
				? `<p class="text-danger">${r.secours.length} copie(s) passeraient sur la chaîne de secours` +
				  " (formateur seul) : la combinaison de réglages serait invalide pour elles.</p>"
				: "";
			frappe.msgprint({
				title: __("Impact du changement"),
				indicator: r.secours.length ? "red" : n ? "orange" : "green",
				message:
					`<p>${frappe.utils.escape_html(resume)}</p>` +
					openlab_academy.liste_impact("Exercices", r.exercices) +
					openlab_academy.liste_impact("Cohortes", r.cohortes) +
					openlab_academy.liste_impact("Champs modifiés", r.champs) +
					secours,
			});
		},
	});
};

frappe.ui.form.on("Reglages Evaluation OpenLab", {
	refresh(frm) {
		frm.add_custom_button(__("Simuler l'impact"), () => openlab_academy.simuler_impact(frm, "reglages"));
	},
});

frappe.ui.form.on("Surcharge Evaluation OpenLab", {
	refresh(frm) {
		frm.add_custom_button(__("Simuler l'impact"), () => openlab_academy.simuler_impact(frm, "surcharge"));
	},
});
