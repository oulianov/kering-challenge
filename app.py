from numpy.core.fromnumeric import prod, product
import streamlit as st
import pandas as pd
import numpy as np
import re
import ast
from loguru import logger
from streamlit_tags import st_tags
from typing import Union, List, Dict
from collections import defaultdict
from PIL import Image


@st.cache()
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


def load_product_df():
    product_df = pd.read_csv("data/products.csv")
    product_df = product_df[["id", "product_name", "composition", "img_path"]]
    product_df["id"] = product_df["id"].astype(int)
    product_list = product_df["product_name"].to_list()
    logger.info(product_df)
    return product_df, product_list


product_df, product_list = load_product_df()
st.sidebar.markdown("### Compute the environmental cost of a product")
current_product_name = st.sidebar.selectbox("Select product", product_list)


def add_product():
    product_df = pd.read_csv("data/products.csv")
    max_id = product_df["id"].astype(int).max() + 1
    logger.debug(f"max_id: {max_id}")
    test_df = pd.DataFrame(
        {
            "id": [max_id],
            "product_name": [f"Product #{max_id}"],
            "composition": [None],
            "img_path": ["data/img/placeholder.png"],
        }
    )
    logger.info(f"Add product: {test_df}")
    logger.debug(f"product_df columns: {product_df.columns}")
    logger.debug(f"test_df columns: {test_df.columns}")
    product_df = product_df.append(test_df, ignore_index=True)
    product_df["id"] = product_df["id"].astype(int)
    product_df.to_csv("data/products.csv", index=False)


st.sidebar.button("Create new product", on_click=add_product)


@st.cache()
def load_image(image_file):
    img = Image.open(image_file)
    return img


def save_product(
    product_id: int,
    product_name: str,
    composition: List[str],
    img_path,
    uploadedfile,
):
    product_df = pd.read_csv("data/products.csv")
    logger.debug(f"product_id: {product_id}")
    if uploadedfile:
        img_path = f"data/img/{uploadedfile.name}"
        with open(img_path, "wb") as f:
            f.write(uploadedfile.getbuffer())
    if pd.isna(composition).any():
        composition = []
    logger.info(f"before: {product_df[product_df['id'] == product_id]}")
    product_df.loc[product_df["id"] == product_id, "product_name"] = product_name
    product_df.loc[product_df["id"] == product_id, "composition"] = str(composition)
    product_df.loc[product_df["id"] == product_id, "img_path"] = img_path

    logger.info(f"after: {product_df[product_df['id'] == product_id]}")
    product_df["id"] = product_df["id"].astype(int)
    product_df.to_csv("data/products.csv", index=False)
    return product_df


current_product = product_df[product_df["product_name"] == current_product_name]
logger.info(current_product)
current_product = current_product.iloc[0]
logger.debug(f"current_product: {current_product}")

if isinstance(current_product["composition"], str):
    if current_product["composition"] != "":
        current_product["composition"] = ast.literal_eval(
            current_product["composition"]
        )
else:
    current_product["composition"] = []
if current_product["composition"] == pd.NA:
    current_product["composition"] = []
col1, col2 = st.columns(2)
with col1:
    product_name = st.text_input("Product name", value=current_product["product_name"])
    st.image(load_image(current_product["img_path"]), width=250)
    uploadedfile = st.file_uploader("Upload product picture", type=["jpg", "png"])
with col2:
    composition = st_tags(
        label="Composition (Material:Weight)",
        value=current_product["composition"],
        suggestions=material_suggestions,
    )
    st.markdown(
        f"Allowed materials: `{', '.join(df_ekpi_perkg['material_slug'].to_list())}`"
    )
    st.markdown(
        f"""## Environmental cost: \
        {compute_environmental_cost(composition, df_ekpi_perkg)}$"""
    )

    if st.button("Save changes"):
        save_product(
            current_product["id"],
            product_name,
            composition,
            current_product["img_path"],
            uploadedfile,
        )

# Add : picture of the product (if available)
# Add : histogram of index score
# Add : "this product is among the top-1% of sustainable products" (compute quantile)
