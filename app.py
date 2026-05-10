from pathlib import Path
from shiny import App, ui, render, reactive
from shinywidgets import output_widget, render_widget
from ipyleaflet import Map, GeoJSON, basemaps, WidgetControl
from ipywidgets import HTML
import geopandas as gpd
import plotly.express as px
import shinyswatch
import json

APP_DIR = Path(__file__).parent

# Load preprocessed data
work_gdf = gpd.read_file(APP_DIR / "work.fgb")
edu_gdf = gpd.read_file(APP_DIR / "study.fgb")

work_gdf["geometry"] = work_gdf["geometry"].simplify(0.003)
edu_gdf["geometry"] = edu_gdf["geometry"].simplify(0.003)

def add_popup_handler(layer, selected_info):
    def handle_click(**kwargs):
        feature = kwargs.get("feature")

        if feature:
            props = feature["properties"]
            selected_info.set(props["popup"])

    layer.on_click(handle_click)
               

# Make catogories
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

# Calculate level of change
        change_num = props.get("change")
        value_2018 = props.get("2018")
        value_2023 = props.get("2023")

        if (
            change_num is not None
            and value_2018 is not None
            and value_2018 != 0
        ):
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

        value_2018_text = (
            "N/A" if value_2018 is None else f"{value_2018:.0f}"
        )

        value_2023_text = (
            "N/A" if value_2023 is None else f"{value_2023:.0f}"
        )

        change_num_text = (
            "N/A" if change_num is None else f"{change_num:+.0f}"
        )

        props["popup"] = (
            f"<b>{props.get('SA22023_V1_00_NAME', 'Unknown')}</b><br>"
            f"{category}<br>"
            f"2018: {value_2018_text}<br>"
            f"2023: {value_2023_text}<br>"
            f"Change: {change_num_text}<br>"
            f"% Change: {change_pct_text}"
        )

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
        labels={
            "SA22023_V1_00_NAME": "Regions",
            col: "People",
        },
    )

    fig.update_layout(
        yaxis={"categoryorder": "total ascending"},
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
    )

    return fig

def make_negative_change_bar(df, title):

    decline_df = (
        df[df["change"] < 0]
        .sort_values("change")
        .head(10)
    )

    fig = px.bar(
    decline_df,
    x="change",
    y="SA22023_V1_00_NAME",
    orientation="h",
    title=title,
    labels={
        "SA22023_V1_00_NAME": "Regions",
        "change": "Change in People",
    },
)

    fig.update_layout(
        yaxis={"categoryorder": "total ascending"},
        margin={"l": 20, "r": 20, "t": 50, "b": 20},
    )

    return fig

# App UI

# Introduction page
app_ui = ui.page_fluid(

    ui.h1("Remote Work and Study in Auckland: An Interactive Overview"),

    ui.navset_tab(

       ui.nav_panel(
        "Introduction",

    ui.br(),
    ui.h2("Project Overview"),

    ui.p(
        "This dashboard explores patterns of working and studying"
        " from home across Auckland SA2 areas using Census records"
        " from 2018 and 2023. In both surveys, the adult New Zealand population"
        " were asked In your main job, did you mostly work at home... or work away from home?"
    ),

    ui.p(
        "The maps provided in this dashboard are used to expore behaviour changes from deciding to work away from home to working from home."
        " According to RNZ nearly 20 percent of the adult population of New Zealand report working from home."
        " An increase of 60 percent compared to census results in 2018."
        " Post-pandemic working habits are often pointed at for this switch in working behaviour."
        " In this analysis, we can clearly see the increase in the amount of people working from home."
        " But also the shifts in where those people are working or studying from home."
        " There is a clear pattern of working and studying from home being a rurally dominated activity to switching to the city"
        " For example, pre pandemic home work jobs were concidered ones in the rural sector but now that opnion has changed."
        " I hope this analysis could be used in conjunction with behaviour and economic studies."
        " As politicians are divided on the benefits or harms of people working from home."
        " Some argue that it encourages foot traffic for businessess and it promotes more flexible routines."
        " But some say it hinders productivity."
        
    ),
    
    ui.p(
        "From this data, Hobsonville Point Park was the most popular suburb for working and studing from home."
        " It also had the most change from 2018 to 2023, with an additional 825 people studying and working from home between the five years."
        " Hobsonville is a new devlopment in Auckland sold with modern town houses often centered towards indivudals who can work from home."
        " Furthermore, Point Catalina is also apart of Hobsonville further proving an 'attractability' of Hobsonville being a place centred modern working from home initiatives."
        " Millwater being the next on the list further proves this point as Millwater too is a new devlopment in the North of Auckland."
        " This analysis combined with data on people's profesions could analysis whether these individuals have their own businesses, and if that is a reason to working from home."
        
    ),
    
    ui.h3("Work vs Study, what is more popular?"),

        ui.p(
        "Working from home is more popular and experienced much larger increases than studying from home between 2018 to 2023."
        " This is probably due to long term effects of working from home initiatives from the Covid-19 pandemic."
        " New technological devlopments and changing attitudes around work attitude have lead to such change."
        " Working from home is also much more attractive for working individuals with full time responsibities like children."
        " Therefore, working from home opens more opportunities for people to work full time."
        ),

        ui.p(
            "Students on the other hand benefit more from engaging with their education says one study."
            " While post pandemic attitudes to translate to students, for the most part it is important to attend classes, laboratories, and tutorials."
            " As a student, I understand this because I need to go to my laboratories to understand my coursework."
            " Furthermore, many students do not want to be left out of the university experience."

        ),

ui.h4("Sources"),
    ui.tags.ul(
        ui.tags.li(
            ui.a(
                "StatsNZ data",
                href="https://datafinder.stats.govt.nz/",
                target="_blank",
            )
        ),
        ui.tags.li(
            ui.a(
                "RNZ: Pros and cons of working from home",
                href="https://www.rnz.co.nz/news/national/528854/the-pros-and-cons-of-working-from-home",
                target="_blank",
            )
        ),

       ui.tags.li(
        ui.a(
            "Shifting work attitudes pre and post pandemic",
            href="https://pmc.ncbi.nlm.nih.gov/articles/PMC9988592/",
            target="_blank",
        )
    ),

    ui.tags.li(
        ui.a(
            "Taylor & Francis study on remote work",
            href="https://www.tandfonline.com/doi/full/10.1080/09585192.2024.2422013",
            target="_blank",
        )
    ),

    ui.tags.li(
        ui.a(
            "NCBI study on online learning",
            href="https://pmc.ncbi.nlm.nih.gov/articles/PMC9769479/",
            target="_blank",
        )
    ),

    ui.tags.li(
        ui.a(
            "OneRoof Hobsonville profile",
            href="https://www.oneroof.co.nz/suburb/hobsonville-waitakere-city-1185",
            target="_blank",
        )
    ),
),

ui.h5("How to Use the dashboard"),

ui.tags.ul(
    ui.tags.li("Open the dashboard tab to view maps and statistics."),
    ui.tags.li("Click regions on the maps to display area information."),
    ui.tags.li("Use the left-side controls to switch variables."),
),

ui.hr(),

# Key stats
ui.h6("Key Statistics"),

ui.tags.ul(

    ui.tags.li(
        f"Largest increase in working from home: "
        f"{work_gdf.loc[work_gdf['change'].idxmax(), 'SA22023_V1_00_NAME']} "
        f"({work_gdf['change'].max():+.0f} people)"
    ),

    ui.tags.li(
        f"Largest increase in studying from home: "
        f"{edu_gdf.loc[edu_gdf['change'].idxmax(), 'SA22023_V1_00_NAME']} "
        f"({edu_gdf['change'].max():+.0f} people)"
    ),

    ui.tags.li(
        f"Highest number working from home in 2023: "
        f"{work_gdf.loc[work_gdf['2023'].idxmax(), 'SA22023_V1_00_NAME']} "
        f"({work_gdf['2023'].max():.0f} people)"
    ),

    ui.tags.li(
        f"Highest number studying from home in 2023: "
        f"{edu_gdf.loc[edu_gdf['2023'].idxmax(), 'SA22023_V1_00_NAME']} "
        f"({edu_gdf['2023'].max():.0f} people)"
    ),

    ui.tags.li(
        f"Greatest overall work-from-home change (2018–2023): "
        f"{work_gdf.loc[work_gdf['change'].abs().idxmax(), 'SA22023_V1_00_NAME']} "
        f"({work_gdf['change'].abs().max():.0f} people)"
    ),

    ui.tags.li(
        f"Greatest overall study-from-home change (2018–2023): "
        f"{edu_gdf.loc[edu_gdf['change'].abs().idxmax(), 'SA22023_V1_00_NAME']} "
        f"({edu_gdf['change'].abs().max():.0f} people)"
    ),
),

        ),

# Map sidebar
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

                    ui.hr(),
# Map slider - for diffrences
                    ui.h5("Difference filter"),
                    ui.input_slider(
                        "change_range",
                        "Show areas with change between:",
                        min=-24,
                        max=714,
                        value=[-24, 714],
                        step=50,
                    ),

                    width=300,
                ),

# Card tab for histogram stats
                ui.navset_card_tab(

                    ui.nav_panel(
                        "Maps",

                        ui.row(

                            ui.column(
                                6,
                                ui.h4("Work From Home"),
                                output_widget("work_map", height="550px"),
                                ui.output_ui("work_info"),
                            ),

                            ui.column(
                                6,
                                ui.h4("Study From Home"),
                                output_widget("study_map", height="550px"),
                                ui.output_ui("study_info"),
                            ),
                        ),
                    ),

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
                                    ui.column(
                                        6,
                                        output_widget("work_2018_chart", height="400px"),
                                    ),
                                    ui.column(
                                        6,
                                        output_widget("work_2023_chart", height="400px"),
                                    ),
                                ),
                            ),

                            ui.nav_panel(
                                "Study Histograms",
                                ui.row(
                                    ui.column(
                                        6,
                                        output_widget("study_2018_chart", height="400px"),
                                    ),
                                    ui.column(
                                        6,
                                        output_widget("study_2023_chart", height="400px"),
                                    ),
                                ),
                            ),

                            ui.nav_panel(
                                "Decline Charts",
                                ui.row(
                                    ui.column(
                                        6,
                                        ui.h4("Largest Decline in Working From Home"),
                                        output_widget("work_decline_chart", height="400px"),
                                    ),

                                    ui.column(
                                        6,
                                        ui.h4("Largest Decline in Studying From Home"),
                                        output_widget("study_decline_chart", height="400px"),
                                    ),
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

    selected_work_info = reactive.Value("Click a work area on the map to see details.")
    selected_study_info = reactive.Value("Click a study area on the map to see details.")

    work_layer = GeoJSON(
        data={"type": "FeatureCollection", "features": []},
        style_callback=lambda feature: feature["properties"]["style"],
        hover_style={"color": "black", "weight": 2, "fillOpacity": 0.95},
        name="Work"
    )

    study_layer = GeoJSON(
        data={"type": "FeatureCollection", "features": []},
        style_callback=lambda feature: feature["properties"]["style"],
        hover_style={"color": "black", "weight": 2, "fillOpacity": 0.95},
        name="Study"
    )

    add_popup_handler(work_layer, selected_work_info)
    add_popup_handler(study_layer, selected_study_info)

    work_map_widget.add_layer(work_layer)
    study_map_widget.add_layer(study_layer)

    work_map_widget.add_control(make_legend("Work from home"))
    study_map_widget.add_control(make_legend("Study from home"))

    @reactive.calc
    def filtered_work_gdf():
        low, high = input.change_range()
        return work_gdf[
            (work_gdf["change"] >= low) &
            (work_gdf["change"] <= high)
        ]


    @reactive.calc
    def filtered_study_gdf():
        low, high = input.change_range()
        return edu_gdf[
            (edu_gdf["change"] >= low) &
            (edu_gdf["change"] <= high)
        ]

    @reactive.effect
    def _update_work_map():
       work_layer.data = make_geojson(filtered_work_gdf(), input.work_metric(), "Work from home")

    @reactive.effect
    def _update_study_map():
        study_layer.data = make_geojson(filtered_study_gdf(), input.study_metric(), "Study from home")

    @render_widget
    def work_map():
        return work_map_widget

    @render_widget
    def study_map():
        return study_map_widget

    @render_widget
    def work_chart():
        return make_bar(filtered_work_gdf(), input.work_metric(), f"Top 10 Work From Home ({input.work_metric()})")

    @render_widget
    def study_chart():
        return make_bar(filtered_study_gdf(), input.study_metric(), f"Top 10 Study From Home ({input.study_metric()})")

    @render_widget
    def work_2018_chart():
        return make_bar(work_gdf, "2018", "Top 10 Work From Home (2018)")

    @render_widget
    def work_2023_chart():
        return make_bar(work_gdf, "2023", "Top 10 Work From Home (2023)")
    
    @render_widget
    def work_decline_chart():
        return make_negative_change_bar(
            work_gdf,
            "Largest Decline in Working From Home"
        )

    @render_widget
    def study_decline_chart():
        return make_negative_change_bar(
            edu_gdf,
            "Largest Decline in Studying From Home"
        )

    @render_widget
    def study_2018_chart():
        return make_bar(edu_gdf, "2018", "Top 10 Study From Home (2018)")

    @render_widget
    def study_2023_chart():
        return make_bar(edu_gdf, "2023", "Top 10 Study From Home (2023)")

    @render.ui
    def work_info():
        return ui.HTML(selected_work_info())

    @render.ui
    def study_info():
        return ui.HTML(selected_study_info())

#App
app = App(app_ui, server)