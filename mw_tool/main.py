import streamlit as st
import pubchempy as pcp
from rdkit import Chem
from rdkit.Chem import rdMolDescriptors
import requests
from io import BytesIO

st.set_page_config(
    page_title="质量及密度查询",
    layout="wide"
)

# 初始化 session state
if 'compound_data' not in st.session_state:
    st.session_state.compound_data = None

def search_compound(query):
    """搜索化合物信息"""
    try:
        compounds = None
        try:
            comp = Chem.MolFromSmiles(query)
            if comp:
                compounds = pcp.get_compounds(query, 'smiles', listkey_count=3)
        except Exception:
            st.error("使用smiles精确查询失败")
        # 尝试通过化学式搜索
        if not (isinstance(compounds, list) and len(compounds) != 0):
            # 尝试通过名称搜索
            try:
                compounds = pcp.get_compounds(query, 'name', listkey_count=3)
            except Exception:
                st.error("使用名称查询失败")
            
        if not (isinstance(compounds, list) and len(compounds) != 0):
            try:
                compounds = pcp.get_compounds(query, 'formula', listkey_count=3)
            except Exception:
                st.error("使用化学式精确查询失败")
        
        if isinstance(compounds, list) and len(compounds) > 0:
            st.info("成功查询物质基本信息，正在获取更多数据。")
            return compounds[0]
        else:
            return None
    except Exception as e:
        st.error(f"搜索时发生错误: {str(e)}")
        # raise e
        return None

def calculate_molecular_weight_from_smiles(smiles):
    """从SMILES计算分子量"""
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol:
            return rdMolDescriptors.CalcExactMolWt(mol)
        else:
            return None
    except Exception as e:
        st.error(f"SMILES分子量计算错误: {str(e)}")
        return None

def generate_molecule_image(inchi=None, smiles=None):
    """从SMILES生成分子结构图"""
    return None
    try:
        if inchi:
            mol = Chem.MolFromInchi(inchi)
        elif smiles:
            mol = Chem.MolFromSmiles(smiles)
        else:
            st.error("必须提供InChI或SMILES字符串")
            return None
        if mol:
            # 生成分子图像
            img = Draw.MolToImage(mol, size=(300, 300))
            # 将图像转换为字节流
            img_buffer = BytesIO()
            img.save("a.png")
            img.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            return img_buffer
        else:
            return None
    except Exception as e:
        st.error(f"分子结构图生成错误: {str(e)}")
        return None

def get_pubchem_properties(compound):
    """从PubChem获取密度、熔点、沸点信息"""
    try:
        # 初始化返回数据
        properties = {
            'density': None,
            'melting_point': None,
            'boiling_point': None
        }

        cid = compound.cid
        
        # 尝试获取物理化学性质相关的记录
        try:
            url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON?heading=Experimental+Properties"
            data = requests.get(url, timeout=3).json()
            for section in data["Record"]["Section"]:
                if section["TOCHeading"] == "Chemical and Physical Properties":
                    for sub in section["Section"]:
                        if sub["TOCHeading"] == "Experimental Properties":
                            for prop in sub["Section"]:
                                prop_heading = prop["TOCHeading"]
                                
                                if prop_heading == "Density" and not properties['density']:
                                    # 可能有多条不同温度/浓度的记录，逐条返回
                                    properties['density'] = [
                                        info["Value"]["StringWithMarkup"][0]["String"]
                                        for info in prop["Information"]
                                        if "Value" in info and "StringWithMarkup" in info["Value"]
                                    ]
                                
                                elif prop_heading == "Melting Point" and not properties['melting_point']:
                                    properties['melting_point'] = [
                                        info["Value"]["StringWithMarkup"][0]["String"]
                                        for info in prop["Information"]
                                        if "Value" in info and "StringWithMarkup" in info["Value"]
                                    ]
                                
                                elif prop_heading == "Boiling Point" and not properties['boiling_point']:
                                    properties['boiling_point'] = [
                                        info["Value"]["StringWithMarkup"][0]["String"]
                                        for info in prop["Information"]
                                        if "Value" in info and "StringWithMarkup" in info["Value"]
                                    ]
            
            return properties
            
        except Exception:
            return properties
    
    except Exception as e:
        # 静默处理异常，返回空的properties字典
        return {
            'density': None,
            'melting_point': None,
            'boiling_point': None
        }

def is_liquid_at_room_temp(melting_point):
    """判断常温下是否为液体（假设常温为25°C）"""
    if melting_point is None:
        return False
    try:
        mp = float(melting_point)
        return mp < 25  # 熔点低于25°C认为是液体
    except:
        return False

def sync_calculations(compound_data, mmol=None, mass=None, volume=None, changed_field=None):
    """同步计算mmol、质量、体积"""
    if not compound_data:
        return mmol, mass, volume
    
    # 确保数值类型转换
    try:
        molecular_weight = float(compound_data.get('molecular_weight', 0))
        density_select = compound_data.get('density_select', None)
        density = float(density_select) if density_select is not None else None
    except (ValueError, TypeError):
        st.error("分子量或密度数据格式错误，无法进行计算")
        return mmol, mass, volume
    
    if molecular_weight == 0:
        return mmol, mass, volume
    
    try:
        if changed_field == 'mmol' and mmol is not None:
            # 根据mmol计算质量
            mass = (mmol / 1000) * molecular_weight  # mmol转mol再乘分子量
            # 如果有密度，计算体积
            if density and density > 0:
                volume = mass / density
        
        elif changed_field == 'mass' and mass is not None:
            # 根据质量计算mmol
            mmol = (mass / molecular_weight) * 1000  # 质量除分子量得mol，再转mmol
            # 如果有密度，计算体积
            if density and density > 0:
                volume = mass / density
        
        elif changed_field == 'volume' and volume is not None and density and density > 0:
            # 根据体积计算质量
            mass = volume * density
            # 根据质量计算mmol
            mmol = (mass / molecular_weight) * 1000
    
    except Exception as e:
        st.error(f"计算错误: {str(e)}")
    
    return mmol, mass, volume

# 主界面
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("物质查询")
    query = st.text_input("输入化学式、名称或SMILES:", placeholder="例如: H2O, water, CCO")
    
    # 添加直接计算分子量选项
    calc_mw_only = st.checkbox("仅计算分子量（不查询数据库）", help="勾选此项将跳过数据库查询，仅从SMILES计算分子量")
    
    if st.button("查询" if not calc_mw_only else "计算", type="primary"):
        if query:
            with st.spinner("正在处理..."):
                # 如果选择仅计算分子量，直接从SMILES计算
                if calc_mw_only:
                    mol_weight = calculate_molecular_weight_from_smiles(query)
                    if mol_weight:
                        compound_data = {
                            'name': "用户输入化合物",
                            'formula': "从SMILES计算",
                            'molecular_weight': mol_weight,
                            'melting_point': None,
                            'density_src': None,
                            'melting_point_src': None,
                            'boiling_point_src': None,
                            'smiles': query,
                            "inchi": None,
                            'found': False
                        }
                        st.session_state.compound_data = compound_data
                        st.success("✅ 分子量计算完成！")
                    else:
                        st.error("❌ 输入的SMILES格式无效")
                        st.session_state.compound_data = None
                else:
                    # 原有的查询逻辑
                    compound = search_compound(query)
                
                    if compound is not None:
                        # 查询到化合物
                        # 获取PubChem的物理化学性质信息
                        pubchem_properties = get_pubchem_properties(compound)
                        
                        compound_data = {
                            'name': compound.iupac_name,
                            'cid': compound.cid,
                            'formula': compound.molecular_formula,
                            'molecular_weight': compound.molecular_weight,
                            "density_src": pubchem_properties['density'],
                            'melting_point_src': pubchem_properties['melting_point'],
                            'boiling_point_src': pubchem_properties['boiling_point'],
                            'smiles': compound.canonical_smiles,
                            "inchi": compound.inchi if hasattr(compound, 'inchi') else None,
                            'found': True,
                        }
                        

                        st.session_state.compound_data = compound_data
                        
                        # 显示查询结果信息
                        if compound_data['density_src'] or compound_data['melting_point_src'] or compound_data['boiling_point_src']:
                            properties_found = []
                            if compound_data['density_src']:
                                properties_found.append("密度")
                            if compound_data['melting_point_src']:
                                properties_found.append("熔点")
                            if compound_data['boiling_point_src']:
                                properties_found.append("沸点")
                            st.success(f"✅ 查询成功！（找到{', '.join(properties_found)}信息）")
                        else:
                            st.success("✅ 查询成功！（未找到物理性质信息）")
                    
                    else:
                        # 未查询到，检查是否为SMILES
                        if query:
                            mol_weight = calculate_molecular_weight_from_smiles(query)
                            if mol_weight:
                                compound_data = {
                                    'name': "未知化合物",
                                    'formula': "从SMILES计算",
                                    'molecular_weight': mol_weight,
                                    'melting_point': None,
                                    'density_src': None,
                                    'melting_point_src': None,
                                    'boiling_point_src': None,
                                    'smiles': query,
                                    "inchi": None,
                                    'found': False
                                }
                                st.session_state.compound_data = compound_data
                                st.warning("⚠️ 未在数据库中找到，但已从SMILES计算分子量")
                            else:
                                st.error("❌ 未找到该化合物，且SMILES格式无效")
                                st.session_state.compound_data = None

with col2:
    st.subheader("化合物信息")
    
    if st.session_state.compound_data:
        data = st.session_state.compound_data
        
        # 显示基本信息
        info_col1, info_col2 = st.columns(2)
        
        with info_col1:
            st.metric("物质名称", data['name'])
            try:
                molecular_weight_value = float(data['molecular_weight'])
                st.metric("分子量 (g/mol)", f"{molecular_weight_value:.3f}")
            except (ValueError, TypeError):
                st.metric("分子量 (g/mol)", "数据格式错误")
        
        with info_col2:
            st.metric("化学式", data['formula'])
            if data.get("cid"):
                st.markdown("### 其他数据")
                st.page_link(f"https://pubchem.ncbi.nlm.nih.gov/compound/{data['cid']}",label="**访问PubChem**")
                st.image(f"https://pubchem.ncbi.nlm.nih.gov/image/imgsrv.fcgi?cid={data['cid']}&t=s","结构式")
                # st.button("访问PubChem",on_click=lambda :st.dire)
            # if data['melting_point']:
            #     st.metric("熔点 (°C)", data['melting_point'])
            # # 显示分子结构图
            # if data.get('inchi') or data.get('smiles'):
            #     st.markdown("分子结构图")
            #     mol_img = generate_molecule_image(inchi=data['inchi'], smiles=data['smiles'])
            #     if mol_img:
            #         st.image(mol_img, caption="分子键线式结构图", width=150)
            #     else:
            #         st.info("无法生成分子结构图")
        
        # 添加熔沸点信息的展开区域
        if data.get('melting_point_src') or data.get('boiling_point_src'):
            with st.expander("熔沸点信息", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    if data.get('melting_point_src'):
                        st.markdown("### 熔点数据")
                        melting_data = data['melting_point_src']
                        if isinstance(melting_data, list):
                            for i, mp in enumerate(melting_data, 1):
                                st.write(f"{i}. {mp}")
                        else:
                            st.write(melting_data)
                with col2:
                    if data.get('boiling_point_src'):
                        st.markdown("### 沸点数据")
                        boiling_data = data['boiling_point_src']
                        if isinstance(boiling_data, list):
                            for i, bp in enumerate(boiling_data, 1):
                                st.write(f"{i}. {bp}")
                        else:
                            st.write(boiling_data)
        
        # 判断是否为液体
        melting_data = data['melting_point_src']
        if isinstance(melting_data, list) and len(melting_data) > 0:
            import re
            melting_point = re.search(r'\d*\.\d+', melting_data[0])
            if melting_point:
                melting_point = float(melting_point.group())
            is_liquid = is_liquid_at_room_temp(melting_point)
        else:
            is_liquid = False

        # 检测值变化并执行计算
        def handle_change(field_name, new_value, current_value):
            try:
                # 确保都转换为浮点数
                new_value = float(new_value) if new_value is not None else 0.0
                current_value = float(current_value) if current_value is not None else 0.0
                
                if abs(new_value - current_value) > 1e-6:  # 避免浮点数比较问题
                    # 同步计算 - 确保数据类型正确
                    try:
                        calc_data = {
                            'molecular_weight': float(data['molecular_weight']),
                            'density_select': float(st.session_state.get('density_select', 0)) if (show_density and st.session_state.get('density_select')) else None
                        }
                    except (ValueError, TypeError):
                        st.error("化合物数据格式错误，无法进行计算")
                        return
                    
                    mmol_calc = mass_calc = volume_calc = 0.0
                    
                    if field_name == 'mmol':
                        mmol_calc, mass_calc, volume_calc = sync_calculations(
                            calc_data, new_value, None, None, 'mmol'
                        )
                    elif field_name == 'mass':
                        mmol_calc, mass_calc, volume_calc = sync_calculations(
                            calc_data, None, new_value, None, 'mass'
                        )
                    elif field_name == 'volume':
                        mmol_calc, mass_calc, volume_calc = sync_calculations(
                            calc_data, None, None, new_value, 'volume'
                        )
                    elif field_name == 'density':
                        # 密度变化时，如果已有质量，重新计算体积；如果已有体积，重新计算质量
                        current_mass = st.session_state.mass_val
                        current_volume = st.session_state.volume_val
                        
                        if current_mass > 0:
                            # 根据质量重新计算体积
                            mmol_calc, mass_calc, volume_calc = sync_calculations(
                                calc_data, None, current_mass, None, 'mass'
                            )
                        elif current_volume > 0:
                            # 根据体积重新计算质量
                            mmol_calc, mass_calc, volume_calc = sync_calculations(
                                calc_data, None, None, current_volume, 'volume'
                            )
                        else:
                            return  # 没有质量或体积数据，无需重新计算
                    
                    # 更新session state
                    st.session_state.mmol_val = float(mmol_calc) if mmol_calc is not None else 0.0
                    st.session_state.mass_val = float(mass_calc) if mass_calc is not None else 0.0
                    st.session_state.volume_val = float(volume_calc) if volume_calc is not None else 0.0
                    st.session_state.last_changed = field_name
                    
                    # 强制刷新页面以更新输入框的值
                    if field_name != 'density':  # 密度变化时不需要rerun，因为已经在密度输入处理中rerun了
                        st.rerun()
            except (ValueError, TypeError) as e:
                st.error(f"数值转换错误: {str(e)}")
                return
        
        # 密度显示选项
        show_density = False
        if data['density_src']:
            if is_liquid:
                show_density = st.checkbox("显示密度信息", value=True)
            else:
                show_density = st.checkbox("显示密度信息", value=False)
            
            if show_density:
                import re
                
                # 初始化密度值在session state中
                if 'density_select' not in st.session_state:
                    st.session_state.density_select = None
                if 'density_input_value' not in st.session_state:
                    st.session_state.density_input_value = 0.0
                
                density_data = data['density_src']
                # print(density_data)
                
                # 如果密度是列表且长度>1，让用户选择
                if isinstance(density_data, list) and len(density_data) > 1:
                    st.markdown("**选择密度数据：**")
                    
                    # 为每个密度选项提取数值并显示
                    density_options = []
                    density_values = []
                    
                    for i, density_str in enumerate(density_data):
                        # 使用正则表达式提取密度数值
                        match = re.search(r'\d*\.\d+', str(density_str))
                        if match:
                            extracted_value = float(match.group())
                            density_options.append(f"{extracted_value:.3f}: {density_str}")
                            density_values.append(extracted_value)
                        else:
                            density_options.append(f"0.000: {density_str} (无法提取数值)")
                            density_values.append(None)
                    
                    # 用户选择密度
                    selected_index = st.selectbox(
                        "选择要使用的密度数据:",
                        range(len(density_options)),
                        format_func=lambda x: density_options[x],
                        key="density_selector"
                    )
                    
                    # 获取选中的密度值
                    if density_values[selected_index] is not None:
                        selected_density_value = density_values[selected_index]
                        st.session_state.density_select = selected_density_value
                        
                        # 显示并允许用户修改密度值
                        st.markdown("**密度值 (可修改)：**")
                        new_density = st.number_input(
                            "密度 (g/mL)",
                            min_value=0.0,
                            value=float(st.session_state.density_select),
                            step=0.001,
                            format="%.3f",
                            key="density_input",
                            help="选择的密度值，可以手动修改"
                        )
                        
                        # 检测密度值变化
                        if abs(new_density - st.session_state.density_input_value) > 1e-6:
                            st.session_state.density_select = new_density
                            st.session_state.density_input_value = new_density
                            # 更新compound_data中的密度值用于计算
                            st.session_state.compound_data['density_select'] = new_density
                            handle_change('density', 1, 0)
                            st.rerun()
                    
                    else:
                        st.error("所选密度数据无法提取有效数值")
                
                # 如果密度是单个值或列表长度为1
                else:
                    try:
                        if isinstance(density_data, list):
                            density_str = str(density_data[0])
                        else:
                            density_str = str(density_data)
                        
                        # 提取密度数值
                        match = re.search(r'\d*\.\d+', density_str)
                        if match:
                            density_value = float(match.group())
                            st.session_state.density_select = density_value
                            
                            # 显示并允许用户修改密度值
                            st.markdown("**密度值 (可修改)：**")
                            new_density = st.number_input(
                                "密度 (g/mL)",
                                min_value=0.0,
                                value=float(st.session_state.density_select),
                                step=0.001,
                                format="%.3f",
                                key="density_input_single",
                                help="提取的密度值，可以手动修改"
                            )
                            
                            # 检测密度值变化
                            if abs(new_density - st.session_state.density_input_value) > 1e-6:
                                st.session_state.density_select = new_density
                                st.session_state.density_input_value = new_density
                                # 更新compound_data中的密度值用于计算
                                st.session_state.compound_data['density_select'] = new_density
                                handle_change('density', 1, 0)
                                st.rerun()
                        else:
                            st.error("无法从密度数据中提取有效数值")
                    except (ValueError, TypeError):
                        st.error("密度数据格式错误")
        
        st.markdown("---")
        
        # 计算器部分
        st.subheader("用量计算器")
        
        # 初始化值
        if 'mmol_val' not in st.session_state:
            st.session_state.mmol_val = 0.0
        if 'mass_val' not in st.session_state:
            st.session_state.mass_val = 0.0
        if 'volume_val' not in st.session_state:
            st.session_state.volume_val = 0.0
        if 'last_changed' not in st.session_state:
            st.session_state.last_changed = None
        
        # 创建响应式列布局
        density_select = st.session_state.get('density_select')
        if show_density and density_select is not None:
            calc_col1, calc_col2, calc_col3 = st.columns([1, 1, 1])
        else:
            calc_col1, calc_col2 = st.columns([1, 1])
            calc_col3 = None
        
        
        with calc_col1:
            st.markdown("**物质的量**")
            new_mmol = st.number_input(
                "用量 (mmol)",
                min_value=0.0,
                value=float(st.session_state.mmol_val),
                step=0.1,
                format="%.3f",
                key="mmol_input",
                help="输入或计算得到的物质的量，单位：毫摩尔"
            )
            
            
            # 检测mmol变化
            if st.session_state.last_changed != 'mmol':
                handle_change('mmol', new_mmol, st.session_state.mmol_val)
        
        with calc_col2:
            st.markdown("**质量**")
            new_mass = st.number_input(
                "质量 (g)",
                min_value=0.0,
                value=float(st.session_state.mass_val),
                step=0.001,
                format="%.3f",
                key="mass_input",
                help="输入或计算得到的质量，单位：克"
            )
            
            # 检测mass变化
            if st.session_state.last_changed != 'mass':
                handle_change('mass', new_mass, st.session_state.mass_val)
        
        if calc_col3 is not None:
            with calc_col3:
                st.markdown("**体积**")
                new_volume = st.number_input(
                    "体积 (mL)",
                    min_value=0.0,
                    value=float(st.session_state.volume_val),
                    step=0.01,
                    format="%.3f",
                    key="volume_input",
                    help="输入或计算得到的体积，单位：毫升"
                )
                
                # 检测volume变化
                if st.session_state.last_changed != 'volume':
                    handle_change('volume', new_volume, st.session_state.volume_val)
        
        # 重置last_changed状态
        st.session_state.last_changed = None
        

        # 清零按钮
        if st.button("清零所有数值", type="secondary"):
            st.session_state.mmol_val = 0.0
            st.session_state.mass_val = 0.0
            st.session_state.volume_val = 0.0
            st.session_state.last_changed = None
            st.rerun()
            st.session_state.mmol_val = 0.0
            st.session_state.mass_val = 0.0
            st.session_state.volume_val = 0.0
            st.rerun()
    
    else:
        st.info("👆 请在左侧输入要查询的化学物质")
