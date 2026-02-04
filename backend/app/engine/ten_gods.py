from .constants import ELEMENT_CONTROLS, ELEMENT_GENERATES, STEM_ELEMENT, STEM_POLARITY

TEN_GODS = [
    "bijian",
    "jiecai",
    "shishen",
    "shangguan",
    "zhengcai",
    "piancai",
    "zhengguan",
    "qisha",
    "zhengyin",
    "pianyin",
]

TEN_GOD_LABELS = {
    "bijian": "比肩",
    "jiecai": "劫财",
    "shishen": "食神",
    "shangguan": "伤官",
    "zhengcai": "正财",
    "piancai": "偏财",
    "zhengguan": "正官",
    "qisha": "七杀",
    "zhengyin": "正印",
    "pianyin": "偏印",
}

TEN_GOD_TO_STRUCTURE = {
    "bijian": "competition",
    "jiecai": "competition",
    "shishen": "output",
    "shangguan": "output",
    "zhengcai": "resource",
    "piancai": "resource",
    "zhengguan": "constraint",
    "qisha": "constraint",
    "zhengyin": "support",
    "pianyin": "support",
}

STRUCTURE_LABELS = {
    "resource": "资源获取结构",
    "constraint": "约束 / 责任结构",
    "support": "支持 / 缓冲结构",
    "output": "输出 / 波动结构",
    "competition": "竞争 / 内耗结构",
}


def ten_god_labels() -> dict[str, str]:
    return TEN_GOD_LABELS.copy()


def ten_god_relation(day_master: str, other_stem: str) -> str:
    dm_element = STEM_ELEMENT[day_master]
    dm_polarity = STEM_POLARITY[day_master]
    other_element = STEM_ELEMENT[other_stem]
    other_polarity = STEM_POLARITY[other_stem]

    if other_element == dm_element:
        return "bijian" if other_polarity == dm_polarity else "jiecai"

    if ELEMENT_GENERATES[dm_element] == other_element:
        return "shishen" if other_polarity == dm_polarity else "shangguan"

    if ELEMENT_GENERATES[other_element] == dm_element:
        return "pianyin" if other_polarity == dm_polarity else "zhengyin"

    if ELEMENT_CONTROLS[dm_element] == other_element:
        return "piancai" if other_polarity == dm_polarity else "zhengcai"

    if ELEMENT_CONTROLS[other_element] == dm_element:
        return "qisha" if other_polarity == dm_polarity else "zhengguan"

    return "bijian"
