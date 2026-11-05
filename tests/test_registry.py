from viperforge.engine import TEMPLATES_DIR
from viperforge.registry import (
    CATEGORY_COLORS, CATEGORY_ICONS, REGISTRY,
    all_categories, get_by_category, get_exploit_by_id, get_exploit_by_name,
)


def test_ids_and_names_are_unique():
    assert len({e.id for e in REGISTRY}) == len(REGISTRY)
    assert len({e.name for e in REGISTRY}) == len(REGISTRY)


def test_every_module_has_a_template():
    missing = [e.name for e in REGISTRY if not (TEMPLATES_DIR / f"{e.template}.j2").is_file()]
    assert missing == []


def test_no_orphan_templates():
    used = {e.template for e in REGISTRY}
    orphans = sorted(p.stem for p in TEMPLATES_DIR.glob("*.j2") if p.stem not in used)
    assert orphans == []


def test_every_category_has_color_and_icon():
    for cat in all_categories():
        assert cat in CATEGORY_COLORS
        assert cat in CATEGORY_ICONS


def test_option_names_unique_per_module():
    for e in REGISTRY:
        names = [o.name for o in e.options]
        assert len(names) == len(set(names)), e.name


def test_lookups():
    first = REGISTRY[0]
    assert get_exploit_by_id(first.id) is first
    assert get_exploit_by_name(first.name) is first
    assert get_exploit_by_id(-12345) is None
    assert get_exploit_by_name("does_not_exist") is None
    assert first in get_by_category(first.category)
