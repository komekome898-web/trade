import sys; sys.path.insert(0,'tests/bt/item_0')
import warnings; warnings.simplefilter("ignore")
import test_bt0_r15_library_code as T
from bot.bt.core import values as V
print(V.__file__)
for kind in T.KINDS:
    for n in (1, 10, 50, 98):
        v = T._nest(kind, n)
        top = T._entry_outcome('place_order', v, None)
        least = None
        for h in range(5, 60):
            if T._entry_outcome('place_order', v, h) == top:
                least = h; break
        print(kind, n, top, 'least headroom', least)
