from app.cache.semantic_cache import DisabledSemanticCache


def test_disabled_cache_is_a_safe_noop():
    cache = DisabledSemanticCache()

    assert cache.lookup("prompt") is None
    cache.insert("prompt", "response")
    assert cache.lookup("prompt") is None
    cache.env.close()
