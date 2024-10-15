from pystac_client.free_text import (
    sqlite_text_search,
)


def test_sqlite_single_term() -> None:
    query = "sentinel"
    assert sqlite_text_search(query, {"description": "The sentinel node was true"})
    assert not sqlite_text_search(query, {"description": "No match here"})


def test_sqlite_special_characters() -> None:
    query = "sentinel-2"
    assert sqlite_text_search(query, {"description": "The sentinel-2 node was true"})
    assert not sqlite_text_search(query, {"description": "No, just sentinel-1 here"})

    query = "sentinel+2"
    assert sqlite_text_search(query, {"description": "The sentinel+2 node was true"})
    assert not sqlite_text_search(query, {"description": "No, just sentinel+1 here"})

    query = "sentinel@2"
    assert sqlite_text_search(query, {"description": "The sentinel@2 node was true"})
    assert not sqlite_text_search(query, {"description": "No, just sentinel@1 here"})


def test_sqlite_exact_phrase() -> None:
    query = '"climate model"'
    assert sqlite_text_search(query, {"description": "The climate model is impressive"})
    assert not sqlite_text_search(
        query, {"description": "This model is for climate modeling"}
    )

    # an exact phrase with a comma inside
    query = '"models, etc"'
    assert sqlite_text_search(
        query, {"description": "Produced with equations, and models, etc."}
    )
    assert not sqlite_text_search(query, {"description": "Produced with models"})


def test_sqlite_and_terms_default() -> None:
    query = "climate model"
    assert sqlite_text_search(
        query,
        {
            "description": "Climate change is a significant challenge",
            "keywords": "model, prediction",
        },
    )
    assert sqlite_text_search(
        query, {"description": "The model was developed using climate observation data"}
    )
    assert not sqlite_text_search(query, {"description": "This is an advanced model"})
    assert not sqlite_text_search(query, {"description": "No relevant terms here"})


def test_sqlite_or_terms_explicit() -> None:
    query = "climate OR model"
    assert sqlite_text_search(query, {"description": "Climate discussion"})
    assert sqlite_text_search(query, {"description": "FPGA model creation"})
    assert not sqlite_text_search(query, {"description": "No matching term here"})


def test_sqlite_or_terms_commas() -> None:
    query = "climate,model"
    assert sqlite_text_search(query, {"description": "Climate change is here"})
    assert sqlite_text_search(query, {"description": "They built a model train"})
    assert sqlite_text_search(query, {"description": "It's a climate model!"})
    assert not sqlite_text_search(
        query, {"description": "It's a mathematical equation"}
    )


def test_sqlite_and_terms() -> None:
    query = "climate AND model"
    assert sqlite_text_search(query, {"description": "The climate model is impressive"})
    assert not sqlite_text_search(
        query, {"description": "This climate change discussion"}
    )
    assert not sqlite_text_search(query, {"description": "Advanced model system"})


def test_sqlite_parentheses_grouping() -> None:
    query = "(quick OR brown) AND fox"
    assert sqlite_text_search(query, {"description": "The quick brown fox"})
    assert sqlite_text_search(query, {"description": "A quick fox jumps"})
    assert sqlite_text_search(query, {"description": "brown bear and a fox"})
    assert not sqlite_text_search(query, {"description": "The fox is clever"})

    query = "(quick AND brown) OR (fast AND red)"
    assert sqlite_text_search(query, {"description": "quick brown fox"})
    assert sqlite_text_search(query, {"description": "fast red car"})
    assert not sqlite_text_search(query, {"description": "quick red car"})


def test_sqlite_inclusions_exclusions() -> None:
    query = "quick +brown -fox"
    assert sqlite_text_search(query, {"description": "The quick brown bear"})
    assert not sqlite_text_search(query, {"description": "The quick fox"})
    assert not sqlite_text_search(query, {"description": "The quickest"})
    assert sqlite_text_search(query, {"description": "A quick light brown jumper"})


def test_sqlite_partial_match() -> None:
    query = "climat"
    assert not sqlite_text_search(query, {"description": "climatology"})
    assert not sqlite_text_search(query, {"description": "climate"})
    assert not sqlite_text_search(query, {"description": "climbing"})
