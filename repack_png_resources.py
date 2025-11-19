import os
import subprocess
from pathlib import Path


prefix_gxt = ".gxt"
prefix_dds = ".dds"

dds_dir = "."
product_dir = "."

def convert_png_to_dds(png_file):
    os.makedirs(dds_dir, exist_ok=True)

    try:
        # 执行 texconv 转换命令
        subprocess.run([
            r".\tools\texconv\texconv.exe",
            "-f", "DXT3",
            "-ft", "dds",
            "-o", ".",
            "-y",
            f"{png_file}"
        ],
            check=True,
            capture_output=True,
            text=True
        )
        print(f"Convert {png_file.name} to dds succeed!")
    except subprocess.CalledProcessError as e:
        print("stdout:", e.stdout)
        print("stderr:", e.stderr)
        raise RuntimeError(f"Convert dds failed: {e} => {e.stderr}")
    except FileNotFoundError:
        raise RuntimeError("Not find ImageMagick.")

def convert_dds_to_gxt(dds_file):
    try:
        # 执行 psp2gxt 转换命令
        subprocess.run(
            [r".\tools\psp2gxt\psp2gxt.exe", "-i", dds_file, "-o", f"{product_dir}/{dds_file.stem}{prefix_gxt}"],
            check=True,
            capture_output=True,
            text=True
        )
        print(f"Convert {dds_file.name} to gxt succeed!")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Convert gxt failed: {e} => {e.stderr}")
    except FileNotFoundError:
        raise RuntimeError("Not find psp2gxt.")


def compile_to_product(dds_file):
    os.makedirs(product_dir, exist_ok=True)

    convert_dds_to_gxt(dds_file)



if __name__ == "__main__":
    files = sorted(Path(".").glob("*.[Pp][Nn][Gg]"), key=lambda x: x.name.lower())

    print("-" * 80 + "Start convert dds" + "-" * 80)
    for file in files:
        convert_png_to_dds(file)

    print()
    print("-" * 80 + "Start compile product" + "-" * 80)
    files = sorted(Path(dds_dir).glob("*.[Dd][Dd][Ss]"), key=lambda x: x.name.lower())
    for file in files:
        compile_to_product(file)

