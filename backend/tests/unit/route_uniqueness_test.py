from api.v1.stocks import router


def test_stock_routes_have_unique_method_and_path_pairs():
    seen = set()
    duplicates = []
    for route in router.routes:
        for method in route.methods or set():
            key = (method, route.path)
            if key in seen:
                duplicates.append(key)
            seen.add(key)

    assert duplicates == []
