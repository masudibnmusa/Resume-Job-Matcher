from app.matching.keyword_matcher import contains_term


def test_special_characters():
    assert contains_term("Experience with C++ and Rust", "C++")
    assert not contains_term("Experience with C++ and Rust", "C")


def test_whole_word_only():
    assert not contains_term("I write JavaScript", "Java")
    assert contains_term("I write Java daily", "java")


def test_aliases_and_plurals():
    assert contains_term("Ran workloads on k8s", "Kubernetes")
    assert contains_term("Built REST APIs", "API")