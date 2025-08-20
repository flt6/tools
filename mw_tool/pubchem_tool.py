import molmass
import streamlit as st
import pubchempy as pcp
import re
from typing import Optional, Dict, List, cast
import requests
import pandas as pd
import numpy as np
import traceback

class PubChemCompound:
    def __init__(self, 
                 compound: Optional[pcp.Compound]=None, 
                 extra: Optional[Dict[str, Optional[List[str]]]] = None,
                 **kwargs
                 ):
        if compound:
            self.cid = compound.cid
            self.name = compound.iupac_name
            self.formula = compound.molecular_formula
            self.smiles = compound.isomeric_smiles
            self.exact_mass = float(compound.exact_mass) if compound.exact_mass else None
        else:
            self.cid = None
            self.name = None
            self.formula = None
            self.smiles = None
            self.exact_mass = None
        if extra:
            self.density = extra.get("density")
            self.melting_point = extra.get("melting_point")
            self.boiling_point = extra.get("boiling_point")
        else:
            self.density = None
            self.melting_point = None
            self.boiling_point = None
        self.__dict__.update(kwargs)  # 允许传入其他属性

def get_pubchem_properties(cid:str) -> Dict[str, Optional[List[str]]]:
    """从PubChem获取密度、熔点、沸点信息"""
    try:
        # 初始化返回数据
        properties:Dict[str, Optional[List[str]]] = {
            'density': None,
            'melting_point': None,
            'boiling_point': None
        }

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


def search_compound(query: str, search_type: str = "name"):
    """
    根据不同类型搜索化合物
    
    Args:
        query: 搜索词
        search_type: 搜索类型 ("name", "formula", "smiles")
    
    Returns:
        PubChem Compound对象或None
    """
    try:
        if search_type == "name":
            compounds = pcp.get_compounds(query, 'name')
        elif search_type == "formula":
            compounds = pcp.get_compounds(query, 'formula')
        elif search_type == "smiles":
            compounds = pcp.get_compounds(query, 'smiles')
        else:
            return None
            
        if compounds is not None and len(compounds) > 0:
            return compounds[0]  # 返回第一个匹配的化合物
        return None
    except Exception as e:
        st.error(f"搜索出错: {str(e)}")
        return None


def get_structure_image(cid: int, width: int = 300, height: int = 300):
    """
    获取化合物的2D结构图
    
    Args:
        cid: PubChem CID
        width: 图片宽度
        height: 图片高度
    
    Returns:
        url
    """
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/PNG?record_type=2d&image_size={width}x{height}"
    return url


def extract_density_value(density_text: str) -> Optional[float]:
    """
    从密度文本中提取数值
    
    Args:
        density_text: 密度描述文本
        
    Returns:
        提取的密度数值或None
    """
    # 使用正则表达式提取数字
    pattern = r'(\d*\.\d+|\d+\.\d*|\d+)'
    matches = re.findall(pattern, density_text)
    if matches:
        try:
            return float(matches[0])
        except ValueError:
            return None
    return None


def calculate_properties(molecular_weight: float, amount_mmol: Optional[float] = None, 
                        mass_g: Optional[float] = None, volume_ml: Optional[float] = None,
                        density: Optional[float] = None):
    """
    计算用量、质量、体积之间的关系
    
    Args:
        molecular_weight: 分子量 (g/mol)
        amount_mmol: 用量 (mmol)
        mass_g: 质量 (g)
        volume_ml: 体积 (mL)
        density: 密度 (g/mL)
        
    Returns:
        计算结果字典
    """
    result = {
        'amount_mmol': amount_mmol,
        'mass_g': mass_g,
        'volume_ml': volume_ml
    }
    
    # 如果有用量和分子量，计算质量
    if amount_mmol is not None and molecular_weight:
        result['mass_g'] = amount_mmol * molecular_weight / 1000
        
    # 如果有质量和分子量，计算用量
    if mass_g is not None and molecular_weight:
        result['amount_mmol'] = mass_g * 1000 / molecular_weight
        
    # 如果有质量和密度，计算体积
    if result['mass_g'] is not None and density is not None and density > 0:
        result['volume_ml'] = result['mass_g'] / density

    # 如果有体积和密度，计算质量
    if volume_ml is not None and density is not None and density > 0:
        result['mass_g'] = volume_ml * density
        result["amount_mmol"] = result['mass_g'] * 1000 / molecular_weight

    return result


def reaction_table_page():
    """反应表格页面"""
    st.header("反应表格")

    with st.expander("**使用说明**", expanded=False):
        st.markdown('''在下方的表格中，您可以输入反应数据，程序会尝试计算其余各项。当量为0时，该物质不参与当量计算。
### 立即计算

选中`立即计算`选项后，输入后立即尝试计算修改部分，您可以实时查看计算结果。但请注意，请勿同时修改多项内容。如果输入某项后计算未正确进行，这是潜在的缺陷，请反馈。

不保证在您主动修改计算结果后程序能正确处理（例如，程序算出质量后您主动修改），通常这会伴随着警告，但也有可能遗漏某些情况。

### 延迟计算

不选中`立即计算`后，在完成输入后，您可以点击“计算”按钮，程序会尝试计算所有可用的结果。

程序在计算时会检查是否有冗余数据，例如同时给定分子量、用量、质量，并拒绝在这种情况下计算。您可以选中`不使用检查`选项来禁用检查，但请保证数据自洽（即使得所有已知量之间的关系成立），否则会发生未定义行为。

如果计算后您想要修改或补充内容再次计算，请选中`不使用检查`选项。
''')
        with st.expander("关于未定义行为"):
            st.markdown('''程序内部计算顺序为
1. n -> mass
2. mass -> n
3. mass -> volumn
4. volumn -> mass
5. mass -> n
6. eqiv -> n
7. n -> mass
8. mass -> volumn

如果存在不自洽的数据，您可以通过上述内容预测程序行为。但这不应该在实际使用中依赖，因为在不同版本下实现可能发生变化。

''')

    # 初始化数据
    if 'reaction_data' not in st.session_state:
        df = pd.DataFrame([[None,None,None,None,None,None,None,None]],columns=[
                "物质",
                "分子量",
                "当量",
                "用量(mmol)",
                "质量(g)",
                "密度(g/mL)",
                "体积(mL)",
                "备注"
        ],dtype="float")
        df["物质"] = df["物质"].astype("string")
        df["备注"] = df["备注"].astype("string")
        st.session_state.reaction_data = df
        
    
    st.info(f"💡 当量为0时，该物质不参与当量计算。")
    use_on_change = st.checkbox("立即计算", value=True)
    if not use_on_change:
        st.checkbox("不使用检查", value=False,key="no_check",)
        st.button("计算",on_click=calc_reaction_data,type="primary")

    # 使用data_editor创建可编辑表格
    edited_data = st.data_editor(
        st.session_state.reaction_data,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "物质": st.column_config.TextColumn("物质", width="medium"),
            "分子量": st.column_config.NumberColumn(
                "分子量",
                format="%.4f",
                min_value=0.0,
                step=0.0001
            ),
            "当量": st.column_config.NumberColumn(
                "当量",
                format="%.2f",
                min_value=0.0,
                step=0.1,
                help="当量为0时不参与当量计算"
            ),
            "用量(mmol)": st.column_config.NumberColumn(
                "用量(mmol)",
                format="%.3f",
                min_value=0.0,
                step=0.001
            ),
            "质量(g)": st.column_config.NumberColumn(
                "质量(g)",
                format="%.6f",
                min_value=0.0,
                step=0.000001
            ),
            "密度(g/mL)": st.column_config.NumberColumn(
                "密度(g/mL)",
                format="%.3f",
                min_value=0.0,
                step=0.001
            ),
            "体积(mL)": st.column_config.NumberColumn(
                "体积(mL)",
                format="%.6f",
                min_value=0.0,
                step=0.000001
            ),
            "备注": st.column_config.TextColumn("备注", width="medium")
        },
        key="reaction_table",
        on_change=recalculate_reaction_data if use_on_change else None
    )

    if not use_on_change and isinstance(edited_data, pd.DataFrame):
        st.session_state.static_reaction_data = edited_data
        
    if st.session_state.get("reaction_table_refresh",0) == 2:
        st.warning("发生多个编辑，无法计算。")
        st.warning("由于计算失败，当前表格内容可能存在错误。")
        st.session_state.reaction_table_refresh = 0

    if st.session_state.get("reaction_table_refresh",0):
        st.session_state.reaction_data = edited_data
        st.session_state.reaction_table_refresh = 2
        st.rerun()

def get_mass_safe(chemical_name: str) -> float:
    try:
        mass = molmass.Formula(chemical_name).mass
        return mass
    except Exception as e:
        return float("nan")

def calc_reaction_data():
    try:
        df: pd.DataFrame = st.session_state.get("static_reaction_data",None)
        if not isinstance(df, pd.DataFrame):
            st.error("反应数据格式不正确")
            raise ValueError("reaction_data must be a DataFrame")
        df.columns = ["name","mw","eq","mol","mass","rho","vol","note"]

        # validate
        if not st.session_state.get("no_check",False):
            if any(df["mw"].notna() & df["mol"].notna() & df["mass"].notna()):
                st.error("分子量、物质的量和质量不能同时存在")
                raise ValueError
            if any((df["mass"].notna() | (df["mw"].notna() & df["mol"].notna())) & df["vol"].notna() & df["rho"].notna()):
                st.error("质量、体积和密度不能同时存在或可求")
                raise ValueError

        fil = df["mw"].isna() & df["name"].notna()
        df.loc[fil, "mw"] = df[fil]["name"].apply(get_mass_safe)

        # mol -> mass
        fil = df["mw"].notna() & df["mol"].notna()
        df.loc[fil, "mass"] = df[fil]["mol"] * df[f"{'mw'}"] / 1000.0  # mmol -> mol，再乘以 g/mol
        
        # mass -> mol
        fil = df["mw"].notna() & df["mass"].notna()
        df.loc[fil, "mol"] = df[fil]["mass"] * 1000.0 / df[f"{'mw'}"]  # g -> mol，再除以 g/mol
        
        # mass -> vol
        fil = df["mass"].notna() & df["rho"].notna()
        df.loc[fil, "vol"] = df[fil]["mass"] / df[fil]["rho"]  # g -> mL，再除以 g/mL

        # vol -> mass
        fil = df["vol"].notna() & df["rho"].notna()
        df.loc[fil, "mass"] = df[fil]["vol"] * df[fil]["rho"]  # mL -> g，再乘以 g/mL
        
        # mass -> mol
        fil = df["mw"].notna() & df["mass"].notna()
        df.loc[fil, "mol"] = df[fil]["mass"] * 1000.0 / df[f"{'mw'}"]  # g -> mol，再除以 g/mol
        
        eql = df[(df["eq"] > 0) & (df["mol"] > 0)]
        if not st.session_state.get("no_check",False):
            if eql.shape[0] > 1:
                st.error("对于当量存在物质，只允许一个物质设置用量、质量或体积")
                raise ValueError
        if eql.shape[0] == 0 and not df[(df["eq"] > 0)].empty:
            st.error("设置了当量，但是均没有设置用量、质量或体积")
            raise ValueError
        if not eql.empty:
            ref = eql.iloc[0]
            base = ref["mol"]/ref["eq"]
            eqfil = df["eq"] > 0
            df.loc[eqfil, "mol"] = df[eqfil]["eq"] * base
            
            fil = df["mw"].notna() & eqfil
            df.loc[fil, "mass"] = df[fil]["mol"] * df[f"{'mw'}"] / 1000.0  # mmol -> mol，再乘以 g/mol
            
            fil = df["rho"].notna() & df["mass"].notna() & eqfil
            df.loc[fil, "vol"] = df[fil]["mass"] / df[fil]["rho"]  # g -> mL，再除以 g/mL
        
        

    except Exception as e:
        # if "df" in locals():
        #     st.session_state.reaction_data = df
        st.error("计算过程中出错，表格可能有误")
        print("calc_reaction_data error:", traceback.format_exc())
        return
    finally:
        if "df" in locals():
            df.columns = [
                "物质",
                "分子量",
                "当量",
                "用量(mmol)",
                "质量(g)",
                "密度(g/mL)",
                "体积(mL)",
                "备注"
            ]
            st.session_state.reaction_data = df

def recalculate_reaction_data():
    """根据最近一次编辑的行及当量，推算其他未编辑行的用量，并更新质量/体积。"""
    try:
        edits = st.session_state.get("reaction_table")
        df = st.session_state.get("reaction_data")

        # 基本校验
        if df is None or not isinstance(df, pd.DataFrame):
            return

        # 仅当从 data_editor 拿到变更字典时才处理
        if not isinstance(edits, dict):
            return
        
         # 处理新增/删除行（若有）
        for new_row in edits.get("added_rows", []) or []:
            # 对象列名对齐现有表头
            if isinstance(new_row, dict):
                to_add = {col: new_row.get(col, None) for col in df.columns}
                df = pd.concat([df, pd.DataFrame([to_add])], ignore_index=True)
        for del_idx in edits.get("deleted_rows", []) or []:
            try:
                df.drop(index=int(del_idx), inplace=True)
            except Exception:
                pass
        if (edits.get("deleted_rows") or []):
            df.reset_index(drop=True, inplace=True)


        edited_rows = edits.get("edited_rows", {}) or {}
        if not edited_rows:
            st.session_state.reaction_data = df
            print("No edited rows found, skipping recalculation.")
            return
        if len(edited_rows) > 1:
            st.session_state.reaction_table_refresh = 1
            return

        # 将编辑内容先写回到 DataFrame，记录“最后编辑的行”作为基准行
        edited_indices = []
        edited = {}
        for idx_str, changes in edited_rows.items():
            try:
                i = int(idx_str)
            except Exception:
                # 有些情况下索引就是 int
                i = idx_str
            edited_indices.append(i)
            for col, val in changes.items():
                if col in df.columns:
                    df.loc[i, col] = val
                    edited[col] = val
                    # if col in ["用量(mmol)","质量(g)","体积(mL)","密度(g/mL)","当量"]:
                    if col == "当量":
                        if val != 0:
                            example = df[(df["当量"] > 0) & (df["用量(mmol)"] > 0)]
                            if example.size > 0:
                                j=0
                                tmp = example.iloc[j]
                                while tmp.name == i:
                                    j+=1
                                    tmp = example.iloc[j]
                                sing = tmp['用量(mmol)']/tmp["当量"]
                                edited["用量(mmol)"] = sing * edited["当量"]

        basis_idx = edited_indices[-1]  # 以最后一条编辑为本次基准
        

        # 数值清洗工具
        def _to_float(x):
            try:
                if x is None:
                    return None
                # 处理 NaN/空串
                try:
                    import pandas as _pd
                    if _pd.isna(x):
                        return None
                except Exception:
                    pass
                s = str(x).strip()
                if s == "":
                    return None
                return float(s)
            except Exception:
                return None

        # 基准行的自洽计算（用量/质量/体积）
            
        brow = df.loc[basis_idx]

        if "物质" in edited.keys() and pd.isna(brow["分子量"]) and "分子量" not in edited.keys():
            df.loc[basis_idx, "分子量"] = get_mass_safe(edited["物质"])

        if "密度(g/mL)" in edited.keys():
            if  _to_float(brow.get("体积(mL)")) is None and "质量(g)" in brow.keys():
                edited["质量(g)"] =  _to_float(brow.get("质量(g)"))
            elif _to_float(brow.get("质量(g)")) is None and "体积(mL)" in brow.keys():
                edited["体积(mL)"] =  _to_float(brow.get("体积(mL)"))
            else:
                print(brow)
                st.error("当质量和体积同时存在时，修改密度为未定义行为。")
                raise ValueError
        
        if "分子量" in edited.keys():
            if all(pd.notna(brow[["质量(g)","用量(mmol)"]])):
                st.error("当质量和用量同时存在时，修改分子量为未定义行为。")
                raise ValueError
            if pd.notna(brow.get("质量(g)")):
                edited["质量(g)"] = _to_float(brow.get("质量(g)"))
            if pd.notna(brow.get("用量(mmol)")):
                edited["用量(mmol)"] = _to_float(brow.get("用量(mmol)"))
            

        b_mw = _to_float(brow.get("分子量"))
        b_density = edited.get("密度(g/mL)", _to_float(brow.get("密度(g/mL)")))
        b_amount = edited.get("用量(mmol)", None)
        b_mass = edited.get("质量(g)", None)
        b_volume = edited.get("体积(mL)", None)
        b_eq = _to_float(brow.get("当量"))

        props = calculate_properties(
            molecular_weight=b_mw if b_mw else 0,
            amount_mmol=b_amount,
            mass_g=b_mass,
            volume_ml=b_volume,
            density=b_density,
        )

        _v = props.get("amount_mmol")
        if isinstance(_v, (int, float)):
            df.at[basis_idx, "用量(mmol)"] = round(float(_v), 6)
        _v = props.get("mass_g")
        if isinstance(_v, (int, float)):
            df.at[basis_idx, "质量(g)"] = round(float(_v), 6)
        _v = props.get("volume_ml")
        if isinstance(_v, (int, float)):
            df.at[basis_idx, "体积(mL)"] = round(float(_v), 6)


        # 基准行当量为 0 或不可用，则不进行当量联动计算
        if not (b_eq and b_eq > 0):
            st.session_state.reaction_data = df
            return

        b_amount_final = _to_float(df.at[basis_idx, "用量(mmol)"])
        if b_amount_final is None:
            st.session_state.reaction_data = df
            return

        base_per_eq = b_amount_final / b_eq
        

        # 按当量推算其他“未编辑行”的用量，并据此计算质量/体积
        for j in range(len(df)):
            if j == basis_idx:
                continue
            if j in edited_indices:
                # 本次被用户直接修改的行不改动
                continue
            eq_j = _to_float(df.at[j, "当量"]) if "当量" in df.columns else None
            if not (eq_j and eq_j > 0):
                continue

            amt_j = base_per_eq * eq_j
            df.at[j, "用量(mmol)"] = round(amt_j, 6)

            mw_j = _to_float(df.at[j, "分子量"]) if "分子量" in df.columns else None
            if mw_j:
                mass_j = amt_j * mw_j / 1000.0  # mmol -> mol，再乘以 g/mol
                df.at[j, "质量(g)"] = round(mass_j, 6)

                dens_j = _to_float(df.at[j, "密度(g/mL)"]) if "密度(g/mL)" in df.columns else None
                if dens_j and dens_j > 0:
                    vol_j = mass_j / dens_j
                    df.at[j, "体积(mL)"] = round(vol_j, 6)
        # 持久化
        st.session_state.reaction_data = df
    except Exception as e:
        # raise e
        st.warning("重新计算反应数据时出错，表格可能有误")
        print("recalculate_reaction_data error:", e)

def add_compound_to_reaction(compound:PubChemCompound):
    """将化合物添加到反应中"""
    d = {
        "物质":compound.formula,
        "分子量":compound.exact_mass,
        "当量":None,
        "用量(mmol)":None,
        "质量(g)":None,
        "密度(g/mL)":st.session_state.get("custom_density",None),
        "体积(mL)":None,
        "备注":compound.name
    }
    st.session_state.reaction_data = pd.concat([st.session_state.reaction_data, pd.DataFrame([d])], ignore_index=True)
    st.success("化合物已添加到反应中")

def compound_search_page():
    """化合物搜索页面"""
    # 输入区域


    with st.expander("**使用说明**"):
        st.markdown("""
        1. **选择搜索类型**: 
           - 名称: 输入化合物的常用名称或IUPAC名称
           - 化学式: 输入分子式 (如 C2H6O)
           - SMILES: 输入SMILES字符串 (如 CCO)
        
        2. **输入查询条件**: 在输入框中输入相应的查询词
        
        3. **点击搜索**: 系统将从PubChem数据库中查询匹配的化合物
        
        4. **查看结果**: 
           - 基本信息包括名称、化学式、分子量和2D结构图
           - 密度和熔沸点信息可在展开区域查看
           - 计算器可帮助您计算用量、质量和体积的关系
        
        ### 示例查询
        - **名称**: ethanol, water, glucose
        - **化学式**: C2H6O, H2O, C6H12O6
        - **SMILES**: CCO, O, C(C1C(C(C(C(O1)O)O)O)O)O
        """)
        
    st.header("查询条件")
    col1, col2 = st.columns([1, 2])
    
    with col1:
        # 选择搜索类型
        mp = {"name": "名称", "formula": "化学式", "smiles": "SMILES","calc":"化学式（本地计算）"}
        search_type = st.selectbox(
            "选择搜索类型",
            mp.keys(),
            format_func=lambda x: mp[x]
        )
    
    with col2:
        # 输入搜索词
        query = st.text_input(
            f"输入{mp[search_type]}",
            placeholder="例如: ethanol, C2H6O, CCO"
        )
    
    search_button = st.button("🔍 搜索", type="primary")
    
    # 主要内容区域
    if search_button and query:
        if search_type == "calc":
            try:
                mass = molmass.Formula(query).mass
                st.session_state.compound = PubChemCompound(exact_mass=mass, formula=query)
            except Exception as e:
                st.error(f"计算分子量时出错: {e}")
        else:
            with st.spinner("正在搜索..."):
                _compound = search_compound(query, search_type)
            
            print(_compound,search_type)

            if _compound is not None:
                st.info("找到匹配的化合物，正在获取详细信息...")
                # 在session_state中存储化合物信息
                additional_props = get_pubchem_properties(str(_compound.cid))
                st.session_state.compound = PubChemCompound(cast(pcp.Compound, _compound), additional_props)

            elif search_type == "formula":
                try:
                    mass = molmass.Formula(query).mass
                    st.session_state.compound = PubChemCompound(exact_mass=mass, formula=query)
                    print(mass)
                    st.info("根据化学式计算得到分子量")
                except Exception as e:
                    st.error(f"计算分子量时出错: {e}")
            else:
                st.error("未找到匹配的化合物，请检查输入并重试。")
    
    # 如果session_state中有化合物信息，显示结果
    if hasattr(st.session_state, 'compound') and st.session_state.compound:
        compound = st.session_state.compound
        st.button("添加到反应", on_click=add_compound_to_reaction, args=(compound,))
        
        # 基本信息展示
        col1, col2 = st.columns(2)
        
        with col1:
            st.header("📊 基本信息")
            
            st.metric("物质名称", compound.name or "未知")
            st.metric("化学式", compound.formula or "未知")
            st.metric("分子量", f"{compound.exact_mass:.4f} g/mol" if compound.exact_mass else "未知")
            if compound.cid:
                st.markdown(f"[**访问PubChem页面**](https://pubchem.ncbi.nlm.nih.gov/compound/{compound.cid})")
            # 创建信息表格
            

            # st.table(info_data)

        with col2:
            st.header("🖼️ 2D结构图")
            if hasattr(compound, 'cid') and compound.cid:
                structure_img = get_structure_image(compound.cid)
                if structure_img:
                    st.image(structure_img, caption=f"CID: {compound.cid}")
                else:
                    st.warning("无法获取结构图")
            else:
                st.warning("无CID信息，无法获取结构图")
        
        # 扩展信息
        st.markdown("---")
        
        # 密度信息
        if compound.density:
            with st.expander("📏 密度信息", expanded=False):
                st.subheader("可用密度数据:")
                
                # 初始化session_state中的密度选择
                if 'selected_density_idx' not in st.session_state:
                    st.session_state.selected_density_idx = 0
                if 'custom_density' not in st.session_state:
                    st.session_state.custom_density = None
                
                # 显示密度选项
                density_options = compound.density
                selected_idx = st.radio(
                    "选择要使用的密度数据:",
                    range(len(density_options)),
                    format_func=lambda x: density_options[x],
                    key="density_radio",
                    index=st.session_state.selected_density_idx
                )
                
                # 提取密度数值
                selected_density_text = density_options[selected_idx]
                extracted_density = extract_density_value(selected_density_text)
                
                custom_density = st.number_input(
                    "密度值 (g/mL):",
                    value=extracted_density if extracted_density else 1.0,
                    # min_value=0.001,
                    # max_value=50.0,
                    step=0.001,
                    format="%.3f",
                    key="custom_density_input"
                )
                st.session_state.custom_density = custom_density
                st.session_state.selected_density_idx = selected_idx
        else:
            st.session_state.custom_density = None
        
        # 熔沸点信息
        if compound.melting_point or compound.boiling_point:
            with st.expander("🌡️ 熔沸点信息", expanded=False):
                col1, col2 = st.columns(2)

                with col1:
                    st.subheader("熔点")
                if compound.melting_point:
                    for mp in compound.melting_point:
                        st.write(f"• {mp}")
                else:
                    st.warning("未找到熔点数据")
            
            with col2:
                st.subheader("沸点")
                if compound.boiling_point:
                    for bp in compound.boiling_point:
                        st.write(f"• {bp}")
                else:
                    st.warning("未找到沸点数据")
        
        # 计算器
        st.markdown("---")
        st.header("🧮 用量计算器")
        
        if compound.exact_mass:
            # 初始化session_state中的计算器数值
            if 'calc_amount' not in st.session_state:
                st.session_state.calc_amount = None
            if 'calc_mass' not in st.session_state:
                st.session_state.calc_mass = None
            if 'calc_volume' not in st.session_state:
                st.session_state.calc_volume = None
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                amount_mmol = st.number_input(
                    "用量 (mmol)",
                    min_value=0.0,
                    value=st.session_state.calc_amount if st.session_state.calc_amount else 0.0,
                    step=0.1,
                    format="%.3f",
                    key="amount_input",
                )
            
            with col2:
                mass_g = st.number_input(
                    "质量 (g)",
                    min_value=0.0,
                    value=st.session_state.calc_mass if st.session_state.calc_mass else 0.0,
                    step=0.001,
                    format="%.6f",
                    key="mass_input"
                )
            
            with col3:
                # 只有在有密度数据时才显示体积输入
                if st.session_state.get('custom_density'):
                    volume_ml = st.number_input(
                        "体积 (mL)",
                        min_value=0.0,
                        value=st.session_state.calc_volume if st.session_state.calc_volume else 0.0,
                        step=0.001,
                        format="%.6f",
                        key="volume_input"
                    )
                else:
                    volume_ml = None
            
            # 检测哪个值发生了变化并重新计算
            current_values = {
                'amount': amount_mmol if amount_mmol!=st.session_state.calc_amount else None,
                'mass': mass_g if mass_g !=  st.session_state.calc_mass else None,
                'volume': volume_ml if volume_ml and volume_ml != st.session_state.calc_volume else None
            }
            
            # 执行计算
            if any(current_values.values()):
                density = st.session_state.get('custom_density')
                results = calculate_properties(
                    molecular_weight=compound.exact_mass,
                    amount_mmol=current_values['amount'],
                    mass_g=current_values['mass'],
                    volume_ml=current_values['volume'],
                    density=density
                )
                
                # 更新session_state
                st.session_state.calc_amount = results['amount_mmol']
                st.session_state.calc_mass = results['mass_g']
                st.session_state.calc_volume = results['volume_ml']
                print(f"计算结果: {results}")
                st.rerun()
        else:
            st.warning("无分子量数据，无法进行计算")

    


def main():
    st.set_page_config(
        page_title="有机合成用量计算工具",
        page_icon="🧪",
        layout="wide"
    )
    
    # 侧边栏导航
    with st.sidebar:
        page = st.radio(
            "选择功能页面",
            ["化合物查询", "反应表格"],
            index=0
        )
    
    # 根据选择显示不同页面
    if page == "化合物查询":
        compound_search_page()
    elif page == "反应表格":
        reaction_table_page()


if __name__ == "__main__":
    main()
