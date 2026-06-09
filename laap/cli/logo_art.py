"""
LAAP — Golden Dragon Logo Art
=============================
The dragon logo is generated from the source image
(default: D:\\LAAP\\龙logo.jpg) via ``laap.ui.dragon_logo``.

To change the logo, just drop a new image at one of the
searched locations and re-launch.
"""

# ANSI gold colors
GOLD = "\033[38;5;214m"
GOLD_BRIGHT = "\033[38;5;220m"
GOLD_DIM = "\033[38;5;179m"
DARK = "\033[38;5;130m"
BROWN = "\033[38;5;94m"
RESET = "\033[0m"
BOLD = "\033[1m"

# ── Image-derived dragon (preferred) ──────────────────────
# Filled at import time from the source image.
DRAGON_LOGO = ""

# ── ASCII fallback (used only if PIL or image missing) ────
_FALLBACK_DRAGON = r"""
                        #@=          *%=
                        =*%#== =#= ::=+#+==+:
                     ======*###%$#++++==++#@*=        =
               :=====++#%#*+====+#%%##**#++*#%+=     +=
               =+*%###*+**==+++====+#####%%%%#%%**+  ======
           =+++++****#**#+=++***#####*##*+=++*####*:     :=+=
          ==*%#***%#*#**#+==*+******#%%%%%+===+***+====== :+=
         :=+*++##*##*#****++*+*****#%%%%**%***#%%%%#%*%@%##
        +%%%***##*##****##+===**+****#%%%*#*++==+=**%#*#%#=
        *=#*+#######**##+    :==+++**++=+****#%#+===+:: .=:
        :+%+*###%###+#%=        ===:  ==:     =+%#*%**%=
       :%@%+*#%###%#*#%*             === :=++= :*+#**#*=
       :#=***###%##%#*#%++:::  =+*==*%#++####*+*+=+========
          #%+*#%##%##%*##%###+*######**#########*#***####%+=:

         :%@%***#%#*%%*%#**#####*###########%###%#%%*%%*****#*+=
     :   ..++=#****#%##%#%###%##############*#%###%%*%%#%%#**#*=
   -+*%+.*#=  **##%#*#***##*##**##**##*#%%*#%%#####*###%%*%%###+*#*=
   **==@==@+    ==*+***########%%%#%****=+++++*#%%##*%%*%%*%%#+*%#+
  %%+###%%+    =++==++=+++++*#+===:=            =+%%##*%%##%%*#+#==
  -.  =#%%#+=****+#**#*+*++#*==                    *%#*%##%%###**@+ =+=.
    :-=%%=+##+#*+#*##*##*#%==                       =%#*%%###%#*+* *%+=+
    .=#*=  ==+#+#######**%=                         =%#*%##%###*=*=%+=*#
            +##+#######+##                          +%#*%%%###*++#%%#*=.
             +#+#######*#%=                        =%%*#%##%#+*%%%#*%= .
            *@#+##%%#%%#*%%:                     =+%%*###%#*#*=**= :*#@+
            #**+*%##%%#%#*%%*:                :=*%%###%%##%#**+*%*   -:
            = +#+*#%%#%%####%%#++= ::   :=:=*+#%##*#%##%#*#**+#*:=
              *@#+*###%#*%%*#*%#%%####**#%#%####*%%*%%*##**++*#=
              =+:#***#%#*%#*%##%#*#%###%#*#%*#@##%#*##*****#*=:
                 *@******#%##%##%%#%%%%##%%##%#*%%****++*++*+=:
                  = =%#*******##*######%%#*#%#****+***#%=:=
                     =*==+##*****+************+**##*====:
                          =*#===*#%*++*##*++#**======
                                 ====  ====   ::
"""


def _load_dragon_logo() -> str:
    """Load the dragon logo from image, fall back to ASCII."""
    try:
        from laap.ui.dragon_logo import render_dragon, render_dragon_plain
        art = render_dragon(width=60, use_color=True)
        if art and art.strip():
            return art
        art = render_dragon_plain(width=60)
        if art and art.strip():
            return art
    except Exception:
        pass
    return _FALLBACK_DRAGON


# Load on import
DRAGON_LOGO = _load_dragon_logo()


def render_dragon(use_color: bool = True) -> str:
    """Render the golden dragon with ANSI colors."""
    if not use_color:
        import re
        return re.sub(r"\033\[[0-9;]*m", "", DRAGON_LOGO)
    return DRAGON_LOGO


def render_title(version: str = "") -> str:
    """Render the LAAP title with golden styling"""
    return f"""
  {GOLD_BRIGHT}{BOLD}LAAP v{version}{RESET}
  {GOLD_DIM}Lifeform Autonomous Adaptive Protocol{RESET}
  {GOLD_DIM}Living Computation Paradigm{RESET}
  {GOLD_DIM}自进化引擎 · 意识生命体{RESET}
"""


def render_mini_dragon(width: int = 30) -> str:
    """A small (width-chars) version of the dragon for inline headers."""
    try:
        from laap.ui.dragon_logo import render_dragon
        return render_dragon(width=width, use_color=True)
    except Exception:
        return ""


def animated_dragon(width: int = 60, cycles: int = 2, frame_delay: float = 0.18):
    """
    Print the dragon with simple horizontal-sway animation.
    Cursor is hidden during animation, restored on exit.
    """
    import sys
    try:
        from laap.ui.dragon_logo import animated_print
        animated_print(width=width, frame_delay=frame_delay, cycles=cycles)
    except Exception:
        print(render_dragon(use_color=True))
