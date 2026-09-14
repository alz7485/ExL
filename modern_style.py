# -*- coding: utf-8 -*-
"""ExLauncher Modern 専用スタイル。Classicから完全分離。"""

# すべて不透明色。左下→右上へ薄く/明るくなるグラデーションを基本にする。
THEMES = {
    "Dark Gray": {"accent":"#7EB2FF","header":"#2B2F36","header2":"#3A404A","item":"#363B44","item2":"#454C57","item_hover":"#444B56","item_hover2":"#56606D","bar":"#1D2026","bar2":"#303640","text":"#F7F9FC","muted":"#C0C6CF","border":"#59616D"},
    "Carbon":    {"accent":"#A7B0BF","header":"#202328","header2":"#343941","item":"#2A2E35","item2":"#3B414B","item_hover":"#383E47","item_hover2":"#4A5260","bar":"#15171B","bar2":"#282C33","text":"#F6F7F9","muted":"#B9BEC6","border":"#535A65"},
    "Midnight":  {"accent":"#8EA8FF","header":"#1B2340","header2":"#2E3A65","item":"#252F52","item2":"#37466F","item_hover":"#324063","item_hover2":"#495A84","bar":"#11172B","bar2":"#232D4E","text":"#F8FAFF","muted":"#BCC5E0","border":"#52638C"},
    "Blue":      {"accent":"#72BCFF","header":"#17314A","header2":"#28557B","item":"#204260","item2":"#326487","item_hover":"#2A5272","item_hover2":"#3D7398","bar":"#102439","bar2":"#1D4260","text":"#F6FBFF","muted":"#BED5E7","border":"#4C7699"},
    "Azure":     {"accent":"#69D0FF","header":"#123A52","header2":"#23647F","item":"#194A66","item2":"#2A718F","item_hover":"#205B78","item_hover2":"#3383A3","bar":"#0C293A","bar2":"#174B63","text":"#F4FCFF","muted":"#B8DCE8","border":"#46849D"},
    "Cyan":      {"accent":"#65E3E8","header":"#123E43","header2":"#22686D","item":"#194E54","item2":"#2B777C","item_hover":"#216167","item_hover2":"#368B91","bar":"#0C2B2F","bar2":"#175155","text":"#F3FFFF","muted":"#B8DDDE","border":"#468A8D"},
    "Teal":      {"accent":"#6DDBC5","header":"#173D38","header2":"#28665B","item":"#1F4D47","item2":"#337568","item_hover":"#286057","item_hover2":"#3F887A","bar":"#102B28","bar2":"#1E4D46","text":"#F4FFFC","muted":"#BCDCD4","border":"#4D887D"},
    "Green":     {"accent":"#83DA9B","header":"#1D3B2B","header2":"#346348","item":"#284B38","item2":"#447457","item_hover":"#335E46","item_hover2":"#508866","bar":"#142A20","bar2":"#254A36","text":"#F6FFF8","muted":"#C3DAC9","border":"#5D846A"},
    "Emerald":   {"accent":"#72E3A8","header":"#123C2C","header2":"#22684B","item":"#1A4D39","item2":"#2D7655","item_hover":"#226047","item_hover2":"#398A64","bar":"#0C2A20","bar2":"#174E39","text":"#F3FFF8","muted":"#B8DDC9","border":"#478A68"},
    "Olive":     {"accent":"#D1D978","header":"#3A3D1E","header2":"#60652F","item":"#4A4E28","item2":"#70763A","item_hover":"#5A5F31","item_hover2":"#838A45","bar":"#292B16","bar2":"#4B4F25","text":"#FFFFF3","muted":"#DDDEC0","border":"#87895C"},
    "Purple":    {"accent":"#BE9BFF","header":"#332546","header2":"#563C72","item":"#433259","item2":"#674A82","item_hover":"#523E6B","item_hover2":"#775895","bar":"#241A33","bar2":"#432E58","text":"#FCF9FF","muted":"#D8C8E6","border":"#8069A0"},
    "Violet":    {"accent":"#AFA2FF","header":"#29274D","header2":"#48457B","item":"#373565","item2":"#57538C","item_hover":"#454279","item_hover2":"#6561A0","bar":"#1D1B36","bar2":"#37345F","text":"#FAF9FF","muted":"#D0CBE8","border":"#716EA4"},
    "Rose":      {"accent":"#FF9DBB","header":"#482635","header2":"#713A50","item":"#5A3042","item2":"#85465F","item_hover":"#6C3A4F","item_hover2":"#99536E","bar":"#321B26","bar2":"#582E40","text":"#FFF8FB","muted":"#E6C5D0","border":"#9C6478"},
    "Wine":      {"accent":"#E993AD","header":"#3D202C","header2":"#633346","item":"#4E2938","item2":"#744054","item_hover":"#603344","item_hover2":"#875065","bar":"#2B161F","bar2":"#4C2938","text":"#FFF7FA","muted":"#DEC1C9","border":"#8E5B69"},
    "Orange":    {"accent":"#FFB36B","header":"#4A3020","header2":"#754B2E","item":"#5C3C28","item2":"#885A38","item_hover":"#6E4930","item_hover2":"#9A6841","bar":"#342217","bar2":"#5A3B25","text":"#FFF9F3","muted":"#E3CEBC","border":"#9A7356"},
    "Coffee":    {"accent":"#D8B08A","header":"#362B26","header2":"#5A463C","item":"#44362F","item2":"#665044","item_hover":"#534239","item_hover2":"#775F51","bar":"#261E1A","bar2":"#463730","text":"#FFF9F5","muted":"#D8CAC1","border":"#806C60"},
    "Navy":      {"accent":"#78A9FF","header":"#101F3A","header2":"#244D7C","item":"#172B4D","item2":"#2E5F91","item_hover":"#203A61","item_hover2":"#3B72A6","bar":"#0A1528","bar2":"#19385C","text":"#F5F9FF","muted":"#B9CAE1","border":"#456D99"},
    "Sky":       {"accent":"#8DE4FF","header":"#17435B","header2":"#3689AD","item":"#205873","item2":"#43A0C3","item_hover":"#2A6B88","item_hover2":"#54B4D4","bar":"#0F3042","bar2":"#286B89","text":"#F5FDFF","muted":"#C0E1EA","border":"#5B9BB3"},
    "Lime":      {"accent":"#C9F06B","header":"#34431A","header2":"#6B852A","item":"#435522","item2":"#7D9934","item_hover":"#526729","item_hover2":"#91AD40","bar":"#242F12","bar2":"#50651F","text":"#FBFFF2","muted":"#D7E4B9","border":"#839B4D"},
    "Magenta":   {"accent":"#FF8BEA","header":"#472044","header2":"#873B7C","item":"#5A2955","item2":"#9B4990","item_hover":"#6D3567","item_hover2":"#B15AA5","bar":"#32162F","bar2":"#652B5E","text":"#FFF6FD","muted":"#E5C2DF","border":"#A45B9A"},
    "Gold":      {"accent":"#FFD36A","header":"#493A16","header2":"#8A6B24","item":"#5C491C","item2":"#9E7B2E","item_hover":"#705923","item_hover2":"#B58E3A","bar":"#33280F","bar2":"#684F1B","text":"#FFFCF2","muted":"#E7D9B4","border":"#A18749"},
}


def _mix(c1: str, c2: str, ratio: float) -> str:
    """c1へc2をratioだけ混ぜる。"""
    ratio = max(0.0, min(1.0, ratio))
    a = tuple(int(c1[i:i+2], 16) for i in (1, 3, 5))
    b = tuple(int(c2[i:i+2], 16) for i in (1, 3, 5))
    rgb = tuple(round(x * (1-ratio) + y * ratio) for x, y in zip(a, b))
    return "#%02X%02X%02X" % rgb


def palette(name: str) -> dict:
    # ベーステーマから用途別の色を派生させる。
    # 追加ボタンは通常アイテムより明るくし、カテゴリ追加とアイテム追加も差をつける。
    t = dict(THEMES.get(name, THEMES["Dark Gray"]))
    t["item_add"] = _mix(t["item"], t["text"], 0.10)
    t["item_add2"] = _mix(t["item2"], t["text"], 0.16)
    t["item_add_hover"] = _mix(t["item_hover"], t["text"], 0.16)
    t["item_add2_hover"] = _mix(t["item_hover2"], t["text"], 0.22)
    t["category_add"] = _mix(t["header"], t["text"], 0.15)
    t["category_add2"] = _mix(t["header2"], t["text"], 0.22)
    t["category_add_hover"] = _mix(t["header"], t["text"], 0.22)
    t["category_add2_hover"] = _mix(t["header2"], t["text"], 0.30)
    t["control"] = _mix(t["item"], t["bar"], 0.18)
    t["control2"] = _mix(t["item2"], t["header2"], 0.20)
    return t


def gradient(c1: str, c2: str) -> str:
    # 左下→右上。終端をさらに明るくしてグラデーション差を強調する。
    c3 = _mix(c2, "#FFFFFF", 0.28)
    return (
        "qlineargradient(x1:0, y1:1, x2:1, y2:0, "
        f"stop:0 {c1}, stop:0.46 {c2}, stop:1 {c3})"
    )


def app_qss(name: str) -> str:
    t = palette(name)
    return f"""
    QWidget {{
        font-family: "Segoe UI", "Yu Gothic UI", sans-serif;
        color: {t['text']};
    }}
    QToolTip {{
        background: {t['bar']}; color: {t['text']};
        border: 1px solid {t['border']}; padding: 2px 5px;
    }}
    QComboBox, QSpinBox, QLineEdit, QTextEdit {{
        background: {gradient(t['control'], t['control2'])}; color: {t['text']};
        border: 1px solid {t['border']}; border-radius: 5px;
        padding: 2px 6px;
        selection-background-color: {t['accent']};
        selection-color: #101216;
    }}
    QComboBox:hover, QSpinBox:hover, QLineEdit:hover, QTextEdit:hover {{
        border-color: {t['accent']};
    }}
    QComboBox QAbstractItemView {{
        background: {t['bar']}; color: {t['text']};
        border: 1px solid {t['border']};
        selection-background-color: {t['item_hover2']};
    }}
    QPushButton {{
        background: {gradient(t['control'], t['control2'])}; color: {t['text']};
        border: 1px solid {t['border']}; border-radius: 5px;
        padding: 2px 6px;
    }}
    QPushButton:hover {{ background: {gradient(t['item_hover'], t['item_hover2'])}; border-color: {t['accent']}; }}
    QPushButton:pressed {{ background: {t['header']}; }}
    QPushButton:checked {{
        background: {t['accent']}; color: #101216; font-weight: 700;
        border: 2px solid {t['text']};
    }}
    QCheckBox {{ color: {t['text']}; spacing: 5px; }}
    QDialog {{ background: {gradient(t['header'], t['header2'])}; }}
    QMenu {{
        background: {t['bar']}; color: {t['text']};
        border: 1px solid {t['border']}; border-radius: 5px;
        padding: 2px;
    }}
    QMenu::item {{ padding: 3px 11px; border-radius: 4px; }}
    QMenu::item:selected {{ background: {t['item_hover2']}; }}
    """
