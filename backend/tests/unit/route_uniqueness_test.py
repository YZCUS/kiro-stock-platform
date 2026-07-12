from api.v1.stocks import router


def test_stock_routes_have_unique_method_and_path_pairs():
    seen = set()
    duplicates = []
    for route in router.routes:
        methods = getattr(route, "methods", None)
        path = getattr(route, "path", None)
        if not methods or path is None:
            continue

        for method in methods:
            key = (method, path)
            if key in seen:
                duplicates.append(key)
            seen.add(key)

    assert duplicates == []
