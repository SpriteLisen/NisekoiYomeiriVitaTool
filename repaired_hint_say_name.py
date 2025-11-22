import os
import glob
import csv

REPLACEMENT_RULES = {
    "@say 【小野寺】": "@say 【小玉】",
    "@say 【小野寺（琉璃）】": "@say 【小玉（琉璃）】",
    "@say 【学姐B】": "@say 【学长B】",
    "@say 【乐】": "@say 【一条 乐】",
    "@say 【千棘】": "@say 【桐崎 千棘】",
    "@say 【小咲】": "@say 【小野寺 小咲】",
    "@say 【诚士郎】": "@say 【鸫 诚士郎】",
    "@say 【万里花】": "@say 【橘 万里花】",
    "@say 【琉璃】": "@say 【宫本 琉璃】",
    "@say 【集】": "@say 【舞子 集】",
    "@say 【阿德鲁特】": "@say 【千棘的父亲】",
    "@say 【华】": "@say 【桐崎 华】",
}


def replace_in_csv(file_path):
    """
    在CSV文件中执行文本替换，只在有更改时写回文件
    """
    try:
        # 读取CSV文件内容
        original_rows = []
        modified_rows = []
        has_changes = False

        with open(file_path, 'r', encoding='utf-8-sig') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                original_rows.append(row.copy())  # 保存原始行

                # 处理第二列和第三列（索引1和2）
                original_row = row.copy()

                if len(row) > 1:  # 确保有第二列
                    for rule_old, rule_new in REPLACEMENT_RULES.items():
                        row[1] = row[1].replace(rule_old, rule_new)

                if len(row) > 2:  # 确保有第三列
                    for rule_old, rule_new in REPLACEMENT_RULES.items():
                        row[2] = row[2].replace(rule_old, rule_new)

                modified_rows.append(row)

                # 检查当前行是否有更改
                if row != original_row:
                    has_changes = True

        # 只有在有更改时才写回文件
        if has_changes:
            with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerows(modified_rows)
            return True, "已修改"
        else:
            return True, "无更改"

    except Exception as e:
        return False, str(e)


def process_csv_files(folder_path):
    """
    处理指定文件夹下的所有CSV文件
    """
    # 查找所有CSV文件
    csv_files = sorted(glob.glob(os.path.join(folder_path, "*.csv")))

    if not csv_files:
        print(f"在文件夹 '{folder_path}' 中未找到CSV文件")
        return

    print(f"找到 {len(csv_files)} 个CSV文件")
    print("替换规则配置:")
    for old_text, new_text in REPLACEMENT_RULES.items():
        print(f"  '{old_text}' -> '{new_text}'")
    print("=" * 60)

    success_count = 0
    modified_count = 0
    no_change_count = 0
    error_count = 0

    for file_path in csv_files:
        filename = os.path.basename(file_path)
        print(f"处理文件: {filename}", end=" ")

        success, result_msg = replace_in_csv(file_path)

        if success:
            if result_msg == "已修改":
                print("✅ 已修改")
                modified_count += 1
            else:
                print("⏭️  无更改")
                no_change_count += 1
            success_count += 1
        else:
            print(f"❌ 失败: {result_msg}")
            error_count += 1

    print("=" * 60)
    print(f"处理完成: 成功 {success_count} 个 (修改 {modified_count} 个, 无更改 {no_change_count} 个), 失败 {error_count} 个")


def main():
    folder_path = "scripts/extract"
    process_csv_files(folder_path)


if __name__ == "__main__":
    main()
