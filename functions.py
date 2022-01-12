import streamlit as st
import pandas as pd
import re

from loguru import logger
from typing import Dict, Tuple, List
from collections import defaultdict
from PIL import Image


@st.cache()
def load_df() -> Tuple[pd.DataFrame, pd.DataFrame, List]:
    # Load df impact by environmental area and raw material
    df_material_ekpi = pd.read_csv("data/raw-material-intensities-2020.csv", sep=";")
    df_material_ekpi_agg = (
        df_material_ekpi.groupby(["Material Group", "Environmentalimpactgroup"])
        .sum()
        .reset_index()
    )
    df_material_ekpi_agg.rename(
        {
            "Material Group": "material_group",
            "Environmentalimpactgroup": "env_impact_group",
        },
        axis=1,
        inplace=True,
    )
    df_material_agg_mat = (
        df_material_ekpi_agg.groupby("material_group")
        .sum()
        .reset_index()[["material_group", "Valued_Ekpi_intensity"]]
        .rename({"Valued_Ekpi_intensity": "underestimated_value"}, axis=1)
    )
    # Load raw material quantity
    df_ekpi_perkg = pd.read_csv("data/material-quantity-in-2019-and-2020.csv", sep=";")
    logger.debug(df_ekpi_perkg.columns)
    df_ekpi_perkg.rename(
        {"Material group (exclude unspecified)": "material_group"}, axis=1, inplace=True
    )
    df_ekpi_perkg["value_per_kg"] = (
        df_ekpi_perkg["Valued result"] / df_ekpi_perkg["Quantity_kg"]
    )
    df_ekpi_perkg["material_slug"] = (
        df_ekpi_perkg["material_group"].str.lower().str.replace(" ", "_")
    )
    # Join
    df_material_ekpi_agg = df_material_ekpi_agg.merge(
        df_ekpi_perkg, on="material_group"
    ).merge(df_material_agg_mat, on="material_group")
    df_material_ekpi_agg["underestimate_coeff"] = (
        df_material_ekpi_agg["Valued result"]
        / df_material_ekpi_agg["underestimated_value"]
    )
    df_material_ekpi_agg["env_impact_per_kg"] = (
        df_material_ekpi_agg["Material_ePKI_intensity"]
        / df_material_ekpi_agg["Quantity_kg"]
        * df_material_ekpi_agg["underestimate_coeff"]
    )
    df_material_ekpi_agg
    # Create raw material suggestion
    material_suggestions = (
        df_ekpi_perkg["material_slug"].apply(lambda x: x + ":100g").to_list()
    )
    return df_ekpi_perkg, df_material_ekpi_agg, material_suggestions


def load_product_df():
    product_df = pd.read_csv("data/products.csv")
    product_df = product_df[["id", "product_name", "composition", "img_path"]]
    product_df["id"] = product_df["id"].astype(int)
    product_list = product_df["product_name"].to_list()
    return product_df, product_list


@st.cache()
def compute_environmental_cost(
    composition: List[str], df_ekpi_perkg: pd.DataFrame, df_material_ekpi: pd.DataFrame
) -> Tuple[int, Dict[str, float]]:
    if not composition:
        return 0
    processed_comp = defaultdict(list)
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
    logger.debug(processed_comp)
    # Environmental cost
    processed_comp_env_cost = processed_comp.merge(
        df_ekpi_perkg,
        left_on="material_name",
        right_on="material_slug",
    )
    processed_comp_env_cost["value_for_material"] = (
        processed_comp_env_cost["weight"] * processed_comp_env_cost["value_per_kg"]
    )
    environmental_cost = processed_comp_env_cost["value_for_material"].sum()
    # Multiply by 100 (constant)
    environmental_cost = environmental_cost * 100
    # Cost by environmental impact
    processed_comp_env_impact = processed_comp.merge(
        df_material_ekpi, left_on="material_name", right_on="material_slug"
    )
    processed_comp_env_impact["env_impact_for_material"] = (
        processed_comp_env_impact["weight"]
        * processed_comp_env_impact["env_impact_per_kg"]
    )
    processed_comp_env_impact = (
        processed_comp_env_impact.groupby("env_impact_group").sum().reset_index()
    )
    env_group_to_impact = {
        material: env_impact
        for (material, env_impact) in zip(
            processed_comp_env_impact["env_impact_group"],
            processed_comp_env_impact["env_impact_for_material"],
        )
    }
    return environmental_cost, env_group_to_impact


def add_product():
    product_df = pd.read_csv("data/products.csv")
    max_id = product_df["id"].astype(int).max() + 1
    test_df = pd.DataFrame(
        {
            "id": [max_id],
            "product_name": [f"Product #{max_id}"],
            "composition": [None],
            "img_path": ["data/img/nico1.png"],
        }
    )
    logger.info(f"Add product: {test_df}")
    product_df = product_df.append(test_df, ignore_index=True)
    product_df["id"] = product_df["id"].astype(int)
    product_df.to_csv("data/products.csv", index=False)


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
    if uploadedfile:
        img_path = f"data/img/{uploadedfile.name}"
        with open(img_path, "wb") as f:
            f.write(uploadedfile.getbuffer())
    if pd.isna(composition).any():
        composition = []
    # Update
    product_df.loc[product_df["id"] == product_id, "product_name"] = product_name
    product_df.loc[product_df["id"] == product_id, "composition"] = str(composition)
    product_df.loc[product_df["id"] == product_id, "img_path"] = img_path
    product_df["id"] = product_df["id"].astype(int)
    product_df.to_csv("data/products.csv", index=False)
    return product_df
