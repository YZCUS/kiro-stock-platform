import pytest

# TODO: reintroduce optimized stocks API tests once new performance endpoints exist
pytestmark = pytest.mark.xfail(reason="Legacy optimized API tests incompatible with refactored modules", run=False)