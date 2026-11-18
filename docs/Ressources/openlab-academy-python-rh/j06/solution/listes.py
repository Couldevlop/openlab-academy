"""Journée 06 : listes, tranches et tri."""


def effectif_trie(noms):
    """Rend une nouvelle liste triée, sans toucher à celle qu'on reçoit."""
    return sorted(noms)


def trois_derniers(noms):
    """Rend les trois derniers noms, ou tous s'il y en a moins de trois."""
    return list(noms[-3:])
