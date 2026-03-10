#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import streamlit as st
from supabase import create_client
from PIL import Image
import io
import time
import zipfile

ADMIN_PASSWORD = "1234"

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

st.set_page_config(page_title="Defect Checklist", page_icon="📋")

st.title("Syed Alwi Pumping Station")


@st.cache_data(ttl=10)
def get_files(path):
    return supabase.storage.from_(bucket).list(path)


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

# -----------------------------
# Progress Summary
# -----------------------------

st.subheader("Defect Progress")

for svc in service_names:

    # before_files = supabase.storage.from_(bucket).list(f"{svc}/before/")
    # after_files = supabase.storage.from_(bucket).list(f"{svc}/after/")

    before_files = get_files(f"{service}/before/")
    after_files = get_files(f"{service}/after/")    

    total = len(before_files)

    cleared = len(set([
        f["name"].split("_")[1]
        for f in after_files if f["name"].startswith("defect_")
    ]))

    st.write(f"**{svc}: {cleared} / {total} defects cleared**")

st.divider()

# -----------------------------
# Select service
# -----------------------------

service = st.selectbox("Select Service", service_names)

# -----------------------------
# Load defects
# -----------------------------

before_files = supabase.storage.from_(bucket).list(f"{service}/before/")
before_files = sorted(before_files, key=lambda x: x["name"])

after_files = supabase.storage.from_(bucket).list(f"{service}/after/")

# -----------------------------
# Build AFTER dictionary
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
##################################################################################################################
st.divider()
st.subheader("Supervisor Download")

password = st.text_input("Enter supervisor password", type="password", key="download_pw")

if password == ADMIN_PASSWORD:

    if st.button("⬇ Download All After Photos"):

        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, "w") as zip_file:

            for f in after_files:

                path = f"{service}/after/{f['name']}"

                file_data = supabase.storage.from_(bucket).download(path)

                zip_file.writestr(f["name"], file_data)

        zip_buffer.seek(0)

        st.download_button(
            label="Download ZIP",
            data=zip_buffer,
            file_name=f"{service}_after_photos.zip",
            mime="application/zip"
        )

elif password != "":
    st.error("Incorrect password")

#################################################################################################################################

# -----------------------------
# Pagination
# -----------------------------

items_per_page = 10
total_defects = len(before_files)
total_pages = (total_defects - 1) // items_per_page + 1

# Initialize page state
if "page" not in st.session_state:
    st.session_state.page = 1

page = st.session_state.page

start = (page - 1) * items_per_page
end = start + items_per_page

page_files = before_files[start:end]


## Top Navigation

col1, col2, col3 = st.columns([1,2,1])

with col1:
    if st.button("⬅ Previous Page", key="top_prev") and st.session_state.page > 1:
        st.session_state.page -= 1
        st.rerun()

with col2:
    new_page = st.number_input(
        f"Page (1 - {total_pages})",
        min_value=1,
        max_value=total_pages,
        value=st.session_state.page,
        step=1,
        key="page_jump"
    )

    if new_page != st.session_state.page:
        st.session_state.page = new_page
        st.rerun()

with col3:
    if st.button("Next Page ➡", key="top_next") and st.session_state.page < total_pages:
        st.session_state.page += 1
        st.rerun()

# -----------------------------
# Session state for camera
# -----------------------------

if "active_camera" not in st.session_state:
    st.session_state.active_camera = None

# -----------------------------
# Display defects
# -----------------------------

for i, file in enumerate(page_files, start=start):

    defect_id = str(i + 1)

    st.divider()

    status = "❌ Pending"

    if defect_id in after_dict:
        status = "✅ Completed"

    st.markdown(f"### Defect {defect_id}   {status}")

    before_url = f"{SUPABASE_URL}/storage/v1/object/public/{bucket}/{service}/before/{file['name']}"

    # st.image(before_url)
    st.image(before_url, use_container_width=True)

    # show after photo
    if defect_id in after_dict:

        after_name = after_dict[defect_id]["name"]

        after_url = f"{SUPABASE_URL}/storage/v1/object/public/{bucket}/{service}/after/{after_name}"

        st.image(after_url)

        # -----------------------------
        # Delete photo section
        # -----------------------------

        if st.button("🗑 Delete Photo", key=f"delete_{service}_{defect_id}"):

            st.session_state[f"delete_confirm_{service}_{defect_id}"] = True


        if st.session_state.get(f"delete_confirm_{service}_{defect_id}", False):

            password = st.text_input(
                "Enter supervisor password",
                type="password",
                key=f"pw_{service}_{defect_id}"
            )

            if password == ADMIN_PASSWORD:

                if st.button("Confirm Delete", key=f"confirm_{service}_{defect_id}"):

                    supabase.storage.from_(bucket).remove(
                        [f"{service}/after/{after_name}"]
                    )

                    st.success("Photo deleted")

                    st.session_state[f"delete_confirm_{service}_{defect_id}"] = False

                    st.rerun()

            elif password != "":
                st.error("Incorrect password")


    # -----------------------------
    # Button to activate camera
    # -----------------------------

    if st.button("📷 Take / Replace Photo", key=f"btn_{service}_{i}"):

        st.session_state.active_camera = defect_id

    # -----------------------------
    # Show camera only if activated
    # -----------------------------


    if st.session_state.active_camera == defect_id:

        uploaded = st.file_uploader(
            "Select Photo from Album",
            type=["jpg","jpeg","png"],
            key=f"upload_{service}_{i}"
        )

        photo = st.camera_input("Or Take Photo", key=f"cam_{service}_{i}")

        file = None

        if uploaded:
            file = uploaded
        elif photo:
            file = photo

        if file:

            compressed = compress_image(file)

            filename = f"{service}/after/defect_{defect_id}_{int(time.time())}.jpg"

            # --------------------------------
            # Remove old photos of this defect
            # --------------------------------
            old_files = [
                f"{service}/after/{f['name']}"
                for f in after_files
                if f["name"].startswith(f"defect_{defect_id}_")
            ]

            if old_files:
                supabase.storage.from_(bucket).remove(old_files)

            # --------------------------------
            # Upload new photo
            # --------------------------------
            supabase.storage.from_(bucket).upload(
                filename,
                compressed,
                file_options={"content-type": "image/jpeg"}
            )

            st.success("Photo uploaded")

            st.session_state.active_camera = None

            st.rerun()

st.divider()

col1, col2 = st.columns(2)

with col1:
    if st.button("⬅ Previous Page") and st.session_state.page > 1:
        st.session_state.page -= 1
        st.rerun()

with col2:
    if st.button("Next Page ➡") and st.session_state.page < total_pages:
        st.session_state.page += 1
        st.rerun()        

