import streamlit as st
from streamlit_tags import st_tags

st.sidebar.markdown("# Compute index of an existing product")
st.sidebar.selectbox("Select product", ["Product 1", "Product 2"])

with st.sidebar.container():
    st.markdown("# Create a new product")
    st.text_input("Product name")
    st_tags(
        label="Composition (Material:Country:Weight)",
        suggestions=["leather:argentina:100g", "brass:peru:10g", "plastic:china:20g"],
    )
    st.file_uploader("Upload product picture")
    st.button("Add product")

st.markdown("# Compute the cost to society of a product")
st.markdown("Product's cost to society: XX$")
# Add : picture of the product (if available)
# Add : histogram of index score
# Add : "this product is among the top-1% of sustainable products" (compute quantile)
