"""
test_interface.py — les selecteurs CSS visent-ils des elements qui existent ?

Une feuille de style qui vise un nom d'element disparu ne provoque aucune
erreur : elle ne s'applique simplement pas. C'est ainsi que le libelle MENU,
l'habillage des pastilles de navigation et la mise en pile des colonnes sur
telephone sont restes sans effet — le code etait ecrit, il ne rencontrait rien.
Streamlit renomme ses `data-testid` d'une version a l'autre : `collapsedControl`
est devenu `stSidebarCollapsedControl`, puis `stExpandSidebarButton` ; `column`
est devenu `stColumn` ; les pastilles sont emises sous `stButtonGroup`.

Ce script relit donc la feuille de style de l'application dans un vrai moteur de
rendu, sur le balisage reellement emis par Streamlit 1.55 — recopie de
`frontend/app/src/components/Header/Header.tsx`, de
`frontend/lib/src/components/widgets/ButtonGroup/ButtonGroup.tsx` et de
`frontend/lib/src/components/core/Block/Block.tsx` au tag 1.55.0 — puis mesure
ce qui s'affiche vraiment.

    pip install playwright
    playwright install chromium
    python test_interface.py

Il n'a besoin ni du serveur Streamlit ni de la base de donnees.
"""

import asyncio
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent
sys.path.insert(0, str(RACINE))

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("playwright n'est pas installe. Ce test verifie le rendu reel de la\n"
          "feuille de style ; sans navigateur, il n'a rien a mesurer.\n\n"
          "    pip install playwright\n    playwright install chromium\n")
    sys.exit(2)

from backend.ui_theme import CSS_CORRECTIF, CSS_MOBILE, CSS_NEO, css_variables

CSS_APP = "\n".join(re.findall(
    r"<style>(.*?)</style>",
    (RACINE / "app.py").read_text(encoding="utf-8"), re.S))

# ── Balisage emis par Streamlit 1.55 ──────────────────────────────────────────
DOM_BOUTON_MENU = """
<header class="stAppHeader" data-testid="stHeader">
  <div class="stAppToolbar" data-testid="stToolbar"><div><div>
    <div><button kind="headerNoPadding" data-testid="stExpandSidebarButton">
      <span data-testid="stIconMaterial">keyboard_double_arrow_right</span>
    </button></div>
  </div></div></header>"""

# Versions anterieures, conservees parce que la feuille les vise encore.
DOM_BOUTON_ANCIEN = """
<div data-testid="stSidebarCollapsedControl">
  <button kind="header"><svg viewBox="0 0 24 24"><path d="M0 0h24v24H0z"/></svg></button>
</div>"""
DOM_BOUTON_TRES_ANCIEN = """
<div data-testid="collapsedControl">
  <svg viewBox="0 0 24 24"><path d="M0 0h24v24H0z"/></svg>
</div>"""

DOM_PASTILLES = """
<div class="stButtonGroup" data-testid="stButtonGroup">
  <div data-testid="stWidgetLabel"></div>
  <div role="group">
    <button aria-pressed="true"  kind="pillsActive">Planning</button>
    <button aria-pressed="false" kind="pills">KPI</button>
    <button aria-pressed="false" kind="pills">Historique</button>
  </div>
</div>"""

DOM_COLONNES = """
<div class="stHorizontalBlock" data-testid="stHorizontalBlock">
  <div class="stColumn" data-testid="stColumn"><div>Graphique A</div></div>
  <div class="stColumn" data-testid="stColumn"><div>Graphique B</div></div>
</div>"""

# Ce que Streamlit applique lui-meme (emotion). Sans cette base, le test
# mesurerait des colonnes sans disposition flex et conclurait a tort qu'elles
# sont empilees sur ordinateur.
BASE_STREAMLIT = """
[data-testid="stHorizontalBlock"] { display: flex; flex-wrap: wrap; gap: 1rem; }
[data-testid="stColumn"] { width: calc(50% - 1rem); flex: 1 1 calc(50% - 1rem); }
@media (max-width: 640px) { [data-testid="stColumn"] { min-width: calc(100% - 2rem); } }
"""

GABARIT = ("<!doctype html><html><head><meta charset='utf-8'>"
           "<style>body{{margin:0;background:#070a10}}{css}</style>"
           "</head><body>{dom}</body></html>")


def feuilles(mobile: bool) -> str:
    css = BASE_STREAMLIT + css_variables() + CSS_APP + CSS_CORRECTIF + CSS_NEO
    if mobile:
        css += CSS_MOBILE          # injectee en dernier : elle doit l'emporter
    return re.sub(r"</?style[^>]*>", "", css)


class Bilan:
    def __init__(self) -> None:
        self.ok = 0
        self.echecs: list[str] = []

    def verifier(self, nom: str, condition: bool, mesure: str = "") -> None:
        if condition:
            self.ok += 1
        else:
            self.echecs.append(f"{nom} — mesure : {mesure}")


async def page(navigateur, dom: str, mobile: bool, largeur: int):
    p = await navigateur.new_page(viewport={"width": largeur, "height": 900})
    await p.set_content(GABARIT.format(css=feuilles(mobile), dom=dom))
    return p


async def main() -> int:
    b = Bilan()
    async with async_playwright() as pw:
        nav = await pw.chromium.launch(args=["--no-sandbox"])

        # ── 1. Le bouton d'ouverture porte-t-il le mot MENU ? ─────────────────
        print("Bouton d'ouverture de la barre laterale")
        for version, dom, sel in (
            ("Streamlit 1.55", DOM_BOUTON_MENU,
             '[data-testid="stExpandSidebarButton"]'),
            ("version anterieure", DOM_BOUTON_ANCIEN,
             '[data-testid="stSidebarCollapsedControl"] button'),
            ("version tres anterieure", DOM_BOUTON_TRES_ANCIEN,
             '[data-testid="collapsedControl"]'),
        ):
            for mobile, largeur in ((False, 1440), (True, 390)):
                p = await page(nav, dom, mobile, largeur)
                el = p.locator(sel)
                support = "telephone" if mobile else "ordinateur"
                if await el.count() == 0:
                    b.verifier(f"{version}/{support} : element present", False, "absent")
                    await p.close()
                    continue
                libelle = await el.evaluate(
                    "e => getComputedStyle(e, '::after').content")
                fond = await el.evaluate("e => getComputedStyle(e).backgroundColor")
                boite = await el.bounding_box()
                h, w = round(boite["height"]), round(boite["width"])
                print(f"  {version:24s} {support:11s} "
                      f"libelle={libelle:8s} {w}x{h} px")
                b.verifier(f"{version}/{support} : libelle MENU",
                           libelle.strip("\"'") == "MENU", libelle)
                b.verifier(f"{version}/{support} : pastille orange",
                           "255, 122, 26" in fond, fond)
                b.verifier(f"{version}/{support} : zone tactile",
                           h >= (44 if mobile else 38), f"{h} px")
                b.verifier(f"{version}/{support} : largeur du mot",
                           70 <= w <= 200, f"{w} px")
                await p.close()

        # ── 2. Pastilles de navigation du telephone ───────────────────────────
        print("\nPastilles de navigation (telephone)")
        p = await page(nav, DOM_PASTILLES, True, 390)
        actif = p.locator('button[aria-pressed="true"]')
        inactif = p.locator('button[aria-pressed="false"]').first
        sa = await actif.evaluate(
            "e => ({couleur: getComputedStyle(e).color,"
            " bordure: getComputedStyle(e).borderColor,"
            " rayon: getComputedStyle(e).borderRadius,"
            " hauteur: e.getBoundingClientRect().height})")
        si = await inactif.evaluate("e => getComputedStyle(e).color")
        groupe = await p.locator('div[role="group"]').evaluate(
            "e => ({d: getComputedStyle(e).display, w: getComputedStyle(e).flexWrap})")
        print(f"  active   : {sa['couleur']}, {round(sa['hauteur'])} px de haut")
        print(f"  inactive : {si}")
        b.verifier("pastille active en orange", "255, 122, 26" in sa["couleur"], sa["couleur"])
        b.verifier("bordure active en orange", "255, 122, 26" in sa["bordure"], sa["bordure"])
        b.verifier("pastille arrondie", sa["rayon"].startswith("999"), sa["rayon"])
        b.verifier("zone tactile >= 40 px", sa["hauteur"] >= 40, f"{sa['hauteur']} px")
        b.verifier("pastille inactive distincte", "255, 122, 26" not in si, si)
        b.verifier("groupe en flex", groupe["d"] == "flex", groupe["d"])
        b.verifier("retour a la ligne autorise", groupe["w"] == "wrap", groupe["w"])
        await p.close()

        # ── 3. Colonnes : cote a cote sur PC, empilees sur telephone ──────────
        print("\nColonnes de graphiques")
        for mobile, largeur in ((False, 1440), (True, 390)):
            p = await page(nav, DOM_COLONNES, mobile, largeur)
            a = p.locator('[data-testid="stColumn"]').nth(0)
            c = p.locator('[data-testid="stColumn"]').nth(1)
            ba, bc = await a.bounding_box(), await c.bounding_box()
            empilees = bc["y"] > ba["y"] + ba["height"] - 2
            support = "telephone" if mobile else "ordinateur"
            print(f"  {support:11s} : {round(ba['width'])} px et "
                  f"{round(bc['width'])} px — "
                  f"{'empilees' if empilees else 'cote a cote'}")
            b.verifier(f"colonnes {support}", empilees == mobile,
                       "empilees" if empilees else "cote a cote")
            if mobile:
                b.verifier("colonne pleine largeur sur telephone",
                           bc["width"] > largeur * 0.8, f"{round(bc['width'])} px")
            await p.close()

        await nav.close()

    total = b.ok + len(b.echecs)
    print(f"\n{b.ok} / {total} verifications passees")
    for e in b.echecs:
        print(f"  ECHEC : {e}")
    return 1 if b.echecs else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
