import arcpy
import json
import os

# ================= 配置区 =================
# 请将这里改为你下载的 JSON 文件的实际路径
# 如果在 Pro 的 Python 窗口运行，请使用绝对路径，例如: r"C:\Users\Name\Downloads\arcgis_color_data.json"
JSON_PATH = "arcgis_color_data.json"  
STYLE_NAME = "My_GIS_Colors.stylx"
# ==========================================

def hex_to_cim_color(hex_code):
    """将 Hex 转换为 CIMRGBColor"""
    hex_code = hex_code.lstrip('#')
    rgb = tuple(int(hex_code[i:i+2], 16) for i in (0, 2, 4))
    c = arcpy.cim.CIMRGBColor()
    c.values = [rgb[0], rgb[1], rgb[2], 100]
    return c

def create_stylx():
    print(f"正在读取数据: {JSON_PATH}...")
    
    if not os.path.exists(JSON_PATH):
        print(f"错误: 找不到文件 {JSON_PATH}，请检查路径。")
        return

    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 获取当前项目 (如果在 Pro 内部)
    try:
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        home = aprx.homeFolder
    except:
        home = os.getcwd() # 如果在外部 Python 运行

    style_path = os.path.join(home, STYLE_NAME)
    
    # 1. 创建空的 Style 文件
    if os.path.exists(style_path):
        print(f"样式文件已存在，将被覆盖: {style_path}")
        os.remove(style_path)
    
    arcpy.management.CreateMobileStyle(home, STYLE_NAME.replace(".stylx", ""))
    print(f"已创建样式容器: {style_path}")

    # 2. 循环处理每个色带
    print(f"开始处理 {len(data)} 个色带...")
    
    for item in data:
        name = item['name']
        colors = item['colors']
        category = item['category']
        
        try:
            # 构建颜色列表
            cim_colors = [hex_to_cim_color(c) for c in colors]
            
            # 构建多部分色带 (Multipart)
            # 这是一个简化的构建方式，创建平滑的 Algorithmic Color Ramp
            color_ramps = []
            for i in range(len(cim_colors) - 1):
                alg_ramp = arcpy.cim.CIMAlgorithmicColorRamp()
                alg_ramp.fromColor = cim_colors[i]
                alg_ramp.toColor = cim_colors[i+1]
                alg_ramp.algorithm = "HSV" # 混合算法
                alg_ramp.mainColor = cim_colors[i]
                color_ramps.append(alg_ramp)
            
            multi_ramp = arcpy.cim.CIMMultipartColorRamp()
            multi_ramp.colorRamps = color_ramps
            
            # 创建 Item 并添加到 Style
            # 注意: ArcPy 直接将 CIM 对象写入 Stylx 比较复杂，通常使用 AddItem
            # 这里我们使用一个替代方案：生成临时 .clr 然后导入 (如果有 Import 工具)
            # 但为了脚本独立性，我们把颜色打印出来提示用户
            # 在 Pro 3.x+ 中，你可以尝试 arcpy.mp.AddItemToStyle (如果支持 CIM)
            
            # 兼容性方案：
            # 由于 ArcPy 缺乏直接“Save CIM to Stylx”的简单函数
            # 我们将生成 CLR 文件到同名文件夹，这是最稳妥的批量方法
            pass

        except Exception as e:
            print(f"处理 {name} 时出错: {e}")

    # ---------------------------------------------------------
    # 真正的批量生成方案 (生成文件夹)
    # ---------------------------------------------------------
    output_dir = os.path.join(home, "Color_Ramps_Output")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    for item in data:
        safe_name = "".join([c for c in item['name'] if c.isalnum() or c in (' ','-','_')]).strip()
        filename = os.path.join(output_dir, f"{item['category']}_{safe_name}.clr")
        
        with open(filename, "w") as f:
            for idx, hex_code in enumerate(item['colors']):
                h = hex_code.lstrip('#')
                rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
                f.write(f"{idx+1} {rgb[0]} {rgb[1]} {rgb[2]}\n")
    
    print("="*30)
    print("完成！")
    print("由于 ArcPy 限制，直接写入 .stylx 需要底层 .NET SDK。")
    print(f"已将所有色带生成为 .clr 文件，保存在: {output_dir}")
    print("导入方法: 打开 ArcGIS Pro -> 样式 -> 导入 -> 选择该文件夹下的所有 .clr 文件")
    print("="*30)

if __name__ == "__main__":
    create_stylx()
