import sys
import platform
import subprocess
from pathlib import Path


FREE_TALK_DDS_SIZE = (1024, 1024)


def tool_command(executable):
    command = []
    if platform.system() in ("Darwin", "Linux"):
        command.append("wine")
    command.append(executable)
    return command


def run_tool(command, failed_message, missing_message):
    try:
        subprocess.run(
            command,
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        print("stdout:", e.stdout)
        print("stderr:", e.stderr)
        raise RuntimeError(f"{failed_message}: {e} => {e.stderr}")
    except FileNotFoundError:
        raise RuntimeError(missing_message)


def pad_png_canvas(png_file, output_dir, width, height):
    output_dir = Path(output_dir)
    padded_png = output_dir / png_file.name
    command = tool_command(r".\tools\ImageMagick\magick.exe")
    command.extend(
        [
            str(png_file),
            "-background", "none",
            "-gravity", "northwest",
            "-extent", f"{width}x{height}",
            str(padded_png),
        ]
    )
    run_tool(command, "Pad png failed", "Not find ImageMagick.")
    return padded_png


def convert_png_to_dds(png_file, output_dir, pad_to=None):
    """
    将 PNG 文件转换为 DDS 文件。

    pad_to 用于随谈大图：先扩到 1024x1024 透明画布，再走同一套 DDS 转换。
    """
    png_file = Path(png_file)
    output_dir = Path(output_dir)
    source_file = png_file
    if pad_to:
        source_file = pad_png_canvas(png_file, output_dir, *pad_to)

    command = tool_command(r".\tools\texconv\texconv.exe")
    command.extend(
        [
            # "-f", "DXT3",
            "-f", "DXT5",
            "-ft", "dds",
            "-o", str(output_dir),
            "-y",
            str(source_file),
        ]
    )
    run_tool(command, "Convert dds failed", "Not find texconv.")
    padded = " padded" if pad_to else ""
    print(f"Convert {png_file.name} to{padded} dds succeed!")


def convert_png_to_tga(png_file, output_dir):
    """
    将 PNG 文件转换为 TAG 文件
    """
    png_file = Path(png_file)
    output_dir = Path(output_dir)
    command = tool_command(r".\tools\ImageMagick\magick.exe")
    command.extend(
        [
            str(png_file),
            str(output_dir / f"{png_file.stem}.tga"),
        ]
    )
    run_tool(command, "Convert tga failed", "Not find ImageMagick.")
    print(f"Convert {png_file.name} to tga succeed!")


def convert_to_gxt(img_file, output_dir):
    """
    将文件转换为 GXT 文件
    """
    gxt_output_path = output_dir / f"{img_file.stem}.gxt"
    command = tool_command(r".\tools\psp2gxt\psp2gxt.exe")
    command.extend(["-i", str(img_file), "-o", str(gxt_output_path)])
    run_tool(command, "Convert gxt failed", "Not find psp2gxt.")
    print(f"Convert {img_file.name} to gxt succeed!")


def process_png_files(input_dir, output_dir):
    """
    递归处理输入目录下的所有PNG文件
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    use_padded_dxt = input_path.name == "free_talk_cmt"

    # 确保输出目录存在
    output_path.mkdir(parents=True, exist_ok=True)

    # 递归查找所有PNG文件
    png_files = sorted(input_path.rglob("*.[Pp][Nn][Gg]"), key=lambda x: x.name.lower())

    if not png_files:
        print(f"在目录 {input_dir} 中未找到PNG文件")
        return

    print(f"找到 {len(png_files)} 个PNG文件")
    print("-" * 80 + "开始转换" + "-" * 80)

    # 临时目录
    temp_img_dir = output_path / "temp_img"
    temp_img_dir.mkdir(exist_ok=True)

    # 第一步：将所有PNG转换为DDS/TGA
    for png_file in png_files:
        # 计算相对路径，用于保持目录结构
        relative_path = png_file.relative_to(input_path)
        tmp_img_subdir = temp_img_dir / relative_path.parent

        # 创建对应的输出目录
        tmp_img_subdir.mkdir(parents=True, exist_ok=True)

        print(f"处理: {relative_path}")

        # 字形图和随谈大图做 dds, 内存小很多
        if use_padded_dxt:
            convert_png_to_dds(png_file, tmp_img_subdir, pad_to=FREE_TALK_DDS_SIZE)
        elif png_file.name == 'font_j24x24_0.png':
            convert_png_to_dds(png_file, tmp_img_subdir)
        else:
            convert_png_to_tga(png_file, tmp_img_subdir)

    print()
    print("-" * 80 + "开始编译GXT产品" + "-" * 80)

    # 第二步：将所有 DDS/TGA 转换为 GXT
    img_files = sorted(
        [f for f in temp_img_dir.rglob('*') if f.suffix.lower() in ['.dds', '.tga']],
        key=lambda x: x.name.lower()
    )

    for img_file in img_files:
        # 计算相对路径
        relative_path = img_file.relative_to(temp_img_dir)
        gxt_subdir = output_path / relative_path.parent

        # 创建对应的GXT输出目录
        gxt_subdir.mkdir(parents=True, exist_ok=True)

        print(f"处理: {relative_path}")
        convert_to_gxt(img_file, gxt_subdir)

    # 清理临时文件
    print("\n清理临时文件...")
    import shutil
    shutil.rmtree(temp_img_dir)
    print("转换完成！")


def main():
    input_directory = sys.argv[1] if len(sys.argv) > 1 else "images/modified"
    # input_directory = "images/origin"
    output_directory = sys.argv[2] if len(sys.argv) > 2 else "images/rebuild"

    # 处理PNG文件
    process_png_files(input_directory, output_directory)


if __name__ == "__main__":
    main()
