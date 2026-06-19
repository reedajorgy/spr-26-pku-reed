"""Enrich Sem 1 source rows into Anki-ready vocab fields."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from apps.flashcards.cedict_lookup import CedictLookup
from apps.flashcards.pinyin_tone import numbered_pinyin_to_tone_marks
from apps.flashcards.sem1_source import Sem1SourceRow, clean_gloss_text

_CHINESE_SENTENCE = re.compile(r"[\u4e00-\u9fff][^。！？\n]*[。！？]")
_ENGLISH_SENTENCE = re.compile(r"[A-Z][^.!?]*[.!?]")
_NUMBERED_SENSE = re.compile(r"(?:^|\s)(\d+)\s+([^0-9]+?)(?=\s\d+\s|$)")
_POS_TAG = re.compile(
    r"\b(?:noun|verb|adjective|adverb|idiom|coll\.|F\.E\.|NOUN|VERB|V\.|N\.|"
    r"ADJ\.|ADV\.|CONJ\.|AUX\.|ATTR\.|B\.F\.|V\.P\.|V\.O\.|S\.V\.|M\.P\.|R\.F\.|"
    r"N\.PHRASE|PLUR|ID\.)\b",
    re.IGNORECASE,
)
_WHITESPACE = re.compile(r"\s+")
_COLLOCATION_CN = re.compile(r"([\u4e00-\u9fff][\u4e00-\u9fff·…]{0,12})")
_BRACKET_REF = re.compile(r"\[([^\]]+)\]")

_ENGLISH_KEYWORD_CN: dict[str, str] = {
    "to save": "救助；挽救",
    "to rescue": "营救",
    "to return": "归还；退回",
    "to share": "分享；共享",
    "to purify": "净化",
    "to gamble": "赌博",
    "to kiss": "亲吻",
    "to purify": "净化",
    "homeless": "无家可归",
    "friendly": "友好",
    "handsome": "英俊",
    "ironic": "讽刺的",
    "glue": "胶水",
    "willow": "柳树",
    "hamster": "仓鼠",
    "mop": "拖把",
    "shady": "阴凉的",
    "scalp": "头皮",
    "ashtray": "烟灰缸",
    "band-aid": "创可贴",
    "insecticide": "杀虫剂",
    "screwdriver": "螺丝刀",
    "headband": "发带",
    "skateboard": "滑板",
    "sunbathing": "日光浴",
    "martyr": "殉道者",
    "shepherd": "牧羊人",
    "hell": "地狱",
    "heaven": "天堂",
    "friendship": "友谊",
    "oxygen": "氧气",
    "bathtub": "浴缸",
    "antibiotic": "抗生素",
    "ointment": "药膏",
    "chewing gum": "口香糖",
    "suitcase": "手提箱",
    "police station": "警察局",
    "immune system": "免疫系统",
    "to look down on": "轻视；看不起",
    "to tease": "挑逗；戏弄",
    "to provoke": "挑衅；挑逗",
    "to be fascinated": "着迷",
    "to be captivated": "被吸引",
    "to purify": "使净化",
    "to prune": "修剪",
    "to moisturize": "保湿",
    "to purify": "净化",
    "to abandon": "抛弃",
    "to endure": "忍受",
    "to reunite": "团聚",
    "to retire": "退休",
    "to persuade": "说服",
    "to pay": "支付",
    "to fold": "折叠",
    "to resist": "抵御",
    "to eulogize": "颂扬",
    "to praise": "赞扬",
    "to hesitate": "犹豫",
    "to deceive": "欺骗",
    "to shiver": "发抖",
    "to tremble": "颤抖",
    "to dodge": "躲开",
    "to escape": "逃避",
    "to imagine": "设想；想象",
    "to assume": "假设",
    "to purify": "净化",
    "inconceivable": "难以想象",
    "unimaginable": "难以想象",
    "inevitable": "不可避免",
    "unavoidable": "不可避免",
    "extravagant": "大手大脚；奢侈",
    "malnutrition": "营养不良",
    "short-lived": "昙花一现",
    "absent-minded": "心不在焉",
    "preoccupied": "心不在焉",
    "naughty": "淘气",
    "mischievous": "淘气",
    "handsome": "英俊",
    "treasure": "宝贝；珍宝",
    "darling": "宝贝；亲昵称呼",
    "wisdom": "智慧",
    "intelligence": "智力",
    "answer": "答案",
    "solution": "解答",
    "account": "账户",
    "deposit": "存款",
    "carpet": "地毯",
    "rug": "小地毯",
    "lotion": "乳液",
    "sunscreen": "防晒霜",
    "lip balm": "润唇膏",
    "repair shop": "修理厂",
    "monitor": "显示器",
    "specialty": "拿手菜；专长",
    "stalker": "跟踪狂",
    "playing card": "纸牌",
    "smog": "雾霾",
    "haze": "薄雾",
    "precious": "名贵",
    "on-site": "实地",
    "undergraduate": "本科",
    "mushroom": "蘑菇",
    "flavor": "口味；风味",
    "taste": "口味；滋味",
    "unfavorable": "不利",
    "harmful": "有害",
    "to be out of the question": "谈不上；不可能",
    "to split the bill": "AA制；各付各的",
    "to go dutch": "AA制",
    "to snap one's fingers": "打响指",
    "to sit in on": "旁听",
    "to audit": "旁听",
    "to be responsible for": "负责",
    "to be in charge of": "负责",
    "conscientious": "认真负责",
    "responsible": "负责任的",
    "would rather": "宁可；宁愿",
    "preferably": "宁可",
    "to treat sb with the formal courtesy accorded to a host or a guest": "见外；客气见外",
    "to return (sth borrowed etc)": "退还",
    "to refund": "退款",
    "to soar": "翱翔",
    "brilliant": "灿烂",
    "splendid": "灿烂；辉煌",
    "to purify": "净化",
    "pampered": "娇贵",
    "fragile": "娇贵；脆弱",
    "tortoise": "乌龟",
    "cuckold": "乌龟（骂人）",
    "to pester": "蘑菇；纠缠",
    "to dawdle": "磨蹭",
    "to despise": "轻视",
    "to look down on": "轻视",
    "blood test": "验血；血检",
    "to draw blood": "抽血",
    "to eliminate insects": "除虫",
    "fruit basket": "果篮",
    "to hold hands": "挽手",
    "remote wilderness": "僻野",
    "to show mercy": "留情",
    "variety": "品种",
    "morning sunlight": "朝晖",
    "garlic skin": "蒜皮",
    "endless": "无休止",
    "withered": "枯焦",
    "taboo": "忌讳",
    "jujube red": "枣红色",
    "haystack": "草垛",
    "to pick up a conversation": "搭碴儿",
    "to join in a conversation": "搭碴儿",
}

_GRAMMAR_MANDARIN: dict[str, str] = {
    "之所以": "连词，用于“N之所以P，是因为……”结构，说明原因。",
    "以及": "连词，表示并列，相当于“和”“还有”。",
    "并不": "副词，强调否定，表示“并不是”。",
    "宁可": "副词，表示宁愿选择后者，常与“也不/也要”呼应。",
    "令人": "用在动词前，表示“使别人……”，后接心理或行为结果。",
    "见外": "动词，把对方当外人般客气，多用于劝人别客气。",
    "谈不上": "动词短语，表示不够格或谈不上某种程度。",
    "莫非": "副词，表示推测，相当于“难道”。",
    "岂": "书面副词，反问，相当于“难道”。",
    "呗": "语气词，表示理所当然或勉强同意。",
    "注": "动词，用文字解释或注释。",
    "唤": "动词，呼叫；召唤。",
}

_MANUAL_GLOSS_FALLBACKS: dict[str, tuple[str, str]] = {
    "两面性": ("dual nature; two-sidedness", "事物具有的两个相对方面或特点。"),
    "僻野": ("remote wilderness; secluded countryside", "偏僻的郊野。"),
    "关山迢递": (
        "remote frontier passes far away (idiom)",
        "成语，形容关山阻隔、路途遥远。",
    ),
    "奇迹": ("miracle; marvelous event", "极不寻常、令人惊叹的事情。"),
    "巧劲": ("knack; clever trick; deft touch", "巧妙的发力方法或窍门。"),
    "找台阶下": (
        "find a way out of an awkward situation",
        "给自己或别人找台阶，化解尴尬。",
    ),
    "挽手": ("to walk hand in arm; hold hands", "手臂相挽或牵手同行。"),
    "换药": ("to change a dressing; apply fresh medicine", "更换伤口敷料或药物。"),
    "搭碴儿": (
        "to strike up a conversation; join in a chat",
        "主动找话头与人攀谈。",
    ),
    "无休止": ("endless; ceaseless; without stop", "没有止境，持续不断。"),
    "春秋笔法": (
        "Spring and Autumn Annals style of subtle moral judgment in writing",
        "指寓褒贬于叙述的笔法。",
    ),
    "朝晖": ("morning sunlight; morning glow", "清晨的阳光。"),
    "果篮": ("fruit basket", "盛放水果的篮子。"),
    "枣红": ("jujube red; reddish brown", "像红枣一样的红褐色。"),
    "枯焦": ("withered and scorched; dried up", "干枯焦黄。"),
    "水土流失": ("soil erosion", "水土被冲刷流失的现象。"),
    "牛角尖": (
        "tip of a bull's horn; pedantic trivial issue",
        "比喻无关紧要的小事或钻牛角尖。",
    ),
    "牵线搭桥": (
        "to act as a go-between; make connections",
        "从中撮合、建立联系。",
    ),
    "猛劲": ("vigorous effort; sudden burst of strength", "猛然用力的劲头。"),
    "男一号": ("male lead actor", "戏剧或影视中的男主角。"),
    "草垛": ("haystack", "堆放干草的垛子。"),
    "蒜皮": ("garlic skin; garlic peel", "大蒜的外皮。"),
    "血检": ("blood test; blood examination", "化验血液。"),
    "除虫": ("to eliminate insects; pest control", "清除害虫。"),
    "可资": ("can serve as; may be used for (written)", "可以用于；可供（书面）。"),
    "扇子舞": (
        "fan dance; traditional folk dance performed with folding fans",
        "手持折扇表演的民间舞蹈。",
    ),
    "时序易迁": ("the seasons change; time passes (idiom)", "时光流逝，季节更替。"),
    "福禄": ("happiness and emolument; good fortune", "幸福与俸禄，泛指福分。"),
    "道道地地": ("genuine; authentic; real", "实实在在的；真正的。"),
    "顶门立户": (
        "to establish an independent household; stand on one's own",
        "独立成家，支撑门户。",
    ),
}

_POS_FROM_TAG: dict[str, str] = {
    "noun": "名",
    "verb": "动",
    "adjective": "形",
    "adverb": "副",
    "idiom": "成语",
    "coll.": "口语",
    "f.e.": "成语",
    "id.": "成语",
    "conj.": "连词",
    "aux.": "助词",
    "attr.": "形",
    "v.": "动",
    "n.": "名",
    "adj.": "形",
    "adv.": "副",
    "v.p.": "动",
    "v.o.": "动",
    "s.v.": "形",
    "m.p.": "助词",
    "r.v.": "动",
    "r.f.": "形",
    "n.phrase": "名",
    "plur": "名",
    "b.f.": "语素",
}


@dataclass
class EnrichedSem1Row:
    hanzi: str
    pinyin: str
    mandarin_meaning: str
    english_meaning: str
    pos: str
    collocations: str
    color: str
    example_sentence: str
    example_sentence_en: str
    usage_note: str
    common_errors: str
    related_words: str
    chapter: str
    source_category: str
    source_categories: set[str] = field(default_factory=set)


def _infer_pos(row: Sem1SourceRow, english: str) -> str:
    if row.source_category in {"chengyu", "literature-chengyu"} or "idiom" in row.tags:
        return "成语"
    for tag in row.tags:
        normalized = tag.lower().rstrip(".")
        if normalized in _POS_FROM_TAG:
            return _POS_FROM_TAG[normalized]
    gloss_lower = english.lower()
    if gloss_lower.startswith("to ") or " verb " in f" {gloss_lower} ":
        return "动"
    if " adjective" in f" {gloss_lower} " or gloss_lower.endswith("ous"):
        return "形"
    if " adverb" in f" {gloss_lower} ":
        return "副"
    if row.source_category in {"proper-nouns", "literature-proper-nouns"}:
        return "专名"
    return "名"


def _clean_sense_text(sense: str) -> str:
    cleaned = clean_gloss_text(sense)
    if _CHINESE_SENTENCE.search(cleaned) and re.search(r"[A-Za-z]", cleaned):
        cleaned = _CHINESE_SENTENCE.sub(" ", cleaned)
        cleaned = _ENGLISH_SENTENCE.sub(" ", cleaned)
    cleaned = _POS_TAG.sub(" ", cleaned)
    cleaned = re.sub(r"\b(?:idiom|lit\.|fig\.|coll\.|wr\.)\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<文>", " ", cleaned)
    cleaned = re.sub(r"\(\s*\)", "", cleaned)
    cleaned = _WHITESPACE.sub(" ", cleaned).strip(" ;,.")
    return cleaned


def _split_english_senses(gloss: str) -> list[str]:
    cleaned = clean_gloss_text(gloss)
    if not cleaned:
        return []

    numbered = _NUMBERED_SENSE.findall(f" {cleaned} ")
    if numbered:
        senses = [_clean_sense_text(sense) for _, sense in numbered if sense.strip()]
        return [sense for sense in senses if sense]

    parts = re.split(r"[;；]", cleaned)
    senses = []
    for part in parts:
        if not part.strip() or _CHINESE_SENTENCE.search(part):
            continue
        cleaned_part = _clean_sense_text(part)
        if cleaned_part:
            senses.append(cleaned_part)
    if senses:
        return senses
    fallback = _clean_sense_text(cleaned)
    return [fallback] if fallback else []


def _is_valid_example_en(text: str) -> bool:
    if len(text) < 12 or " " not in text:
        return False
    if any(marker in text for marker in ("", "", "[", "Example:")):
        return False
    return True


def _extract_examples(gloss: str) -> tuple[list[str], list[str]]:
    chinese_examples = [match.group(0).strip() for match in _CHINESE_SENTENCE.finditer(gloss)]
    english_examples = [
        match.group(0).strip()
        for match in _ENGLISH_SENTENCE.finditer(gloss)
        if _is_valid_example_en(match.group(0).strip())
    ]
    return chinese_examples, english_examples


def _extract_collocations(gloss: str, hanzi: str) -> list[str]:
    found: list[str] = []
    for match in _COLLOCATION_CN.finditer(gloss):
        phrase = match.group(1)
        if hanzi in phrase and len(phrase) <= 8 and phrase not in found:
            found.append(phrase)
    return found[:4]


def _extract_related_words(gloss: str) -> str:
    refs = _BRACKET_REF.findall(gloss)
    cleaned = [ref for ref in refs if re.search(r"[\u4e00-\u9fff]", ref)]
    return "；".join(cleaned[:3])


def _infer_color(english: str, pos: str, category: str) -> str:
    lower = english.lower()
    negative = (
        "unfavorable",
        "harmful",
        "detrimental",
        "cuckold",
        "stingy",
        "coward",
        "sly",
        "crafty",
        "deceive",
        "cheat",
        "swindle",
        "stalker",
        "annihilate",
        "malevolent",
        "sinister",
        "pester",
        "sponge off",
        "wasteful",
        "extravagant",
        "scandalous",
    )
    positive = (
        "wisdom",
        "friendship",
        "revere",
        "honor",
        "glorious",
        "splendid",
        "brilliant",
        "cherish",
        "treasure",
        "darling",
        "nimble",
        "conscientious",
        "responsible",
        "benefit",
    )
    if any(word in lower for word in negative):
        return "贬义"
    if any(word in lower for word in positive):
        return "褒义"
    if category in {"chengyu", "literature-chengyu"}:
        return "中性"
    if pos in {"副", "连词", "助词"}:
        return "中性"
    if "coll." in lower or "colloquial" in lower:
        return "口语"
    if "wr." in lower or "written" in lower:
        return "书面"
    return "中性"


def _english_to_mandarin_gloss(hanzi: str, senses: list[str], pos: str, is_idiom: bool) -> str:
    if hanzi in _GRAMMAR_MANDARIN:
        return _GRAMMAR_MANDARIN[hanzi]

    mandarin_parts: list[str] = []
    for sense in senses[:4]:
        normalized = sense.strip().rstrip(".")
        lower = normalized.lower()
        matched = False
        for english_key, chinese_value in _ENGLISH_KEYWORD_CN.items():
            if english_key in lower:
                mandarin_parts.append(chinese_value)
                matched = True
                break
        if matched:
            continue
        if is_idiom or pos == "成语":
            if lower.startswith("to "):
                mandarin_parts.append(f"比喻{normalized[3:]}")
            elif lower.startswith("lit."):
                mandarin_parts.append(normalized.replace("lit.", "字面指").strip())
            else:
                mandarin_parts.append(normalized)
            continue
        if pos == "动" and lower.startswith("to "):
            mandarin_parts.append(normalized[3:])
            continue
        if pos == "形":
            mandarin_parts.append(f"形容{normalized}")
            continue
        if pos == "副":
            mandarin_parts.append(f"表示{normalized}")
            continue
        mandarin_parts.append(normalized)

    if mandarin_parts:
        return "；".join(dict.fromkeys(mandarin_parts))
    return f"{hanzi}的常用义项，详见英文释义。"


def _build_usage_note(row: Sem1SourceRow, senses: list[str], pos: str) -> str:
    if row.hanzi in _GRAMMAR_MANDARIN:
        return _GRAMMAR_MANDARIN[row.hanzi]
    if pos == "成语":
        return "固定搭配，整体理解，不宜逐字直译。"
    if pos == "动" and any(sense.lower().startswith("to ") for sense in senses):
        return "动词用法，注意宾语和常见搭配。"
    if pos == "专名":
        return "专有名词，多用于识别语境，不必过度扩展。"
    if len(senses) > 1:
        return "一词多义，结合上下文判断具体义项。"
    return ""


def _join_english_senses(senses: list[str]) -> str:
    unique: list[str] = []
    for sense in senses:
        cleaned = _clean_sense_text(sense)
        if cleaned and cleaned not in unique:
            unique.append(cleaned)
    return "；".join(unique)


def _is_weak_cedict_gloss(gloss: str) -> bool:
    normalized = gloss.strip().lower()
    return not normalized or normalized.startswith("variant of")


def _manual_fallback(hanzi: str) -> tuple[str, str] | None:
    return _MANUAL_GLOSS_FALLBACKS.get(hanzi)


def _merge_cedict_senses(senses: list[str], cedict: CedictLookup | None, hanzi: str) -> list[str]:
    if cedict is None:
        return senses
    entry = cedict.lookup(hanzi)
    if not entry:
        return senses
    cedict_senses = [definition.strip() for definition in entry[1] if definition.strip()]
    cedict_senses = [sense for sense in cedict_senses if not _is_weak_cedict_gloss(sense)]
    if not senses:
        return cedict_senses
    if len(senses) >= len(cedict_senses):
        return senses
    merged = list(senses)
    for cedict_sense in cedict_senses:
        if cedict_sense not in merged:
            merged.append(cedict_sense)
    return merged


def enrich_source_row(row: Sem1SourceRow, cedict: CedictLookup | None = None) -> EnrichedSem1Row:
    manual = _manual_fallback(row.hanzi)
    gloss = row.raw_gloss
    if not gloss.strip() and cedict is not None:
        cedict_gloss = cedict.english_gloss(row.hanzi)
        if not _is_weak_cedict_gloss(cedict_gloss):
            gloss = cedict_gloss
    if not gloss.strip() and manual is not None:
        gloss = manual[0]

    senses = _split_english_senses(gloss)
    if not senses and cedict is not None:
        fallback = cedict.english_gloss(row.hanzi)
        if not _is_weak_cedict_gloss(fallback):
            senses = _split_english_senses(fallback)
    if not senses and manual is not None:
        senses = _split_english_senses(manual[0])

    senses = _merge_cedict_senses(senses, cedict, row.hanzi)

    english_meaning = _join_english_senses(senses)
    is_idiom = row.source_category in {"chengyu", "literature-chengyu"} or "idiom" in row.tags
    pos = _infer_pos(row, english_meaning)
    if manual is not None:
        mandarin_meaning = manual[1]
    else:
        mandarin_meaning = _english_to_mandarin_gloss(row.hanzi, senses, pos, is_idiom)

    numbered = row.numbered_pinyin
    if not numbered.strip() and cedict is not None:
        numbered = cedict.numbered_pinyin(row.hanzi)
    pinyin = numbered_pinyin_to_tone_marks(numbered)

    chinese_examples, english_examples = _extract_examples(row.raw_gloss or gloss)
    collocations = _extract_collocations(row.raw_gloss or gloss, row.hanzi)
    related_words = _extract_related_words(row.raw_gloss or gloss)

    return EnrichedSem1Row(
        hanzi=row.hanzi,
        pinyin=pinyin,
        mandarin_meaning=mandarin_meaning,
        english_meaning=english_meaning,
        pos=pos,
        collocations="；".join(collocations),
        color=_infer_color(english_meaning, pos, row.source_category),
        example_sentence=chinese_examples[0] if chinese_examples else "",
        example_sentence_en=english_examples[0] if english_examples else "",
        usage_note=_build_usage_note(row, senses, pos),
        common_errors="",
        related_words=related_words,
        chapter=row.chapter,
        source_category=row.source_category,
        source_categories={row.source_category},
    )


def enrich_source_rows(
    rows: list[Sem1SourceRow],
    cedict: CedictLookup | None = None,
) -> list[EnrichedSem1Row]:
    return [enrich_source_row(row, cedict=cedict) for row in rows]
