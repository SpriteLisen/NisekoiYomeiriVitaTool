import platform
import subprocess
from pathlib import Path

prefix_gxt = ".gxt"
prefix_dds = ".dds"


def convert_png_to_dds(png_file, output_dir):
    """
    将 PNG 文件转换为 DDS 文件
    """
    try:
        command = []
        system = platform.system()

        if system == "Darwin" or system == "Linux":
            command.append("wine")

        command.extend(
            [
                r".\tools\texconv\texconv.exe",
                "-f", "DXT3",
                "-ft", "dds",
                "-o", output_dir,
                "-y",
                f"{png_file}"
            ]
        )

        # 执行 texconv 转换命令
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            # text=True
        )
        print(f"Convert {png_file.name} to dds succeed!")
    except subprocess.CalledProcessError as e:
        print("stdout:", e.stdout)
        print("stderr:", e.stderr)
        raise RuntimeError(f"Convert dds failed: {e} => {e.stderr}")
    except FileNotFoundError:
        raise RuntimeError("Not find ImageMagick.")


def convert_dds_to_gxt(dds_file, output_dir):
    """
    将 DDS 文件转换为 GXT 文件
    """
    try:
        # 构建输出GXT文件路径
        gxt_output_path = output_dir / f"{dds_file.stem}{prefix_gxt}"

        command = []
        system = platform.system()

        if system == "Darwin" or system == "Linux":
            command.append("wine")

        command.extend(
            [r".\tools\psp2gxt\psp2gxt.exe", "-i", dds_file, "-o", str(gxt_output_path)]
        )

        # 执行 psp2gxt 转换命令
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            # text=True
        )
        print(f"Convert {dds_file.name} to gxt succeed!")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Convert gxt failed: {e} => {e.stderr}")
    except FileNotFoundError:
        raise RuntimeError("Not find psp2gxt.")


def process_png_files(input_dir, output_dir):
    """
    递归处理输入目录下的所有PNG文件
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)

    # 确保输出目录存在
    output_path.mkdir(parents=True, exist_ok=True)

    # 递归查找所有PNG文件
    png_files = sorted(input_path.rglob("*.[Pp][Nn][Gg]"), key=lambda x: x.name.lower())

    if not png_files:
        print(f"在目录 {input_dir} 中未找到PNG文件")
        return

    print(f"找到 {len(png_files)} 个PNG文件")
    print("-" * 80 + "开始转换DDS" + "-" * 80)

    # 临时DDS目录
    temp_dds_dir = output_path / "temp_dds"
    temp_dds_dir.mkdir(exist_ok=True)

    # 第一步：将所有PNG转换为DDS
    for png_file in png_files:
        # 计算相对路径，用于保持目录结构
        relative_path = png_file.relative_to(input_path)
        dds_subdir = temp_dds_dir / relative_path.parent

        # 创建对应的DDS输出目录
        dds_subdir.mkdir(parents=True, exist_ok=True)

        print(f"处理: {relative_path}")
        convert_png_to_dds(png_file, dds_subdir)

    print()
    print("-" * 80 + "开始编译GXT产品" + "-" * 80)

    # 第二步：将所有 DDS 转换为 GXT
    dds_files = sorted(temp_dds_dir.rglob("*.[Dd][Dd][Ss]"), key=lambda x: x.name.lower())

    for dds_file in dds_files:
        # 计算相对路径
        relative_path = dds_file.relative_to(temp_dds_dir)
        gxt_subdir = output_path / relative_path.parent

        # 创建对应的GXT输出目录
        gxt_subdir.mkdir(parents=True, exist_ok=True)

        print(f"处理: {relative_path}")
        convert_dds_to_gxt(dds_file, gxt_subdir)

    # 清理临时DDS文件（可选）
    print("\n清理临时DDS文件...")
    import shutil
    shutil.rmtree(temp_dds_dir)
    print("转换完成！")


def main():
    input_directory = "images/modified"
    # input_directory = "images/origin"
    output_directory = "images/rebuild"

    # 处理PNG文件
    process_png_files(input_directory, output_directory)


if __name__ == "__main__":
    main()
