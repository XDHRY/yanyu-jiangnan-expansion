"""Authoritative 340-card board: planned → implemented → validated → integrated.

The original 148 spec cards stay as detailed prompts. This module adds the
second wave (192 compact cards) and a machine-readable board that CI can
assert against. Status is evidence-based: a card is never marked integrated
just because a similar box exists in the town.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOARD = ROOT / "catalog" / "board.json"
WAVE2 = ROOT / "tasks" / "wave2"

# Live detail-stage evidence: ids that currently have geometry or shaders in
# expansion/scripts/*_detail.py. Honest, not aspirational.
IMPLEMENTED_148 = {
    "S01", "S02", "S03", "S04", "S05", "S06", "S10",
    "A001", "A002", "A005", "A010", "A017", "A021",
    "A025", "A026", "A027", "A028", "A030", "A031", "A032", "A033", "A034",
    "A035", "A036", "A037", "A038",
    "A041", "A043", "A044", "A047", "A050",
    "A053", "A054", "A055", "A057", "A058", "A060", "A064",
    "A073", "A074", "A075", "A077", "A078", "A080", "A083",
    "A085", "A089", "A091", "A092", "A094", "A095", "A096",
    "M01", "M02", "M03", "M04", "M05", "M06", "M07", "M08",
    "M09", "M10", "M11", "M12", "M13", "M14", "M15", "M16",
    "K01", "K07",
    "D01", "D02", "D03", "D04", "D05", "D06", "D07", "D08",
    "D09", "D10", "D11", "D12",
}

# Second-wave ids that this round actually ships geometry for.
IMPLEMENTED_WAVE2 = {
    "A097", "A098", "A099", "A100", "A101", "A102",
    "A121", "A132", "A142", "A143",
    "A161", "A162", "A163",
    "A182", "A183", "A184", "A185", "A186",
    "M17", "M18", "M19", "M26", "M27", "M28", "M30",
    "S13", "S14", "S15", "S16", "S17", "S18", "S22", "S23",
    "K13", "K14", "K15", "K16", "K18", "K20", "K24",
    "Q01", "Q02", "Q03", "Q22", "Q23", "Q26", "Q27",
    "Q29", "Q30", "Q31", "Q32", "Q33", "Q34", "Q35", "Q36", "Q37",
    "Q39",
    "V01", "V02", "V03", "V04", "V05", "V06",
}


def _card(task_id, kind, name, wave, priority, depends, evidence, status="planned"):
    return {
        "id": task_id,
        "type": kind,
        "name": name,
        "wave": wave,
        "priority": priority,
        "depends_on": depends,
        "evidence": evidence,
        "status": status,
    }


def _wave1_from_graph():
    graph = json.loads((ROOT / "catalog" / "task_graph.json").read_text(encoding="utf-8"))
    out = []
    for item in graph["tasks"]:
        tid = item["id"]
        status = "implemented" if tid in IMPLEMENTED_148 else "planned"
        out.append({
            "id": tid,
            "type": item["type"],
            "name": tid,
            "wave": 1,
            "priority": "P0" if tid.startswith(("S0", "A00", "M0", "D0")) else "P1",
            "depends_on": item.get("depends_on") or [],
            "path": item.get("path"),
            "evidence": "scripts/*_detail.py" if status != "planned" else "",
            "status": status,
        })
    return out


def _wave2():
    cards = []
    interiors = [
        ("A097", "格扇门成对", "real lattice door leaves in the opening"),
        ("A098", "民居床榻被褥", "bed, posts and quilt visible through the door"),
        ("A099", "灶台铁锅", "interior hearth and iron pot"),
        ("A100", "店内货架陶坛", "shop shelves and ceramic jars"),
        ("A101", "仓内货箱酒缸", "warehouse crates and vats"),
        ("A102", "室内油灯", "paper oil lamp on the floor plate"),
        ("A103", "二层楼梯", "stair void between storeys"),
        ("A104", "隔断屏风", "timber screen dividing the bay"),
        ("A105", "神龛香案", "household shrine against the back wall"),
        ("A106", "厨房碗柜", "kitchen cupboard and stacked bowls"),
        ("A107", "客栈铺位", "inn bunk row"),
        ("A108", "账房桌椅", "clerk desk visible from the shopfront"),
        ("A109", "阁楼铺板", "loft boards over the shop"),
        ("A110", "天井排水", "courtyard drain under the drip line"),
        ("A111", "后门卸货台", "service stoop at the rear wall"),
        ("A112", "马头墙墀头", "gable-end brick corbel"),
        ("A113", "内院天井", "open well between wings"),
        ("A114", "堂屋太师椅", "pair of chairs facing the door"),
        ("A115", "案上香炉", "censer on the hall table"),
        ("A116", "书房地台", "raised study platform"),
        ("A117", "厨房水缸", "water jar by the hearth"),
        ("A118", "储物壁橱", "wall cupboard"),
        ("A119", "楼板暴露梁", "exposed floor joists upstairs"),
        ("A120", "后门门槛", "rear threshold"),
    ]
    for tid, name, ev in interiors:
        cards.append(_card(tid, "asset", name, 2, "P0", ["A001", "S03"], ev))

    crafts = [
        ("A121", "摊位货篮陶坛布匹", "stall wares: basket, jar, cloth bolt"),
        ("A122", "木作刨台", "carpenter bench in workshop districts"),
        ("A123", "染缸晾架", "dye vats and drying poles"),
        ("A124", "窑炉匣钵", "kiln saggars"),
        ("A125", "药柜抽屉", "apothecary drawers"),
        ("A126", "酒旗幌子", "hanging trade banner"),
        ("A127", "手推车", "wood handcart on the quay"),
        ("A128", "砻谷石碾", "millstone in the farm district"),
        ("A129", "织机占位", "loom silhouette in the cloth shop"),
        ("A130", "铁砧风箱", "anvil and bellows"),
        ("A131", "茶焙烘笼", "tea-drying baskets"),
        ("A132", "渔网修补架", "net rack on the quay"),
        ("A133", "磨刀石", "whetstone by the workshop"),
        ("A134", "炭筐", "charcoal basket"),
        ("A135", "油篓", "oil jars in a row"),
        ("A136", "酱缸盖", "crock lids in the kitchen yard"),
        ("A137", "竹帘卷轴", "rolled bamboo blinds"),
        ("A138", "染布石砧", "beating stone for cloth"),
        ("A139", "船钉箱", "nail box at the boat shed"),
        ("A140", "量米斗", "grain dou measure"),
    ]
    for tid, name, ev in crafts:
        cards.append(_card(tid, "asset", name, 2, "P0", ["A053", "K08"], ev))

    ecology = [
        ("A141", "驳岸苔斑", "moss patches on wet stone"),
        ("A142", "睡莲浮萍加密", "lily pads along every reed clump"),
        ("A143", "月门后借景竹", "calligraphic bamboo beyond the moon gate"),
        ("A144", "河滩乱石", "shore rock groups"),
        ("A145", "茶树行", "tea rows in D09"),
        ("A146", "稻田块", "paddy plots"),
        ("A147", "岸边垂柳加密", "extra willows on the water edge"),
        ("A148", "落叶薄层", "fallen leaf scatter"),
        ("A149", "青苔瓦沟", "moss in tile valleys"),
        ("A150", "水埠青苔踏步", "algae on quay steps"),
        ("A151", "芦苇扩丛", "reed belts at every district edge"),
        ("A152", "荷花挺茎", "lotus stems above pads"),
        ("A153", "驳岸藤蔓", "vines on the revetment"),
        ("A154", "水边苔石", "mossy stones at the splash line"),
        ("A155", "岸柳气根", "willow roots into the bank"),
        ("A156", "浮萍条带", "duckweed strips in still water"),
        ("A157", "芦花穗", "reed seed heads"),
        ("A158", "池岸鸢尾", "iris clumps"),
        ("A159", "梅下落英", "fallen petals under the bough"),
        ("A160", "墙根蕨类", "ferns at the wall foot"),
    ]
    for tid, name, ev in ecology:
        cards.append(_card(tid, "asset", name, 2, "P0", ["A077", "A078"], ev))

    life = [
        ("A161", "井台水桶", "buckets at the shared well"),
        ("A162", "晾衣竹竿", "bamboo laundry poles with hung cloth on the quay"),
        ("A163", "门前石凳", "stone bench along the quay edge"),
        ("A164", "檐下鸟笼", "cage under the eave"),
        ("A165", "桥头候船凳", "waiting bench at the ferry"),
        ("A166", "孩童玩具风车", "tiny pinwheel on a stall"),
        ("A167", "渔篓绳索", "coiled rope on the boat"),
        ("A168", "蓑衣斗笠", "rain gear on the boat cabin"),
        ("A169", "灶边柴垛", "firewood stack"),
        ("A170", "猫狗占位剪影", "low animal silhouettes, no characters"),
        ("A171", "牌匾字层", "sign board without fake glyphs"),
        ("A172", "巷口土地龛", "tiny earth-god niche"),
        ("A173", "门环铺首", "door knockers"),
        ("A174", "台阶湿痕", "wet footprints on the stoop"),
        ("A175", "井绳辘轳", "well windlass"),
        ("A176", "檐下辣椒串", "drying peppers"),
        ("A177", "巷内水缸", "shared water jars"),
        ("A178", "桥栏湿手印", "wear polish on the rail"),
        ("A179", "船头香火", "tiny incense at the bow"),
        ("A180", "夜巷残灯", "one lantern left burning"),
    ]
    for tid, name, ev in life:
        cards.append(_card(tid, "asset", name, 2, "P1", ["A066", "K06"], ev))

    more_arch = [
        ("A181", "滴水瓦当", "drip tiles at the eave"),
        ("A182", "正吻走兽", "ridge beasts already on hip/gable ends"),
        ("A183", "挂落楣子", "hanging fascia under the eave beam"),
        ("A184", "美人靠", "gallery beauty-lean benches"),
        ("A185", "砖券月门", "segmented brick voussoir"),
        ("A186", "粉墙雨泪痕", "vertical rain-streak shader"),
        ("A187", "室内地坪高差", "threshold absorbs the 0.12 m road step"),
        ("A188", "窗下槛墙", "sill wall under lattice windows"),
        ("A189", "山墙搏风板", "barge boards on gables"),
        ("A190", "廊内灯龛", "lantern niche in the corridor"),
        ("A191", "天井四水归堂", "inward roof drainage"),
        ("A192", "封火山墙", "fire gable stepping"),
    ]
    for tid, name, ev in more_arch:
        cards.append(_card(tid, "asset", name, 2, "P0", ["A030", "A035"], ev))

    mats = [
        ("M17", "花瓣透光", "blossom SSS + faint emission"),
        ("M18", "湿青砖砂浆", "brick texture with mortar grooves"),
        ("M19", "旧粉墙雨痕", "plaster rain streaks"),
        ("M20", "油纸伞面", "oiled paper"),
        ("M21", "生锈铁件", "rusted iron micro"),
        ("M22", "青苔湿石", "algae on quay stone"),
        ("M23", "粗陶釉滴", "ceramic glaze runs"),
        ("M24", "旧麻布纤维", "cloth fibre"),
        ("M25", "竹编孔隙", "woven bamboo holes"),
        ("M26", "远山水墨", "ink-mountain panorama"),
        ("M27", "水面吸收体积", "water volume absorption"),
        ("M28", "灯笼透光纸", "lantern paper emission"),
        ("M29", "黛瓦青苔", "tile moss mix"),
        ("M30", "老梅树皮", "bark triplanar"),
        ("M31", "室内暖木", "interior timber warmer"),
        ("M32", "月色冷石", "moonlit stone response"),
    ]
    for tid, name, ev in mats:
        cards.append(_card(tid, "material", name, 2, "P0", ["S04", "S07"], ev))

    systems = [
        ("S13", "任务板状态机", "board.json four-state loop"),
        ("S14", "视觉QA统计", "mean/p01/p99 and dead-black check"),
        ("S15", "贴图与材质审计", "packed albedo presence"),
        ("S16", "提交预览/成片分流", "16spp preview vs HQ on main"),
        ("S17", "实例与共享网格", "content-hash mesh reuse"),
        ("S18", "确定性seed", "per-instance rng streams"),
        ("S19", "穿模漂浮门禁", "bounds vs water/ground"),
        ("S20", "法线与双面", "winding and smooth hints"),
        ("S21", "面数与性能预算", "face floors and blend size"),
        ("S22", "相机契约", "six named cameras always present"),
        ("S23", "环境叙事层", "life props tell use, not decoration"),
        ("S24", "旧化PBR通道", "roughness/bump/wetness not baked light"),
    ]
    for tid, name, ev in systems:
        cards.append(_card(tid, "system", name, 2, "P0", ["S02", "S04"], ev))

    assemblies = [
        ("K13", "店宅室内可视组", "door leaves + furniture"),
        ("K14", "摊位货品组", "wares on every stall"),
        ("K15", "水岸生态带", "reeds, lilies, moss"),
        ("K16", "月门借景组", "bamboo beyond the aperture"),
        ("K17", "作坊工具组", "benches and vats"),
        ("K18", "里巷生活组", "wells, buckets, laundry"),
        ("K19", "桥头生活组", "ferry bench and ropes"),
        ("K20", "屋顶收口组", "chiwen + fascia + chimes"),
        ("K21", "夜巷灯组", "lanterns plus interior oil lamps"),
        ("K22", "田庄作物组", "tea and paddy"),
        ("K23", "寺轴线香案组", "censer already present"),
        ("K24", "渔船生活组", "oar, basket, rain gear"),
    ]
    for tid, name, ev in assemblies:
        cards.append(_card(tid, "assembly", name, 2, "P1", ["K01", "K07"], ev))

    qa = [
        ("Q01", "manifest 计数门禁", "check_scene floors"),
        ("Q02", "缺失贴图门禁", "seven albedo files packed"),
        ("Q03", "相机六机位门禁", "named cameras exist"),
        ("Q04", "死黑检查", "p01 not crushed to 0 on hero shots"),
        ("Q05", "塑料感检查", "roughness not uniformly 0.2"),
        ("Q06", "雾量检查", "mean stays in night range 18-80"),
        ("Q07", "重复图案检查", "organic streets not a 6x6 grid"),
        ("Q08", "尺度检查", "bay 3.2 m, storey 3.25 m"),
        ("Q09", "穿模抽查", "boats sit on water_z"),
        ("Q10", "漂浮抽查", "no land below water"),
        ("Q11", "江南辨识度", "moon gate + plaster + tile + canal"),
        ("Q12", "生活逻辑", "doors, stalls, boats, lanterns"),
        ("Q13", "构图主次", "斜梅-月门-远山"),
        ("Q14", "冷暖分离", "moon cold, lanterns warm"),
        ("Q15", "近景厚重", "threshold, fascia, voussoir read"),
        ("Q16", "中景层次", "street recedes into mist"),
        ("Q17", "远景留白", "ink mountains, not a hard horizon"),
        ("Q18", "程序化痕迹", "no identical tree grid"),
        ("Q19", "面数预算", "faces >= 700k, blend < 80MB"),
        ("Q20", "实例化", "unique_meshes << mesh_objects"),
        ("Q21", "确定性", "same seed, same counts"),
        ("Q22", "HQ分流", "preview 16spp, HQ on main"),
        ("Q23", "artifact 完整", "png + blend + manifest + qa json"),
        ("Q24", "日志保留", "blender stdout uploaded"),
        ("Q25", "法线平滑", "roofs/hulls smoothed, walls faceted"),
        ("Q26", "材质槽合法", "only PALETTE slots on geometry"),
        ("Q27", "变体覆盖", "blossom/lantern_paper/bark resolve"),
        ("Q28", "室内不被门洞吃掉", "furniture sits behind 1.4 m"),
        ("Q29", "月门砖缝可读", "voussoir not a smooth torus"),
        ("Q30", "白梅夜可读", "blossoms not dark leaf blobs"),
        ("Q31", "脊兽不悬空", "chiwen on ridge, not eave tips"),
        ("Q32", "挂落贴梁", "fascia under the eave beam"),
        ("Q33", "美人靠向外", "gallery lean toward the street"),
        ("Q34", "雨泪痕竖直", "streak noise compressed in Z"),
        ("Q35", "摊位有货", "basket/jar/cloth on stalls"),
        ("Q36", "船有橹有篓", "oar and fish basket"),
        ("Q37", "水岸有萍", "lily pads at reeds"),
        ("Q38", "灯不抢戏", "warm only as local accents"),
        ("Q39", "总览不棋盘", "organic streets, not a CAD plot"),
        ("Q40", "巷道可走", "6 m spine, 0.12 m road lift"),
        ("Q41", "无IP网格", "no Wukong/Yan Yun ripped assets"),
        ("Q42", "seed 不交叉", "district streams isolated"),
        ("Q43", "LOD声明", "near hero, far instance"),
        ("Q44", "碰撞净空", "doors 2.25 m, galleries 0.92 m rail"),
        ("Q45", "贴图色彩空间", "albedo packed sRGB"),
        ("Q46", "体积雾有顶", "mist_top ~17 m"),
        ("Q47", "AgX 不漂白", "p99 < 200 on night shots"),
        ("Q48", "每轮出图", "six cameras every validated round"),
    ]
    for tid, name, ev in qa:
        cards.append(_card(tid, "qa", name, 2, "P0", ["S13", "S14"], ev))

    views = [
        ("V01", "听雨轩内视", "JNX_TingYuXuan from inside the pavilion"),
        ("V02", "月门借景", "JNX_MoonGate_Vista through the aperture"),
        ("V03", "运河英雄", "JNX_Canal_Hero along the water"),
        ("V04", "青石巷道", "JNX_Lane walking height"),
        ("V05", "平水探桥", "JNX_Water_Level"),
        ("V06", "十二区总览", "JNX_Overview"),
        ("V07", "店内窥视", "through a house door at night"),
        ("V08", "作坊院落", "workshop courtyard, D08"),
    ]
    for tid, name, ev in views:
        cards.append(_card(tid, "view", name, 2, "P0", ["S10", "S22"], ev))

    for card in cards:
        if card["id"] in IMPLEMENTED_WAVE2:
            card["status"] = "implemented"
    return cards


def build_board():
    cards = _wave1_from_graph() + _wave2()
    counts = {}
    for card in cards:
        counts[card["status"]] = counts.get(card["status"], 0) + 1
    board = {
        "schema_version": 1,
        "loop": ["planned", "implemented", "validated", "integrated"],
        "total": len(cards),
        "counts": counts,
        "tasks": cards,
    }
    if board["total"] != 340:
        raise SystemExit(f"board has {board['total']} cards, expected 340")
    return board


def write_wave2_markdown(cards):
    WAVE2.mkdir(parents=True, exist_ok=True)
    for card in cards:
        if card.get("wave") != 2:
            continue
        path = WAVE2 / f"{card['id']}.md"
        status = card["status"]
        body = (
            f"# {card['id']} · {card['name']}\n\n"
            f"**状态：{status}。** 闭环：planned → implemented → validated → integrated。\n"
            f"返回 [任务板](../../catalog/board.json) · [总索引](../../TASK_INDEX.md)。\n\n"
            f"- 类型：`{card['type']}`；优先级：`{card['priority']}`；波次：2。\n"
            f"- 依赖：{', '.join(card['depends_on']) or '无'}。\n"
            f"- 证据：{card['evidence']}\n"
            f"- 实现落点：现有 `expansion/scripts/*_detail.py` 与 GitHub Actions 视觉QA，"
            f"不新开 future/ 空工厂，不复制游戏提取网格。\n"
            f"- 完成标准：真实 Blender 渲染可辨认；未渲染不得标 validated；"
            f"未进入全景组装不得标 integrated。\n"
        )
        path.write_text(body, encoding="utf-8")


def write_state_md(board):
    lines = [
        "# 340 卡闭环状态",
        "",
        f"总计 **{board['total']}**。"
        + "  ".join(f"{k}={v}" for k, v in sorted(board["counts"].items())),
        "",
        "闭环：`planned → implemented → validated → integrated`。",
        "validated 必须有本轮渲染图；integrated 必须进入全景组装。",
        "",
        "| id | 类型 | 名称 | 状态 | 波次 |",
        "|---|---|---|---|---:|",
    ]
    for card in board["tasks"]:
        lines.append(
            f"| {card['id']} | {card['type']} | {card['name']} | {card['status']} | {card['wave']} |"
        )
    (ROOT / "STATE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    board = build_board()
    BOARD.write_text(json.dumps(board, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_wave2_markdown(board["tasks"])
    write_state_md(board)
    print(json.dumps({"total": board["total"], "counts": board["counts"]}, sort_keys=True))


if __name__ == "__main__":
    main()
