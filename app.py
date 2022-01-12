import streamlit as st
import ast

from streamlit_tags import st_tags
from functions import *


df_ekpi_perkg, df_material_ekpi_agg, material_suggestions = load_df()
product_df, product_list = load_product_df()

with st.sidebar:
    st.markdown("### Compute the environmental cost of a product")
    current_product_name = st.selectbox("Select product", product_list)
    st.button("Create new product", on_click=add_product)

current_product = product_df[product_df["product_name"] == current_product_name]
current_product = current_product.iloc[0]

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
    st.image(
        load_image(current_product["img_path"]),
    )
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
    env_cost, env_group_to_impact = compute_environmental_cost(
        composition, df_ekpi_perkg, df_material_ekpi_agg
    )
    st.markdown(
        f"""## Environmental cost: \
        {env_cost:.0f}$\
        \nAir emissions: {env_group_to_impact["Air emissions"]*1000:.0f} g\
        \nGHGs: {env_group_to_impact["GHGs"]:.2f} kg CO2e\
        \nLand use: {env_group_to_impact["Land use"]*10000:.0f} m²\
        \nWaste: {env_group_to_impact["Waste"]*1000:.0f} g\
        \nWater consumption: {env_group_to_impact["Water consumption"]*1000:.0f} L\
        \nWater pollution: {env_group_to_impact["Water pollution"]*1000:.0f} L\
        """
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
