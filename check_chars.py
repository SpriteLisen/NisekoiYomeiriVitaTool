import sys
import csv
import opencc
from pathlib import Path


def detect_traditional_and_japanese_in_directory(directory):
    converter = opencc.OpenCC('t2s')

    japanese_chars = set("""
    ぁあぃいぅうぇえぉおかがきぎくぐけげこごさざしじすずせぜそぞただちぢっつづてでとどなにぬねのはばぱひびぴふぶぷへべぺほぼぽまみむめもゃやゅゆょよらりるれろゎわゐゑをん゛゜ゝゞ
    ァアィイゥウェエォオカガキギクグケゲコゴサザシジスズセゼソゾタダチヂッツヅテデトドナニヌネノハバパヒビピフブプヘベペホボポマミムメモャヤュユョヨラリルレロヮワヰヱヲンヴヵヶヽヾ
    """.replace('\n', '').replace(' ', ''))

    # 和制汉字（国字）完整列表
    japanese_only_kanji = set("""
        鶫 栃 椛 辻 畠 凪 雫 峠 榊 畑 込 迯 躾 働 鱚 鰯 鮨 鮓 鯱 麿 俤 凧
        凩 噺 杢 枠 栂 柾 栴 梺 槙 樫 橇 毟 毬 涙 渋 砿 筈 簗 綛 縒 繋
        罅 苅 莚 萠 蓙 蘂 蜆 蟷 衒 袴 襦 軈 辻 這 遖 邨 釼 鎹 閊 頰
        餠 饂 饅 駈 髢 魛 魴 鮒 鮟 鮠 鮪 鮫 鰆 鰈 鰊 鰍 鰐 鰒 鰕 鰛 鰤 鱈
        枠 栂 栃 椛 辻 畠 峠 凪 雫 麿 凧 凩 杢 梺 槙 樫 橇 毟 毬 砿 筈
        簗 綛 縒 繋 罅 苅 莚 萠 蓙 蘂 蜆 蟷 衒 襦 軈 遖 邨 釼 鎹 閊 髢

        匁 俥 凅 劦 勹 匸 卩 卬 厎 厖 厠 叺 吋 呎 咢 哘 垳 堺 塀 墹 壱 夊
        夛 姙 娚 娵 婀 媼 嬶 宀 岾 峩 嵯 嶋 巛 巵 幵 庁 廾 弖 彅 徂 怱 恷
        悳 惣 惤 惷 戉 扨 挊 挌 捗 揃 摑 擡 昻 昿 晄 暃 暘 曻 朏 朞 柧
        栐 栫 桙 桛 桟 梠 梶 椈 椊 椏 楕 楯 楳 榎 榧 榿 槎 槔 槧 樋 樽 橸
        檍 檮 櫁 櫂 櫟 櫨 欅 歿 毉 毖 毘 氷 汸 沍 沚 泙 洟 浤 渕 湫 溏
        漣 潅 澁 澆 澑 澣 澪 瀧 灘 炑 烝 焔 燁 燵 爨 牀 牋 犲 犲 狢 狹
        狽 猯 珱 琲 瑠 璢 瓧 瓰 瓱 瓲 甃 甅 甎 甑 甓 甕 甖 甞 畦 畧 疂 瘧
        瘭 癪 皹 盥 盦 眛 睇 瞋 瞠 磯 礑 祇 祢 禰 秌 竂 筥 箆 箟 箒 箙
        箞 箦 箬 箸 篭 篳 簀 簃 簓 簔 籐 籔 籏 籖 籘 籤 籥 糀 糒 糘 糝 糶
        紏 絣 綉 綯 縒 繧 繿 罘 罟 羂 羃 耆 耒 耨 肬 胂 胄 胩 脇 腟 腨 膵
        臈 臍 臑 臘 舛 艸 苆 苧 茣 荊 荻 菖 萓 葢 蓚 蓧 蓴 蕗 蕣 蕷 薗 薤
        薮 藁 藜 藟 蘓 蘖 蘰 虻 蚋 蜊 蝋 螢 蟇 蟇 蠎 蠣 蠧 衂 衟 衠 袰 裃
        裄 褄 襃 襅 襷 襻 訖 詬 詮 誂 誄 誨 誧 諏 諒 謄 謚 謠 謳 譁 讃 豈
        賹 贉 趂 趺 跏 跚 踈 踠 蹇 蹌 蹏 蹟 躡 躪 軅 轌 辻 迚 逎 逧 逵 逹
        鄕 酢 醂 醍 醐 釼 鈑 鈔 鈬 鉈 鉉 鉢 銕 銛 銜 銷 鋏 鋤 鋥 鋭 鋸 鍔
        鎚 鎰 鏑 鏤 鐡 鑞 閖 闘 陦 雩 靏 靱 鞆 鞱 韈 韮 頞 頟 顋 顚 飩 飮
        飰 餉 餝 饉 饌 饑 駈 驛 驫 髟 鬚 鬮 魞 魵 鮇 鮑 鮹 鰒 鰛 鰟 鰦 鱚
        鱟 鱧 鱲 鳰 鴟 鴫 鵄 鵆 鵤 鶉 鶚 鶯 鷗 鷲 鷽 鸛 麪 麸 麹 鼈 鼡
    """.replace('\n', ' ').split())

    japanese_chars = {c for c in japanese_chars if c.strip()}

    all_results = {}

    for file_path in sorted(Path(directory).rglob(f'*.csv')):
        problematic = []

        with open(file_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
            try:
                reader = csv.reader(f)
            except Exception:
                reader = csv.reader(f, delimiter=";")

            next(reader)

            for line_num, row in enumerate(reader, 1):
                line = row[2].rstrip('\n\r')
                if not line:
                    continue

                matched_chars = []
                for char in line:
                    converted = converter.convert(char)

                    if converted != char:
                        matched_chars.append(f"繁体汉字: {char}")
                    elif converted in japanese_only_kanji:
                        matched_chars.append(f"日文汉字: {char}")
                    elif char in japanese_chars:
                        matched_chars.append(f"平片假字: {char}")

                if matched_chars:
                    problematic.append((line_num + 1, line[:100], matched_chars))

        if problematic:
            all_results[str(file_path)] = problematic

    return all_results


def wait_for_enter_to_exit(prompt="按回车键退出程序..."):
    try:
        input(prompt)
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        sys.exit(0)


if __name__ == "__main__":
    # results = detect_traditional_and_japanese_in_directory("scripts/extract/")
    results = detect_traditional_and_japanese_in_directory("./")

    with open("log.txt", "w", encoding="utf-8") as f:
        for file_path, lines in results.items():
            print(f"\n{file_path}:")
            f.write(f"\n{file_path}:\n")
            for line_num, line, chars in lines:
                print(f"  行 {line_num}: {line[:50]}")
                print(f"    字符: {', '.join(chars)}")

                f.write(f"  行 {line_num}: {line[:50]}\n")
                f.write(f"    字符: {', '.join(chars)}\n")

    print()
    wait_for_enter_to_exit()
