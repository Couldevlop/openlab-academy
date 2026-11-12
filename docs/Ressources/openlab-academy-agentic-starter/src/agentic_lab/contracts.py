from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, StrictStr


class StrictContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ListInvoicesArgs(StrictContract):
    age_min_jours: StrictInt = Field(ge=0, le=3650)
    exclure_litiges: StrictBool = True


class CalculateExposureArgs(StrictContract):
    facture_ids: list[StrictStr] = Field(min_length=1, max_length=100)


class PrepareDraftArgs(StrictContract):
    facture_id: StrictStr = Field(min_length=1, max_length=40)
    palier: StrictInt = Field(ge=1, le=2)


class SubmitApprovalArgs(StrictContract):
    brouillon_id: StrictStr = Field(min_length=1, max_length=80)


class RecordReminderArgs(StrictContract):
    brouillon_id: StrictStr = Field(min_length=1, max_length=80)
    validation_id: StrictStr = Field(min_length=1, max_length=80)
    cle_idempotence: StrictStr = Field(min_length=1, max_length=128)


ToolName = Literal[
    "lister_factures_impayees",
    "calculer_exposition",
    "preparer_brouillon_relance",
    "soumettre_pour_validation",
    "enregistrer_relance_simulee",
]


class ToolCall(StrictContract):
    name: ToolName
    arguments: dict
