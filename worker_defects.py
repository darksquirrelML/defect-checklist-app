#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import streamlit as st
from supabase import create_client
from PIL import Image
import io
import time

# -----------------------------
# Supabase connection
# -----------------------------

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

bucket = "defect-photos"

# -----------------------------
# Page setup
# -----------------------------

st.set_page_config(
    page_title="Defect Checklist",
    page_icon="📋",
    layout="centered"
)

st.title("Syed Alwi Pumping Station")
st.subheader("Defect Checklist")

# -----------------------------
# Image compression
# -----------------------------

def compress_image(uploaded_file):

    image = Image.open(uploaded_file)
    image = image.convert("RGB")

    buffer = io.BytesIO()

    image.save(buffer, format="JPEG", quality=75, optimize=True)

    return buffer.getvalue()

# -----------------------------
# Detect services automatically
# -----------------------------

services = supabase.storage.from_(bucket).list()
service_names = [s["name"] for s in services]

service = st.selectbox(
    "Select Service",
    service_names
)

# -----------------------------
# Load BEFORE photos
# -----------------------------

with st.spinner("Loading defects..."):

    before_files = supabase.storage.from_(bucket).list(f"{service}/before/")
    before_files = sorted(before_files, key=lambda x: x["name"])

    after_files = supabase.storage.from_(bucket).list(f"{service}/after/")

# -----------------------------
# Build AFTER photo dictionary
# -----------------------------

after_dict = {}

for f in after_files:

    name = f["name"]

    if name.startswith("defect_"):

        parts = name.split("_")

        defect_num = parts[1]
        timestamp = int(parts[2].split(".")[0])

        if defect_num not in after_dict or timestamp > after_dict[defect_num]["timestamp"]:

            after_dict[defect_num] = {
                "name": name,
                "timestamp": timestamp
            }

# -----------------------------
# Pagination
# -----------------------------

items_per_page = 10
total_defects = len(before_files)
total_pages = (total_defects - 1) // items_per_page + 1

page = st.number_input(
    "Page",
    min_value=1,
    max_value=total_pages,
    value=1,
    step=1
)

start = (page - 1) * items_per_page
end = start + items_per_page

page_files = before_files[start:end]

# -----------------------------
# Display defects
# -----------------------------

for i, file in enumerate(page_files, start=start):

    defect_id = str(i + 1)

    st.divider()

    if defect_id in after_dict:
        status = "✅ Completed"
    else:
        status = "❌ Pending"

    st.markdown(f"### Defect {defect_id}   {status}")

    before_url = f"{SUPABASE_URL}/storage/v1/object/public/{bucket}/{service}/before/{file['name']}"

    st.markdown("**Before Photo**")
    st.image(before_url, use_column_width=True)

    # -----------------------------
    # Show AFTER photo if exists
    # -----------------------------

    if defect_id in after_dict:

        after_name = after_dict[defect_id]["name"]

        after_url = f"{SUPABASE_URL}/storage/v1/object/public/{bucket}/{service}/after/{after_name}"

        st.markdown("**After Photo**")
        st.image(after_url, use_column_width=True)

    # -----------------------------
    # Upload / Replace photo
    # -----------------------------

    photo = st.camera_input(
        "📷 Upload / Replace After Photo",
        key=f"{service}_{i}"
    )

    if photo:

        compressed = compress_image(photo)

        filename = f"{service}/after/defect_{defect_id}_{int(time.time())}.jpg"

        supabase.storage.from_(bucket).upload(
            filename,
            compressed,
            {"content-type": "image/jpeg"}
        )

        st.success("Photo uploaded successfully")

        st.rerun()

