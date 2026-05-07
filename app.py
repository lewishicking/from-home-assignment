from pathlib import Path
from shiny import App, ui, render, reactive
from shinywidgets import output_widget, render_widget
from ipyleaflet import Map, GeoJSON, basemaps, WidgetControl, Popup
from ipywidgets import HTML
import geopandas as gpd
import plotly.express as px
import shinyswatch
import json

APP_DIR = Path(__file__).parent

# Load preprocessed data
work_gdf = gpd.read_file(APP_DIR / "work.fgb")
edu_gdf = gpd.read_file(APP_DIR / "study.fgb")

def add_popup_handler(layer, map_widget):
    def handle_click(**kwargs):
        feature = kwargs.get("feature")
        coordinates = kwargs.get("coordinates")

        if feature and coordinates:
            props = feature["properties"]

            popup = Popup(
                location=coordinates,
                child=HTML(value=props["popup"]),
                close_button=True,
                auto_close=True,
                close_on_escape_key=True,
            )

            map_widget.add_layer(popup)

    layer.on_click(handle_click)

def make_geojson(gdf, value_col, category):
    plot_gdf = gdf.dropna(subset=["geometry", value_col]).copy()
    geojson_data = json.loads(plot_gdf.to_json())

    vals = plot_gdf[value_col].dropna()
    q1, q2, q3, q4, q5 = vals.quantile([0.2, 0.4, 0.6, 0.8, 0.95])

    colours = [
        "#fff7ec",
        "#fee8c8",
        "#fdd49e",
        "#fdbb84",
        "#fc8d59",
        "#d7301f",
    ]

    for feature in geojson_data["features"]:
        props = feature["properties"]
        val = props[value_col]

        if val <= q1:
            fill = colours[0]
        elif val <= q2:
            fill = colours[1]
        elif val <= q3:
            fill = colours[2]
        elif val <= q4:
            fill = colours[3]
        elif val <= q5:
            fill = colours[4]
        else:
            fill = colours[5]

        change_num = props.get("change")
        value_2018 = props.get("2018")
        value_2023 = props.get("2023")

        if value_2018 and value_2018 != 0:
            change_pct = (change_num / value_2018) * 100
            change_pct_text = f"{change_pct:.1f}%"
        else:
            change_pct_text = "N/A"

        props["style"] = {
            "color": "#333333",
            "weight": 0.6,
            "fillColor": fill,
            "fillOpacity": 0.8,
        }

        props["popup"] = f"""
        <b>{props.get("SA22023_V1_00_NAME", "Unknown area")}</b><br>
        <b>{category}</b><br><br>
        2018: {value_2018:.0f}<br>
        2023: {value_2023:.0f}<br>
        Change: {change_num:+.0f}<br>
        Percentage change: {change_pct_text}
        """

    return geojson_data
# Map helpers
def make_legend(title):
    colours = [
        "#fff7ec",
        "#fee8c8",
        "#fdd49e",
        "#fdbb84",
        "#fc8d59",
        "#d7301f",
    ]

    legend_html = f"""
    <div style="
        background:white;
        padding:10px;
        border:2px solid grey;
        border-radius:8px;
        font-size:12px;
    ">
    <b>{title}</b><br>
    <i style="background:{colours[0]};width:18px;height:12px;display:inline-block;"></i> Very low<br>
    <i style="background:{colours[1]};width:18px;height:12px;display:inline-block;"></i> Low<br>
    <i style="background:{colours[2]};width:18px;height:12px;display:inline-block;"></i> Moderate<br>
    <i style="background:{colours[3]};width:18px;height:12px;display:inline-block;"></i> High<br>
    <i style="background:{colours[4]};width:18px;height:12px;display:inline-block;"></i> Very high<br>
    <i style="background:{colours[5]};width:18px;height:12px;display:inline-block;"></i> Extreme
    </div>
    """
    return WidgetControl(widget=HTML(value=legend_html), position="bottomleft")


def make_bar(df, col, title):
    top10 = (
        df.dropna(subset=[col])[["SA22023_V1_00_NAME", col]]
        .sort_values(col, ascending=False)
        .head(10)
    )

    fig = px.bar(
        top10,
        x=col,
        y="SA22023_V1_00_NAME",
        orientation="h",
        title=title,
    )
    fig.update_layout(
        yaxis={"categoryorder": "total ascending"},
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
    )
    return fig


# UI
app_ui = ui.page_fluid(

    ui.h1("Auckland Work and Study From Home (2018–2023)"),

    ui.navset_tab(

        # ---------------- INTRO PAGE ----------------
        ui.nav_panel(
            "Introduction",

            ui.br(),

            ui.h2("Project Overview"),

            ui.p(
                """
                This dashboard explores patterns of working and studying
                from home across Auckland SA2 areas using New Zealand
                Census data from 2018 and 2023.
                """
            ),

            ui.p(
                """
                The project compares spatial differences in remote work
                and remote study behaviour before and after major societal
                changes such as COVID-19.
                """
            ),

            ui.h3("Data Sources"),

            ui.tags.ul(
                ui.tags.li("2023 New Zealand Census"),
                ui.tags.li("SA2 Generalised Boundaries"),
                ui.tags.li("Work-from-home and study-from-home statistics"),
            ),

            ui.h3("How to Use the Dashboard"),

            ui.tags.ul(
                ui.tags.li("Use the Maps page to explore spatial patterns."),
                ui.tags.li("Use the Statistics page to compare top areas."),
                ui.tags.li("Switch between 2018, 2023, and change values."),
            ),

            ui.br(),
        ),

        # ---------------- DASHBOARD ----------------
        ui.nav_panel(

            "Dashboard",

            ui.layout_sidebar(

                ui.sidebar(

                    ui.h4("Map Controls"),

                    ui.h5("Work map"),
                    ui.input_radio_buttons(
                        "work_metric",
                        None,
                        choices={
                            "2018": "Work from home (2018)",
                            "2023": "Work from home (2023)",
                            "change": "Difference",
                        },
                        selected="change",
                    ),

                    ui.hr(),

                    ui.h5("Study map"),
                    ui.input_radio_buttons(
                        "study_metric",
                        None,
                        choices={
                            "2018": "Study from home (2018)",
                            "2023": "Study from home (2023)",
                            "change": "Difference",
                        },
                        selected="change",
                    ),

                    width=300,
                ),

                ui.navset_card_tab(

                    # -------- MAPS TAB --------
                    ui.nav_panel(

                        "Maps",

                        ui.row(
                            ui.column(
                                6,
                                ui.h4("Work From Home"),
                                output_widget("work_map", height="550px"),
                            ),

                            ui.column(
                                6,
                                ui.h4("Study From Home"),
                                output_widget("study_map", height="550px"),
                            ),
                        ),
                    ),

                    # -------- STATISTICS TAB --------
                    ui.nav_panel(

                        "Statistics",

                        ui.row(
                            ui.column(
                                6,
                                ui.h4("Top 10 Work From Home Areas"),
                                output_widget("work_chart", height="350px"),
                            ),

                            ui.column(
                                6,
                                ui.h4("Top 10 Study From Home Areas"),
                                output_widget("study_chart", height="350px"),
                            ),
                        ),

                        ui.hr(),

                        ui.navset_tab(

                            ui.nav_panel(
                                "Work Histograms",
                                ui.row(
                                    ui.column(6, output_widget("work_2018_chart", height="400px")),
                                    ui.column(6, output_widget("work_2023_chart", height="400px")),
                                ),
                            ),

                            ui.nav_panel(
                                "Study Histograms",
                                ui.row(
                                    ui.column(6, output_widget("study_2018_chart", height="400px")),
                                    ui.column(6, output_widget("study_2023_chart", height="400px")),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    ),

    theme=shinyswatch.theme.minty,
)
# Server
def server(input, output, session):

    # Build maps once
    work_map_widget = Map(center=(-36.85, 174.76), zoom=9, basemap=basemaps.OpenStreetMap.Mapnik)
    study_map_widget = Map(center=(-36.85, 174.76), zoom=9, basemap=basemaps.OpenStreetMap.Mapnik)

    work_layer = GeoJSON(
        data={"type": "FeatureCollection", "features": []},
        style_callback=lambda feature: feature["properties"]["style"],
        hover_style={"color": "black", "weight": 2, "fillOpacity": 0.95},
        name="Work"
    )

    add_popup_handler(work_layer, work_map_widget)

    study_layer = GeoJSON(
        data={"type": "FeatureCollection", "features": []},
        style_callback=lambda feature: feature["properties"]["style"],
        hover_style={"color": "black", "weight": 2, "fillOpacity": 0.95},
        name="Study"
    )

    add_popup_handler(study_layer, study_map_widget)

    work_map_widget.add_layer(work_layer)
    study_map_widget.add_layer(study_layer)

    work_map_widget.add_control(make_legend("Work from home"))
    study_map_widget.add_control(make_legend("Study from home"))
    
    @reactive.effect
    def _update_work_map():
        work_layer.data = make_geojson(work_gdf, input.work_metric(), "Work from home")

    @reactive.effect
    def _update_study_map():
        study_layer.data = make_geojson(edu_gdf, input.study_metric(), "Study from home")

    @render_widget
    def work_map():
        return work_map_widget

    @render_widget
    def study_map():
        return study_map_widget

    @render_widget
    def work_chart():
        return make_bar(work_gdf, input.work_metric(), f"Top 10 Work From Home ({input.work_metric()})")

    @render_widget
    def study_chart():
        return make_bar(edu_gdf, input.study_metric(), f"Top 10 Study From Home ({input.study_metric()})")

    @render_widget
    def work_2018_chart():
        return make_bar(work_gdf, "2018", "Top 10 Work From Home (2018)")

    @render_widget
    def work_2023_chart():
        return make_bar(work_gdf, "2023", "Top 10 Work From Home (2023)")

    @render_widget
    def study_2018_chart():
        return make_bar(edu_gdf, "2018", "Top 10 Study From Home (2018)")

    @render_widget
    def study_2023_chart():
        return make_bar(edu_gdf, "2023", "Top 10 Study From Home (2023)")


#App
app = App(app_ui, server)
