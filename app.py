import streamlit as st
import pandas as pd
import re
import ast
from loguru import logger
from streamlit_tags import st_tags
from typing import Union, List, Dict
from collections import defaultdict
from PIL import Image


@st.cache
def load_df() -> Union[pd.DataFrame, List]:
    df_ekpi_perkg = pd.read_csv("data/material-quantity-in-2019-and-2020.csv", sep=";")
    df_ekpi_perkg["value_per_kg"] = (
        df_ekpi_perkg["Valued result"] / df_ekpi_perkg["Quantity_kg"]
    )
    df_ekpi_perkg["material_slug"] = (
        df_ekpi_perkg["Material group (exclude unspecified)"]
        .str.lower()
        .str.replace(" ", "_")
    )
    material_suggestions = (
        df_ekpi_perkg["material_slug"].apply(lambda x: x + ":100g").to_list()
    )
    return df_ekpi_perkg, material_suggestions


def compute_environmental_cost(composition: List[str], df_ekpi_perkg: pd.DataFrame):
    if not composition:
        return 0
    processed_comp = defaultdict(list)
    logger.info(composition)
    for material in composition:
        m = re.search("^(.*)\:([0-9]*)([A-z]*)", material)
        if m:
            material_name, weight, unit = m.group(1), m.group(2), m.group(3)
            if unit not in ["kg", "g"]:
                logger.warning(f"Unknown unit: {unit} (accepted units: g, kg)")
                continue
            if material_name not in df_ekpi_perkg["material_slug"].to_list():
                logger.warning(
                    f"Unknown material: {material_name} (accepted materials: {df_ekpi_perkg['material_slug'].to_list()})"
                )
                continue
            weight = float(weight)
            if unit == "g":
                weight /= 1000  # conversion to kg
            processed_comp["material_name"].append(material_name)
            processed_comp["weight"].append(weight)
        else:
            # Ignore
            logger.warning(f"Poorly formatted material: {material}")
            pass
    if not processed_comp:
        return 0
    processed_comp = pd.DataFrame(processed_comp)
    processed_comp = processed_comp.merge(
        df_ekpi_perkg,
        left_on="material_name",
        right_on="material_slug",
    )
    processed_comp["value_for_material"] = (
        processed_comp["weight"] * processed_comp["value_per_kg"]
    )
    environmental_cost = processed_comp["value_for_material"].sum()
    # Formating
    environmental_cost = round(environmental_cost, 2)
    return environmental_cost


df_ekpi_perkg, material_suggestions = load_df()

st.sidebar.markdown("# Compute environmental cost of an existing product")
try:
    product_df = pd.read_csv("data/products.csv")
    product_list = product_df["product_name"].to_list()
except:
    product_df = None
    product_list = []
current_product_name = st.sidebar.selectbox("Select product", product_list)
if type(product_df) != type(None):
    current_product = product_df[
        product_df["product_name"] == current_product_name
    ].iloc[0]
else:
    current_product = None


@st.cache
def load_image(image_file):
    img = Image.open(image_file)
    return img


def add_product(product_name: str, composition: List[str], uploadedfile):
    if uploadedfile:
        img_path = f"data/img/{uploadedfile.name}"
        with open(img_path, "wb") as f:
            f.write(uploadedfile.getbuffer())
    else:
        img_path = None
    new_product_line = pd.DataFrame(
        {
            "product_name": [product_name],
            "composition": [composition],
            "img_path": [img_path],
        }
    )
    try:
        df = pd.read_csv("data/products.csv")
        df = df.append(new_product_line)
    except:
        df = new_product_line
    df.to_csv("data/products.csv")


st.markdown("# Compute the product's environmental cost")
if type(current_product) != type(None):
    current_product["composition"] = ast.literal_eval(current_product["composition"])
    col1, col2 = st.columns(2)
    with col1:
        product_name = st.text_input(
            "Product name", value=current_product["product_name"]
        )
        st.image(load_image(current_product["img_path"]), width=250)
        uploadedfile = st.file_uploader("Upload product picture", type=["jpg", "png"])
    with col2:
        composition = st_tags(
            label="Composition (Material:Weight)",
            value=current_product["composition"],
            suggestions=material_suggestions,
        )
        st.markdown(
            f"""## Environmental cost: \
            {compute_environmental_cost(composition, df_ekpi_perkg)}$"""
        )

    # Add : picture of the product (if available)
    # Add : histogram of index score
    # Add : "this product is among the top-1% of sustainable products" (compute quantile)

st.sidebar.button(
    "Add product",
    on_click=add_product,
    kwargs={
        "product_name": product_name,
        "composition": composition,
        "uploadedfile": uploadedfile,
    },
)
