import geopandas as gpd
import pandas as pd

# --- LOAD FULL DATA (LOCAL ONLY) ---
sa2 = gpd.read_file("data_raw/statistical-area-2-2023-generalised.gpkg").to_crs(4326)

# Filter to Auckland (your bounding box is good)
sa2 = sa2.cx[174.25:175.10, -37.25:-36.58].copy()

# Keep only needed columns
sa2["SA2"] = sa2["SA22023_V1_00"].astype(str)
sa2 = sa2[["SA2", "SA22023_V1_00_NAME", "geometry"]]

# Simplify geometry
sa2["geometry"] = sa2["geometry"].simplify(0.002)

# --- WORK DATA ---
work = pd.read_csv("data_raw/2023-census-main-means-of-travel-to-work-by-statistical-area.csv").replace(-999, pd.NA)
work["SA2"] = work["SA22023_V1_00_workplace_address"].astype(str)
work["2018"] = pd.to_numeric(work["2018_Work_at_home"], errors="coerce")
work["2023"] = pd.to_numeric(work["2023_Work_at_home"], errors="coerce")
work["change"] = work["2023"] - work["2018"]

work = work.groupby("SA2", as_index=False)[["2018", "2023", "change"]].mean()

# --- STUDY DATA ---
edu = pd.read_csv("data_raw/2023-census-main-means-of-travel-to-education-by-statistical.csv").replace(-999, pd.NA)
edu["SA2"] = edu["SA22023_V1_00_educational_institution_address"].astype(str)
edu["2018"] = pd.to_numeric(edu["2018_Study_at_home"], errors="coerce")
edu["2023"] = pd.to_numeric(edu["2023_Study_at_home"], errors="coerce")
edu["change"] = edu["2023"] - edu["2018"]

edu = edu.groupby("SA2", as_index=False)[["2018", "2023", "change"]].mean()

# --- MERGE ---
work_gdf = sa2.merge(work, on="SA2", how="left")
edu_gdf = sa2.merge(edu, on="SA2", how="left")

# --- SAVE SMALL FILES ---
work_gdf.to_file("work.fgb", driver="FlatGeobuf")
edu_gdf.to_file("study.fgb", driver="FlatGeobuf")
