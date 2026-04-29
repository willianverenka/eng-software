from __future__ import annotations

import os
import sys


RAIZ_PROJETO = os.path.dirname(os.path.dirname(__file__))
if RAIZ_PROJETO not in sys.path:
    sys.path.insert(0, RAIZ_PROJETO)
